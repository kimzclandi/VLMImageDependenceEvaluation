"""One-command offline evidence pipeline. No optimizer, fitting or training occurs."""

import logging
from collections import Counter
from pathlib import Path

from flywheel.adapters import ReferenceAdapter
from flywheel.augmentation import augment
from flywheel.data import generate, validate
from flywheel.evaluation import compare, export_review, infer, score, summarize
from flywheel.io import digest, write_json, write_jsonl
from flywheel.strategy import prioritize

LOG = logging.getLogger(__name__)


def report_markdown(result: dict, old: list[dict], samples: list[dict]) -> str:
    holdout = result["holdout_regression"]
    by_id = {s["sample_id"]: s for s in samples}
    lines = [
        "# Experiment report: deterministic reference comparison",
        "",
        "> Actual code execution on original synthetic data. Both baselines read privileged scene metadata. No VLM was trained or evaluated. Rule changes were specified in advance; augmentation did not train v2.",
        "",
        "## Question and hypothesis",
        "",
        "Can a reproducible evaluation-to-data workflow discover known rule defects, produce valid targeted samples and reject a candidate whose overall score rises while counting regresses? The expected negative control is the v2 large-only counting rule.",
        "",
        "## Provenance",
        "",
        f"- Dataset: `{result['config']['dataset_version']}`; SHA-256 `{result['dataset_sha256']}`",
        f"- Configuration SHA-256: `{result['config_sha256']}`",
        f"- Seed: {result['config']['seed']}; prompt: `{result['config']['prompt_version']}`; models: `metadata-reference-NOT-VLM/v1` and `/v2`.",
        "- Command: `flywheel demo --config configs/demo.json --data-dir data/sample --report-dir reports/demo`",
        "- Input: `data/sample/samples.jsonl`; outputs/scores: `reports/demo/{v1,v2}_{outputs,scores}.jsonl`.",
        "- Exact software versions: `reports/demo/environment.json`; file hashes: `reports/demo/artifact_manifest.json`.",
        "",
        "## Fixed holdout results",
        "",
        "| Task | n | v1 | v2 | Delta (pp) |",
        "|---|---:|---:|---:|---:|",
    ]
    for task, values in holdout["task_slices"].items():
        lines.append(
            f"| {task} | {values['n']} | {values['old']:.1%} | {values['new']:.1%} | {values['delta'] * 100:+.1f} |"
        )
    lo, hi = holdout["paired_ci95"]
    lines += [
        "",
        f"Paired accuracy delta: **{holdout['delta'] * 100:+.1f} pp**, 95% scene-family bootstrap interval [{lo * 100:+.1f}, {hi * 100:+.1f}] pp. Candidate gate: **{holdout['gate']}**. Regressed slices: {', '.join(holdout['regressed_tasks']) or 'none'}.",
        "",
        "The interval describes this small synthetic generator distribution, not real robots. Multiple slices are descriptive; the conservative release rule rejects any observed task drop. All capability slices are checked, including those not targeted by the data queue.",
        "",
        "## Failure-to-data decision",
        "",
        f"From dev only: {result['selected_parents']} diverse parent families selected; {result['augmentation']['generated']} novel augmentations accepted; {len(result['augmentation']['skipped'])} candidates skipped after bounded retries. Holdout families never enter production. Augmentation performance is a diagnostic selected slice, not independent evidence of improvement.",
        "",
        "| Operator | Accepted |",
        "|---|---:|",
    ]
    lines += [f"| {k} | {v} |" for k, v in result["augmentation"]["operator_counts"].items()]
    lines += [
        "",
        "## Traceable dev failures",
        "",
        "| Sample | Question | Ground truth | v1 parsed | Provisional classification |",
        "|---|---|---|---|---|",
    ]
    seen = set()
    for row in old:
        if row["split"] != "dev" or row["correct"] or row["failure_type"] in seen:
            continue
        seen.add(row["failure_type"])
        sample = by_id[row["sample_id"]]
        lines.append(
            f"| `{row['sample_id']}` | {sample['question']} | {sample['ground_truth']} | {row['parsed_answer']} | {row['failure_type']} |"
        )
    lines += [
        "",
        "## Interpretation and next decision",
        "",
        "The workflow hypothesis is supported if data validation succeeds and the intentional counting regression is detected. A higher aggregate score does not justify release. Reject v2, fix the counting rule for pipeline validation, and next evaluate a real VLM with pixels-only inputs on a newly frozen holdout before making any model-quality claim.",
        "",
        "No measured outcome here establishes that synthetic data improves a neural model. There is no training job, no external model run, no human-verified causal label, and no real-robot success metric. v1/v2 timing is measured CPU rule execution and must not be compared with VLM latency.",
        "",
        "## Full evidence",
        "",
        "See `summary.json` for dev/holdout/all/augmentation metrics and configuration; `priority_queue.jsonl` for every score factor; `review_queue.csv` for human triage; `validation.json` for generated-data checks; and `v*_scores.jsonl` for per-sample results.",
        "",
    ]
    return "\n".join(lines)


def demo(config: dict, data_root: Path, report_root: Path, schema_path: Path) -> dict:
    for path in (data_root, report_root):
        if path.exists():
            raise FileExistsError(f"Use new data/report directories; refusing to overwrite {path}")
    data, reports = data_root.resolve(), report_root.resolve()
    if data.is_relative_to(reports) or reports.is_relative_to(data):
        raise ValueError("Data and report directories must not overlap")
    report_root.mkdir(parents=True, exist_ok=False)
    LOG.info("Generating paired dataset")
    samples = generate(data_root, config)
    validation = {"base": validate(samples, data_root, schema_path)}
    old = score(
        samples, infer(samples, data_root, ReferenceAdapter("v1"), config["prompt_version"])
    )
    ranked = prioritize(samples, old, config)
    LOG.info("Selected %d development families", sum(r["selected"] for r in ranked))
    augmented, aug_manifest = augment(samples, ranked, data_root / "augmentation", config)
    validation["augmentation"] = validate(augmented, data_root / "augmentation", schema_path)
    new = score(
        samples, infer(samples, data_root, ReferenceAdapter("v2"), config["prompt_version"])
    )
    metrics = {}
    for version, rows in (("v1", old), ("v2", new)):
        write_jsonl(report_root / f"{version}_scores.jsonl", rows)
        evaluation_keys = {
            "group_id",
            "task_type",
            "difficulty",
            "split",
            "tags",
            "ground_truth",
            "correct",
            "exact_match",
            "failure_type",
            "classification_reason",
            "review_status",
        }
        write_jsonl(
            report_root / f"{version}_outputs.jsonl",
            [{k: v for k, v in r.items() if k not in evaluation_keys} for r in rows],
        )
        metrics[version] = summarize(rows, config)
        aug_scores = score(
            augmented,
            infer(
                augmented,
                data_root / "augmentation",
                ReferenceAdapter(version),
                config["prompt_version"],
            ),
        )
        write_jsonl(report_root / f"{version}_augmentation_scores.jsonl", aug_scores)
        metrics[version]["augmentation"] = summarize(aug_scores, config)
    result = {
        "experiment_type": "deterministic reference comparison; no training",
        "config": config,
        "config_sha256": digest(config),
        "dataset_sha256": digest(samples),
        "sample_count": len(samples),
        "group_count": len({s["group_id"] for s in samples}),
        "selected_parents": sum(r["selected"] for r in ranked),
        "augmentation": aug_manifest,
        "failure_counts_v1_dev": dict(
            Counter(r["failure_type"] for r in old if r["split"] == "dev" and not r["correct"])
        ),
        "metrics": metrics,
        "all_regression": compare(old, new, config),
        "holdout_regression": compare(
            [r for r in old if r["split"] == "holdout"],
            [r for r in new if r["split"] == "holdout"],
            config,
        ),
    }
    write_json(report_root / "summary.json", result)
    write_json(report_root / "validation.json", validation)
    write_jsonl(report_root / "priority_queue.jsonl", ranked)
    export_review([r for r in old if r["split"] == "dev"], report_root / "review_queue.csv")
    (report_root / "EXPERIMENT_REPORT.md").write_text(
        report_markdown(result, old, samples), encoding="utf-8"
    )
    LOG.info("Holdout candidate gate: %s", result["holdout_regression"]["gate"])
    return result
