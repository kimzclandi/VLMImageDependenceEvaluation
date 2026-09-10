"""Frozen small tabletop experiment: independent families, paired prompts, no training."""

import copy
import random
import re
from pathlib import Path

from flywheel.data import COLORS, SHAPES, render
from flywheel.io import file_digest, write_json, write_jsonl

VERSION = "visual-tabletop-v2"


def parse(raw, task):
    text = raw.strip().lower().rstrip(".").strip()
    pattern = {"existence": r"yes|no", "counting": r"[0-4]", "spatial": r"yes|no"}[task]
    return text if re.fullmatch(pattern, text) else None


def audit(rows, root):
    ids, families, hashes = set(), {}, {}
    for r in rows:
        if r["sample_id"] in ids:
            raise ValueError("Duplicate ID")
        ids.add(r["sample_id"])
        for mapping, key in ((families, r["family"]), (hashes, r["image_sha256"])):
            if key in mapping and mapping[key] != r["split"]:
                raise ValueError("Split leakage")
            mapping[key] = r["split"]
        if file_digest(root / r["image_path"]) != r["image_sha256"]:
            raise ValueError("Changed image")
    return {"samples": len(rows), "families": len(families), "cross_split_images": 0}


def build(root: Path):
    rng = random.Random(91027)
    rows = []
    # Every family contains three questions on one image; family is split before generation.
    for family in range(24):
        positions = [(110, 130), (390, 130), (110, 280), (390, 280)]
        rng.shuffle(positions)
        labels = list("ABCD")
        rng.shuffle(labels)
        objects = [
            dict(
                id=labels[i],
                x=x + rng.randint(-10, 10),
                y=y + rng.randint(-10, 10),
                size="large",
                color=rng.choice(list(COLORS)),
                shape=rng.choice(SHAPES),
            )
            for i, (x, y) in enumerate(positions)
        ]
        scene = {"width": 512, "height": 384, "objects": objects}
        # Uniform target color choice, independent of object ordering and ID.
        color = rng.choice(list(COLORS))
        shape = rng.choice(SHAPES)
        a, b = rng.sample(objects, 2)
        questions = [
            (
                "counting",
                f"How many {color} objects are visible? Answer an integer from 0 to 4.",
                str(sum(o["color"] == color for o in objects)),
            ),
            (
                "existence",
                f"Is there a {color} {shape}? Answer yes or no.",
                "yes"
                if any(o["color"] == color and o["shape"] == shape for o in objects)
                else "no",
            ),
            (
                "spatial",
                f"Is object {a['id']} to the left of object {b['id']}? Compare centers. Answer yes or no.",
                "yes" if a["x"] < b["x"] else "no",
            ),
        ]
        image_path = f"images/f{family:02d}.png"
        render(scene, root / image_path)
        for task, q, gold in questions:
            rows.append(
                dict(
                    sample_id=f"f{family:02d}-{task}",
                    family=f"f{family:02d}",
                    split="dev" if family < 12 else "holdout",
                    task=task,
                    question=q,
                    ground_truth=gold,
                    scene=scene,
                    image_path=image_path,
                    image_sha256=file_digest(root / image_path),
                    dataset_version=VERSION,
                )
            )
    write_jsonl(root / "samples.jsonl", rows)
    write_json(root / "audit.json", audit(rows, root))
    return rows


def score(rows, outputs):
    expected = {(r["sample_id"], arm) for r in rows for arm in ("baseline", "observe")}
    lookup = {}
    for o in outputs:
        key = o["sample_id"], o["arm"]
        if key not in expected or key in lookup:
            raise ValueError("Unexpected or duplicate output")
        lookup[key] = o
    scores = []
    for r in rows:
        for arm in ("baseline", "observe"):
            o = lookup.get((r["sample_id"], arm), {"raw_output": "", "error": "missing_output"})
            parsed = None if o.get("error") else parse(o["raw_output"], r["task"])
            scores.append(
                dict(
                    sample_id=r["sample_id"],
                    family=r["family"],
                    split=r["split"],
                    task=r["task"],
                    arm=arm,
                    gold=r["ground_truth"],
                    prediction=parsed,
                    correct=parsed == r["ground_truth"],
                    valid=parsed is not None,
                    raw_output=o["raw_output"],
                    error=o.get("error"),
                )
            )
    return scores


def summarize(scores):
    result = {}
    for split in ("dev", "holdout"):
        result[split] = {}
        for arm in ("baseline", "observe"):
            part = [s for s in scores if s["split"] == split and s["arm"] == arm]
            result[split][arm] = {
                "n": len(part),
                "accuracy": sum(s["correct"] for s in part) / len(part),
                "format_validity": sum(s["valid"] for s in part) / len(part),
                "tasks": {
                    t: sum(s["correct"] for s in part if s["task"] == t)
                    / sum(s["task"] == t for s in part)
                    for t in ("counting", "existence", "spatial")
                },
            }
        pairs = {
            s["sample_id"]: s for s in scores if s["split"] == split and s["arm"] == "baseline"
        }
        other = [s for s in scores if s["split"] == split and s["arm"] == "observe"]
        result[split]["paired"] = {
            "fixed": sum(s["correct"] and not pairs[s["sample_id"]]["correct"] for s in other),
            "regressed": sum(not s["correct"] and pairs[s["sample_id"]]["correct"] for s in other),
            "both_valid_n": sum(s["valid"] and pairs[s["sample_id"]]["valid"] for s in other),
        }
    return result


def produce(rows, scores, root):
    queue = []
    byid = {r["sample_id"]: r for r in rows}
    parents = set()
    children = []
    for s in scores:
        if s["correct"]:
            continue
        symptom = (
            "system_error"
            if s["error"]
            else ("invalid_format" if not s["valid"] else "answer_mismatch")
        )
        queue.append(
            {
                **s,
                "symptom": symptom,
                "root_cause": "unverified",
                "review_status": "pending",
                "production_eligible": s["split"] == "dev" and symptom == "answer_mismatch",
            }
        )
        r = byid[s["sample_id"]]
        if (
            s["split"] != "dev"
            or symptom != "answer_mismatch"
            or r["family"] in parents
            or len(parents) >= 6
        ):
            continue
        parents.add(r["family"])
        child = copy.deepcopy(r)
        child.update(
            sample_id=r["sample_id"] + "-jitter",
            parent_id=r["sample_id"],
            dataset_version=VERSION + "-augmentation-v1",
            generation_config={"operator": "global_translation", "dx": 5, "dy": -5},
            label_source="translation_invariant_parent_oracle",
            training_consumed=False,
        )
        for obj in child["scene"]["objects"]:
            obj["x"] += 5
            obj["y"] -= 5
        child["image_path"] = "images/" + child["sample_id"] + ".png"
        render(child["scene"], root / child["image_path"])
        child["image_sha256"] = file_digest(root / child["image_path"])
        child["parent_image_sha256"] = r["image_sha256"]
        children.append(child)
    write_jsonl(root / "samples.jsonl", children)
    return queue, children
