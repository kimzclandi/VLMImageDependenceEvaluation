"""Regenerate in a temporary directory and compare stable artifacts, not clocks."""

import tempfile
from pathlib import Path

from flywheel.io import read_json, read_jsonl
from flywheel.pipeline import demo


def stable(value):
    volatile = {"latency_ms", "latency_ms_median", "latency_ms_p95", "run_time_utc"}
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in volatile}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def main() -> None:
    config = read_json(Path("configs/demo.json"))
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        result = demo(config, root / "data", root / "reports", Path("schemas/sample.schema.json"))
        assert stable(result) == stable(read_json(Path("reports/demo/summary.json")))
        for relative in ("samples.jsonl", "augmentation/samples.jsonl"):
            assert read_jsonl(root / "data" / relative) == read_jsonl(
                Path("data/sample") / relative
            )
        for name in (
            "v1_outputs.jsonl",
            "v2_outputs.jsonl",
            "v1_scores.jsonl",
            "v2_scores.jsonl",
            "priority_queue.jsonl",
            "v1_augmentation_scores.jsonl",
            "v2_augmentation_scores.jsonl",
        ):
            assert stable(read_jsonl(root / "reports" / name)) == stable(
                read_jsonl(Path("reports/demo") / name)
            ), name
        assert (root / "reports/EXPERIMENT_REPORT.md").read_text() == Path(
            "reports/demo/EXPERIMENT_REPORT.md"
        ).read_text()
    print(
        "PASS: datasets, PNG hashes, predictions, metrics, queue, augmentation and report reproduced; only clocks excluded"
    )


if __name__ == "__main__":
    main()
