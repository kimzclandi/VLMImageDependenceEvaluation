"""Strict answer contracts, grouped bootstrap uncertainty and paired regression gates."""

import csv
import json
import random
import re
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from flywheel.adapters import Adapter, ModelInput
from flywheel.io import digest, safe_path

TAXONOMY = (
    "perception_error",
    "spatial_reasoning_error",
    "attribute_binding_error",
    "counting_error",
    "instruction_following_error",
    "distractor_susceptibility",
    "output_format_error",
    "abstention_or_refusal",
    "system_or_api_error",
    "ambiguous_sample",
    "annotation_error",
)


def normalize(answer: str) -> str:
    text = answer.strip().lower()
    if re.fullmatch(r"o\d+(\s*,\s*o\d+)*", text):
        return ",".join(sorted(part.strip() for part in text.split(",")))
    if re.fullmatch(r"\d+", text):
        return str(int(text))
    return text


def parse(raw: str, query: dict) -> tuple[str | None, str | None]:
    """Accept only a JSON object with one string/int answer in the task's domain."""
    try:
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"answer"}:
            return None, "output_format_error"
        answer = value["answer"]
        if isinstance(answer, bool) or not isinstance(answer, (str, int)):
            return None, "output_format_error"
        text = normalize(str(answer))
        kind = query["kind"]
        valid = (
            (kind in ("exists", "relation") and text in ("yes", "no"))
            or (kind == "count" and bool(re.fullmatch(r"\d+", text)))
            or (kind == "select" and (text == "none" or bool(re.fullmatch(r"o\d+(,o\d+)*", text))))
        )
        if not valid or (kind == "select" and len(text.split(",")) != len(set(text.split(",")))):
            return None, "output_format_error"
        return str(answer), None
    except (ValueError, TypeError):
        return None, "output_format_error"


def infer(samples: list[dict], root: Path, adapter: Adapter, prompt_version: str) -> list[dict]:
    """Persist real measured timing; failed requests remain in metric denominators."""
    outputs = []
    for sample in samples:
        item = ModelInput(
            sample["question"],
            safe_path(root, sample["image_path"]).read_bytes(),
            sample["scene_metadata"],
            sample["query"],
        )
        started = datetime.now(UTC).isoformat()
        t0 = time.perf_counter()
        reply = adapter.predict(item)
        elapsed = (time.perf_counter() - t0) * 1000
        answer, parse_error = (
            parse(reply.raw_output, sample["query"]) if not reply.error else (None, None)
        )
        outputs.append(
            {
                "sample_id": sample["sample_id"],
                "sample_sha256": digest(sample),
                "dataset_version": sample["dataset_version"],
                "model_name": adapter.name,
                "model_version": adapter.version,
                "prompt_version": prompt_version,
                "inference_parameters": adapter.parameters,
                "raw_output": reply.raw_output,
                "parsed_answer": answer,
                "latency_ms": round(elapsed, 6),
                "error_status": reply.error,
                "parse_error": parse_error,
                "run_time_utc": started,
                "confidence": None,
                **{k: v for k, v in vars(reply).items() if k not in ("raw_output", "error")},
            }
        )
    return outputs


def classify(sample: dict, output: dict, correct: bool) -> tuple[str | None, str]:
    """Task-based symptoms are triage hypotheses, not verified causal diagnoses."""
    if output["error_status"] == "refusal":
        return "abstention_or_refusal", "adapter reported refusal"
    if output["error_status"]:
        return "system_or_api_error", "adapter reported a request failure"
    if output["parse_error"]:
        return "output_format_error", "answer violates the JSON/domain contract"
    if correct:
        return None, "answer matched"
    label = {
        "spatial_relation": "spatial_reasoning_error",
        "attribute_binding": "attribute_binding_error",
        "counting": "counting_error",
        "target_selection": "instruction_following_error",
        "instruction_following": "instruction_following_error",
        "counterfactual": "attribute_binding_error",
    }[sample["task_type"]]
    return label, "provisional task-based symptom; visual cause requires human review"


def score(samples: list[dict], outputs: list[dict], reviews: dict | None = None) -> list[dict]:
    by_id = {o["sample_id"]: o for o in outputs}
    if (
        len(by_id) != len(outputs)
        or len(samples) != len({s["sample_id"] for s in samples})
        or set(by_id) != {s["sample_id"] for s in samples}
    ):
        raise ValueError("Outputs must align exactly once with every sample")
    rows = []
    for sample in samples:
        output = by_id[sample["sample_id"]]
        if output["sample_sha256"] != digest(sample):
            raise ValueError("Output was generated from different sample content")
        answer = output["parsed_answer"]
        correct = (
            answer is not None
            and normalize(answer) == normalize(sample["ground_truth"])
            and not output["error_status"]
        )
        failure, reason = classify(sample, output, correct)
        review = (reviews or {}).get(sample["sample_id"])
        if review:
            if correct:
                raise ValueError("Review must reference a failed sample")
            failure, reason = review["failure_type"], review["note"]
        rows.append(
            {
                **output,
                "group_id": sample["group_id"],
                "task_type": sample["task_type"],
                "difficulty": sample["difficulty"],
                "split": sample["split"],
                "tags": sample["tags"],
                "ground_truth": sample["ground_truth"],
                "correct": bool(correct),
                "exact_match": bool(
                    answer == sample["ground_truth"] and not output["error_status"]
                ),
                "failure_type": failure,
                "classification_reason": reason,
                "review_status": "reviewed" if review else "provisional",
            }
        )
    return rows


def bootstrap(
    rows: list[dict], field: str = "correct", seed: int = 42, repeats: int = 1000
) -> list[float | None]:
    """Percentile cluster bootstrap: resample entire scene families, not paired rows."""
    if not rows:
        return [None, None]
    groups = defaultdict(list)
    for row in rows:
        groups[row["group_id"]].append(float(row[field]))
    if len(groups) < 2:
        return [None, None]
    values = list(groups.values())
    rng = random.Random(seed)
    means = []
    for _ in range(repeats):
        draw = [v for cluster in rng.choices(values, k=len(values)) for v in cluster]
        means.append(statistics.mean(draw))
    means.sort()
    return [
        round(means[int((repeats - 1) * 0.025)], 6),
        round(means[int((repeats - 1) * 0.975)], 6),
    ]


def metric(rows: list[dict], seed: int, repeats: int) -> dict:
    if not rows:
        return {"n": 0, "accuracy": None, "ci95": [None, None]}
    latencies = sorted(r["latency_ms"] for r in rows)
    costs = [r["estimated_cost_usd"] for r in rows]
    return {
        "n": len(rows),
        "groups": len({r["group_id"] for r in rows}),
        "accuracy": statistics.mean(r["correct"] for r in rows),
        "exact_match": statistics.mean(r["exact_match"] for r in rows),
        "ci95": bootstrap(rows, seed=seed, repeats=repeats),
        "error_rate": statistics.mean(bool(r["error_status"]) for r in rows),
        "unparseable_rate": statistics.mean(bool(r["parse_error"]) for r in rows),
        "latency_ms_median": statistics.median(latencies),
        "latency_ms_p95": latencies[min(len(rows) - 1, int(len(rows) * 0.95))],
        "estimated_cost_usd": sum(costs) if all(c is not None for c in costs) else None,
        "unknown_cost_rows": sum(c is None for c in costs),
        "cache_hits": sum(r["cache_hit"] for r in rows),
    }


def summarize(rows: list[dict], config: dict) -> dict:
    seed, repeats = config["seed"], config["bootstrap_replicates"]
    result = {"overall": metric(rows, seed, repeats)}
    for key in ("task_type", "difficulty", "split", "tags"):
        groups = defaultdict(list)
        for row in rows:
            for value in row[key] if key == "tags" else [row[key]]:
                groups[value].append(row)
        result[key] = {
            value: metric(subset, seed, repeats) for value, subset in sorted(groups.items())
        }
    return result


def compare(old: list[dict], new: list[dict], config: dict) -> dict:
    """Paired fixed-set comparison. A slice drop blocks promotion regardless of total."""
    previous = {r["sample_id"]: r for r in old}
    current = {r["sample_id"]: r for r in new}
    if len(previous) != len(old) or len(current) != len(new) or set(previous) != set(current):
        raise ValueError("Regression requires identical unique sample IDs")
    for sid, row in current.items():
        if row["sample_sha256"] != previous[sid]["sample_sha256"]:
            raise ValueError("Regression requires frozen sample contents")
    deltas = [
        {"group_id": r["group_id"], "delta": int(r["correct"]) - int(previous[sid]["correct"])}
        for sid, r in current.items()
    ]
    slices = {}
    for task in sorted({r["task_type"] for r in old}):
        before = [r for r in old if r["task_type"] == task]
        after = [r for r in new if r["task_type"] == task]
        a = statistics.mean(r["correct"] for r in before)
        b = statistics.mean(r["correct"] for r in after)
        slices[task] = {"n": len(before), "old": a, "new": b, "delta": b - a}
    regressed = [sid for sid, r in current.items() if previous[sid]["correct"] and not r["correct"]]
    fixed = [sid for sid, r in current.items() if not previous[sid]["correct"] and r["correct"]]
    rejected = [
        task for task, values in slices.items() if values["delta"] < -config["regression_tolerance"]
    ]
    return {
        "n": len(old),
        "delta": statistics.mean(r["delta"] for r in deltas) if deltas else None,
        "paired_ci95": bootstrap(deltas, "delta", config["seed"], config["bootstrap_replicates"]),
        "task_slices": slices,
        "fixed_ids": fixed,
        "regressed_ids": regressed,
        "gate": "REJECT" if rejected else "PASS",
        "regressed_tasks": rejected,
        "gate_scope": "descriptive slice guardrail, not a statistical significance claim",
    }


def export_review(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["sample_id", "suggested_failure", "failure_type", "note"]
        )
        writer.writeheader()
        writer.writerows(
            {
                "sample_id": r["sample_id"],
                "suggested_failure": r["failure_type"],
                "failure_type": "",
                "note": "",
            }
            for r in rows
            if not r["correct"]
        )


def load_reviews(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    result = {}
    for row in rows:
        if not row["failure_type"]:
            continue
        if row["failure_type"] not in TAXONOMY or not row["note"].strip():
            raise ValueError("Reviewed failures need a valid taxonomy label and evidence note")
        if row["sample_id"] in result:
            raise ValueError("Duplicate review")
        result[row["sample_id"]] = row
    return result
