"""Original synthetic scenes with explicit semantics and grouped interventions."""

import copy
import math
import random
from collections import Counter
from pathlib import Path

import jsonschema
from PIL import Image, ImageDraw, ImageFont

from flywheel.io import digest, file_digest, read_json, safe_path, write_json, write_jsonl

TASKS = (
    "spatial_relation",
    "attribute_binding",
    "counting",
    "target_selection",
    "instruction_following",
    "counterfactual",
)
COLORS = {"red": "#df4f56", "blue": "#3886d8", "green": "#26a584", "yellow": "#e9b936"}
SHAPES = ("circle", "square", "triangle")
GENERATOR_VERSION = "1.0.0"


def relation(a: dict, b: dict, name: str) -> bool:
    """Image coordinates: x increases right; y increases down; adjacent <= 150 px."""
    return {
        "left": a["x"] < b["x"],
        "right": a["x"] > b["x"],
        "above": a["y"] < b["y"],
        "below": a["y"] > b["y"],
        "adjacent": math.hypot(a["x"] - b["x"], a["y"] - b["y"]) <= 150,
    }[name]


def solve(scene: dict, query: dict) -> str:
    """Independent label oracle over structured objects; never a visual model."""
    objects = scene["objects"]
    by_id = {obj["id"]: obj for obj in objects}
    if query["kind"] == "relation":
        return "yes" if relation(by_id[query["a"]], by_id[query["b"]], query["relation"]) else "no"
    matches = [obj for obj in objects if all(obj[k] == v for k, v in query["filters"].items())]
    if "relation" in query:
        matches = [
            obj
            for obj in matches
            if obj["id"] != query["anchor"]
            and relation(obj, by_id[query["anchor"]], query["relation"])
        ]
    if query["kind"] == "count":
        return str(len(matches))
    if query["kind"] == "exists":
        return "yes" if matches else "no"
    return ",".join(sorted(obj["id"] for obj in matches)) or "none"


def question(query: dict) -> str:
    """Render the same query used by the label oracle into unambiguous English."""
    if query["kind"] == "relation":
        desc = {
            "left": "to the left of",
            "right": "to the right of",
            "above": "above",
            "below": "below",
            "adjacent": "adjacent to",
        }[query["relation"]]
        extra = " (centers at most 150 pixels apart)" if query["relation"] == "adjacent" else ""
        return f"Is {query['a']} {desc} {query['b']}{extra}? Answer yes or no."
    f = query["filters"]
    desc = " ".join(f[k] for k in ("size", "color", "shape") if k in f)
    spatial = (
        f" that is {query['relation']} {query['anchor']} (compare centers)"
        if "relation" in query
        else ""
    )
    if query["kind"] == "count":
        return f"How many {desc} objects are visible{spatial}? Answer an integer."
    if query["kind"] == "exists":
        return f"Is there a {desc} object{spatial}? Answer yes or no."
    return f"Select every {desc} object{spatial}. Return sorted object IDs separated by commas, or none."


def render(scene: dict, path: Path) -> None:
    """Draw objects and IDs with no label-answer text; sizes mean radius 18 or 27 px."""
    image = Image.new("RGB", (512, 384), "#f3f6fa")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=16)
    draw.rounded_rectangle(
        (12, 12, 500, 372), radius=18, fill="#ffffff", outline="#d6e0ec", width=2
    )
    draw.text((28, 26), "TABLETOP  /  512 x 384", font=font, fill="#64748b")
    for obj in scene["objects"]:
        x, y = obj["x"], obj["y"]
        r = 18 if obj["size"] == "small" else 27
        box = (x - r, y - r, x + r, y + r)
        color = COLORS[obj["color"]]
        if obj["shape"] == "circle":
            draw.ellipse(box, fill=color)
        elif obj["shape"] == "square":
            draw.rectangle(box, fill=color)
        else:
            draw.polygon([(x, y - r), (x - r, y + r), (x + r, y + r)], fill=color)
        draw.text((x - 9, y + r + 6), obj["id"], font=font, fill="#26364e")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def refresh(sample: dict, root: Path) -> dict:
    """Regenerate answer, natural-language question, tags and image after mutation."""
    sample["question"] = question(sample["query"])
    sample["ground_truth"] = solve(sample["scene_metadata"], sample["query"])
    sample["image_path"] = f"images/{sample['sample_id']}.png"
    render(sample["scene_metadata"], root / sample["image_path"])
    sample["image_sha256"] = file_digest(root / sample["image_path"])
    tags = [
        sample["task_type"],
        sample["difficulty"],
        f"objects_{len(sample['scene_metadata']['objects'])}",
    ]
    if len(sample["scene_metadata"]["objects"]) >= 6:
        tags.append("distractors")
    if sample.get("mutation"):
        tags.append(sample["mutation"])
    sample["tags"] = sorted(set(tags))
    return sample


def generate(root: Path, config: dict) -> list[dict]:
    """Generate 12 * groups_per_task samples. Pair families remain in one split."""
    rng = random.Random(config["seed"])
    rows = []
    for task in TASKS:
        for group in range(config["groups_per_task"]):
            level = (group // 3) % 3  # orthogonal to split, with all difficulties in each
            count = (4, 5, 7)[level]
            positions = [
                (x + rng.randint(-7, 7), y + rng.randint(-7, 7))
                for y in (112, 272)
                for x in (80, 192, 304, 416)
            ]
            rng.shuffle(positions)
            color = rng.choice(list(COLORS))
            shape = rng.choice(SHAPES)
            other_color = rng.choice([c for c in COLORS if c != color])
            other_shape = rng.choice([s for s in SHAPES if s != shape])
            objects = [
                {
                    "id": f"o{i + 1}",
                    "color": rng.choice(list(COLORS)),
                    "shape": rng.choice(SHAPES),
                    "size": rng.choice(("small", "large")),
                    "x": xy[0],
                    "y": xy[1],
                }
                for i, xy in enumerate(positions[:count])
            ]
            objects[0].update(color=color, shape=shape, size="small")
            objects[1].update(color=color, shape=other_shape, size="large")
            for obj in objects[2:]:
                if obj["color"] == color and obj["shape"] == shape:
                    obj["color"] = other_color
            query = {"kind": "exists", "filters": {"color": color, "shape": shape}}
            if task == "spatial_relation":
                query = {
                    "kind": "relation",
                    "a": "o1",
                    "b": "o2",
                    "relation": ("left", "right", "above", "below", "adjacent")[group % 5],
                }
            elif task == "counting":
                query["kind"] = "count"
                if group % 2:
                    query["filters"].pop("shape")
            elif task in ("target_selection", "instruction_following"):
                objects[1]["shape"] = shape
                query["kind"] = "select"
                query["filters"]["size"] = "small"
                if task == "instruction_following":
                    query.update(
                        anchor="o3",
                        relation="left" if objects[0]["x"] < objects[2]["x"] else "right",
                    )
            scene = {"width": 512, "height": 384, "objects": objects}
            group_id = f"s{config['seed']}-{task}-{group:03d}"
            sample = {
                "sample_id": group_id + "-a",
                "group_id": group_id,
                "parent_id": None,
                "task_type": task,
                "difficulty": ("easy", "medium", "hard")[level],
                "scene_metadata": scene,
                "query": query,
                "data_source": "procedural-original",
                "generator_version": GENERATOR_VERSION,
                "dataset_version": config["dataset_version"],
                "split": "holdout" if group % 3 == 2 else "dev",
                "annotation_confidence": 1.0,
                "mutation": "original",
            }
            rows.append(refresh(sample, root))
            paired = copy.deepcopy(sample)
            paired.update(
                sample_id=group_id + "-b",
                parent_id=sample["sample_id"],
                mutation="counterfactual_pair",
            )
            if task == "spatial_relation":
                paired["query"]["a"], paired["query"]["b"] = "o2", "o1"
            else:
                paired["scene_metadata"]["objects"][0]["color"] = other_color
            rows.append(refresh(paired, root))
    write_jsonl(root / "samples.jsonl", rows)
    write_json(
        root / "manifest.json",
        {
            "dataset_version": config["dataset_version"],
            "generator_version": GENERATOR_VERSION,
            "seed": config["seed"],
            "samples": len(rows),
            "groups": len({r["group_id"] for r in rows}),
            "split_counts": dict(Counter(r["split"] for r in rows)),
            "content_sha256": digest(rows),
            "config_sha256": digest(config),
        },
    )
    return rows


def validate(rows: list[dict], root: Path, schema_path: Path) -> dict:
    """Validate schema, labels, file bytes, IDs, spacing, pairs and split isolation."""
    schema = read_json(schema_path)
    ids, groups, contents, images = set(), {}, {}, {}
    for row in rows:
        jsonschema.validate(row, schema)
        sid, split = row["sample_id"], row["split"]
        if sid in ids:
            raise ValueError("Duplicate sample ID")
        ids.add(sid)
        group = row["group_id"]
        if group in groups and groups[group] != split:
            raise ValueError("Group crosses splits")
        groups[group] = split
        path = safe_path(root, row["image_path"])
        if file_digest(path) != row["image_sha256"]:
            raise ValueError("Image hash mismatch")
        with Image.open(path) as im:
            if im.size != (512, 384):
                raise ValueError("Invalid image dimensions")
        if solve(row["scene_metadata"], row["query"]) != row["ground_truth"]:
            raise ValueError("Annotation error")
        objects = row["scene_metadata"]["objects"]
        if len({o["id"] for o in objects}) != len(objects):
            raise ValueError("Duplicate object IDs")
        for i, a in enumerate(objects):
            for b in objects[i + 1 :]:
                if abs(a["x"] - b["x"]) < 65 and abs(a["y"] - b["y"]) < 90:
                    raise ValueError("Overlapping objects or labels")
        fingerprint = digest([row["scene_metadata"], row["query"]])
        if fingerprint in contents:
            raise ValueError("Duplicate scene and query")
        contents[fingerprint] = sid
        ih = row["image_sha256"]
        if ih in images and images[ih] != split:
            raise ValueError("Identical image crosses splits")
        images[ih] = split
    return {
        "samples_validated": len(rows),
        "groups": len(groups),
        "schema": "sample.schema.json",
        "duplicate_content": 0,
        "cross_split_images": 0,
        "annotation_errors": 0,
    }
