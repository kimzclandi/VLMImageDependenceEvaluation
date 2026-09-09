"""Targeted production operators; every mutation recomputes the oracle label."""

import copy
import random
from collections import Counter
from pathlib import Path

from flywheel.data import COLORS, SHAPES, refresh, solve
from flywheel.io import digest, write_json, write_jsonl

OPERATORS = (
    "counterfactual",
    "hard_negative",
    "curriculum",
    "attribute_substitution",
    "spatial_perturbation",
    "distractor_injection",
)


def fingerprint(sample: dict) -> str:
    return digest([sample["scene_metadata"], sample["query"]])


def add_object(sample: dict, hard: bool = False) -> None:
    """Use a free grid cell, respecting both object and label spacing."""
    objects = sample["scene_metadata"]["objects"]
    if len(objects) >= 8:
        raise ValueError("No free cell")
    for x, y in [(x, y) for y in (112, 272) for x in (80, 192, 304, 416)]:
        if all(abs(x - o["x"]) >= 65 or abs(y - o["y"]) >= 90 for o in objects):
            obj = copy.deepcopy(objects[0])
            obj.update(id=f"o{len(objects) + 1}", x=x, y=y)
            if hard:
                # A near match differs in exactly one queried attribute.
                obj.update(sample["query"].get("filters", {}))
                obj["size"] = "large" if obj["size"] == "small" else "small"
            else:
                obj["color"] = next(c for c in COLORS if c != obj["color"])
            objects.append(obj)
            return
    raise ValueError("No collision-free cell")


def mutate(parent: dict, operator: str, rng: random.Random, forbidden: set[str]) -> dict:
    row = copy.deepcopy(parent)
    objects = row["scene_metadata"]["objects"]
    if operator == "counterfactual":
        candidates = []
        if row["query"]["kind"] == "relation":
            for rel in ("left", "right", "above", "below", "adjacent"):
                candidate = copy.deepcopy(row)
                candidate["query"]["relation"] = rel
                candidates.append(candidate)
        else:
            for i in range(len(objects)):
                for key, values in (
                    ("color", list(COLORS)),
                    ("shape", SHAPES),
                    ("size", ("small", "large")),
                ):
                    for value in values:
                        candidate = copy.deepcopy(row)
                        candidate["scene_metadata"]["objects"][i][key] = value
                        candidates.append(candidate)
        valid = [
            c
            for c in candidates
            if solve(c["scene_metadata"], c["query"]) != parent["ground_truth"]
            and fingerprint(c) not in forbidden
        ]
        if not valid:
            raise ValueError("No novel answer-changing single-attribute intervention")
        row = rng.choice(valid)
    elif operator in ("hard_negative", "distractor_injection"):
        add_object(row, hard=operator == "hard_negative")
        row["difficulty"] = "hard"
    elif operator == "curriculum":
        # A harder task instance, preserving the original question and label semantics.
        add_object(row, hard=True)
        row["scene_metadata"]["objects"][-1]["shape"] = rng.choice(SHAPES)
        row["scene_metadata"]["objects"][-1]["color"] = rng.choice(list(COLORS))
        row["difficulty"] = "hard"
    elif operator == "attribute_substitution":
        # Global color permutation in both scene and query: answer-preserving equivariance.
        colors = list(COLORS)
        shift = rng.randint(1, len(colors) - 1)
        mapping = dict(zip(colors, colors[shift:] + colors[:shift], strict=True))
        for obj in objects:
            obj["color"] = mapping[obj["color"]]
        filters = row["query"].get("filters", {})
        if "color" in filters:
            filters["color"] = mapping[filters["color"]]
    elif operator == "spatial_perturbation":
        for obj in objects:
            obj["x"] += rng.choice((-4, 4))
            obj["y"] += rng.choice((-4, 4))
    else:
        raise ValueError("Unknown augmentation operator")
    return row


def augment(
    samples: list[dict], ranked: list[dict], root: Path, config: dict
) -> tuple[list[dict], dict]:
    by_id = {s["sample_id"]: s for s in samples}
    rng = random.Random(config["seed"] + 1000)
    forbidden = {fingerprint(s) for s in samples}
    accepted, skipped = [], []
    for chosen in ranked:
        if not chosen["selected"]:
            continue
        parent = by_id[chosen["sample_id"]]
        if parent["split"] != "dev":
            raise ValueError("Never augment a holdout family")
        for operator in OPERATORS:
            row = None
            for _ in range(8):
                try:
                    candidate = mutate(parent, operator, rng, forbidden)
                except ValueError:
                    continue
                if fingerprint(candidate) not in forbidden:
                    row = candidate
                    break
            if row is None:
                skipped.append(
                    {
                        "parent_id": parent["sample_id"],
                        "operator": operator,
                        "reason": "no novel valid candidate",
                    }
                )
                continue
            row.update(
                sample_id=f"{parent['sample_id']}-aug-{operator}",
                parent_id=parent["sample_id"],
                split="augmentation",
                mutation=operator,
                dataset_version=config["dataset_version"] + "-augmentation-v1",
            )
            row = refresh(row, root)
            row["answer_changed"] = row["ground_truth"] != parent["ground_truth"]
            forbidden.add(fingerprint(row))
            accepted.append(row)
    summary = {
        "selected_parents": sum(r["selected"] for r in ranked),
        "generated": len(accepted),
        "operator_counts": dict(Counter(r["mutation"] for r in accepted)),
        "answer_changed": sum(r["answer_changed"] for r in accepted),
        "skipped": skipped,
        "content_sha256": digest(accepted),
    }
    write_jsonl(root / "samples.jsonl", accepted)
    write_json(root / "manifest.json", summary)
    return accepted, summary
