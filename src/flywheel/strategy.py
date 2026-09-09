"""Configurable, inspectable failure prioritization with diversity caps."""

from collections import Counter

from flywheel.io import digest


def signature(sample: dict) -> str:
    """Coarse similarity proxy; not semantic novelty or a learned embedding."""
    return digest([sample["task_type"], sample["difficulty"], sample["query"].get("filters", {}), sample["query"].get("relation")])[:16]


def prioritize(samples: list[dict], scores: list[dict], config: dict, previous: list[dict] | None = None) -> list[dict]:
    """Only dev failures can feed the production queue; never mine holdout failures."""
    by_id = {s["sample_id"]: s for s in samples}
    previous_by_id = {r["sample_id"]: r for r in (previous or [])}
    dev = [r for r in scores if r["split"] == "dev"]
    totals = Counter(r["task_type"] for r in dev)
    failures = Counter(r["task_type"] for r in dev if not r["correct"])
    signatures = Counter(signature(by_id[r["sample_id"]]) for r in dev)
    weights = config["weights"]
    if any(w < 0 for w in weights.values()) or abs(sum(weights.values())-1) > 1e-8:
        raise ValueError("Priority weights must be nonnegative and sum to one")
    ranked = []
    for row in dev:
        if row["correct"] or row["failure_type"] in ("annotation_error", "ambiguous_sample", "system_or_api_error", "output_format_error", "abstention_or_refusal"):
            continue
        sample = by_id[row["sample_id"]]
        sig = signature(sample)
        regression = bool(previous_by_id.get(row["sample_id"], {}).get("correct", False))
        factors = {"failure_frequency": failures[row["task_type"]]/totals[row["task_type"]], "task_importance": config["task_importance"][row["task_type"]], "severity": config["severity"][row["failure_type"]], "novelty": 1/signatures[sig], "regression": float(regression)}
        cost = config["cost"]["base"] + config["cost"]["per_object"]*len(sample["scene_metadata"]["objects"])
        if cost <= 0:
            raise ValueError("Production cost proxy must be positive")
        value = sum(weights[k]*factors[k] for k in weights)*sample["annotation_confidence"]/cost
        ranked.append({"sample_id": row["sample_id"], "task_type": row["task_type"], "failure_type": row["failure_type"], "priority_score": round(value, 6), "factors": factors, "annotation_confidence": sample["annotation_confidence"], "production_cost_proxy": cost, "signature": sig, "selected": False})
    ranked.sort(key=lambda r: (-r["priority_score"], r["sample_id"]))
    counts, families, selected = Counter(), set(), 0
    for row in ranked:
        family = by_id[row["sample_id"]]["group_id"]
        if selected < config["selection_budget"] and counts[row["signature"]] < config["max_per_signature"] and family not in families:
            row["selected"] = True
            selected += 1
            counts[row["signature"]] += 1
            families.add(family)
    return ranked
