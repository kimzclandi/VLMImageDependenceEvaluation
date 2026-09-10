"""Descriptive post-run diagnostics; never selects another prompt or changes gold."""

import random
from collections import Counter, defaultdict
from pathlib import Path

from flywheel.io import read_jsonl, write_json

root = Path("reports/real_vlm")
rows = read_jsonl(Path("data/visual_v2/samples.jsonl"))
scores = read_jsonl(root / "scores.jsonl")
result = {"scope": "descriptive diagnostics, no hypothesis selection or dataset exclusions"}
for split in ("dev", "holdout"):
    subset = [r for r in rows if r["split"] == split]
    baseline = {s["sample_id"]: s for s in scores if s["split"] == split and s["arm"] == "baseline"}
    observe = {s["sample_id"]: s for s in scores if s["split"] == split and s["arm"] == "observe"}
    groups = defaultdict(list)
    for r in subset:
        groups[r["family"]].append(
            int(observe[r["sample_id"]]["correct"]) - int(baseline[r["sample_id"]]["correct"])
        )
    rng = random.Random(42)
    means = []
    for _ in range(2000):
        draw = [v for group in rng.choices(list(groups.values()), k=len(groups)) for v in group]
        means.append(sum(draw) / len(draw))
    means.sort()
    both = [
        r["sample_id"]
        for r in subset
        if baseline[r["sample_id"]]["valid"] and observe[r["sample_id"]]["valid"]
    ]
    near = []
    for r in subset:
        if r["task"] != "spatial":
            continue
        words = r["question"].split()
        objects = {o["id"]: o for o in r["scene"]["objects"]}
        if abs(objects[words[2]]["x"] - objects[words[8].rstrip("?")]["x"]) < 25:
            near.append(r["sample_id"])
    result[split] = {
        "paired_delta_ci95_cluster_bootstrap": [means[49], means[1949]],
        "bootstrap_families": len(groups),
        "bootstrap_replicates": 2000,
        "both_valid_n": len(both),
        "both_valid_accuracy": {
            a: sum(table[i]["correct"] for i in both) / len(both) if both else None
            for a, table in [("baseline", baseline), ("observe", observe)]
        },
        "near_x_spatial_ids": near,
        "near_x_spatial_accuracy": {
            a: sum(table[i]["correct"] for i in near) / len(near) if near else None
            for a, table in [("baseline", baseline), ("observe", observe)]
        },
        "label_counts": {
            t: dict(Counter(r["ground_truth"] for r in subset if r["task"] == t))
            for t in ("counting", "existence", "spatial")
        },
    }
priors = {
    task: Counter(
        r["ground_truth"] for r in rows if r["split"] == "dev" and r["task"] == task
    ).most_common(1)[0][0]
    for task in ("counting", "existence", "spatial")
}
result["dev_majority_prior"] = {
    "answers": priors,
    "holdout_correct": sum(
        r["ground_truth"] == priors[r["task"]] for r in rows if r["split"] == "holdout"
    ),
    "holdout_n": 36,
    "status": "post-hoc descriptive control, no model rerun",
}
write_json(root / "diagnostics.json", result)
print(result)
