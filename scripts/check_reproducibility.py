"""Reproduce semantic evidence across PNG codecs; optionally require identical bytes."""

import argparse
import tempfile
from pathlib import Path

from PIL import Image

from flywheel.io import digest, file_digest, read_json, read_jsonl
from flywheel.pipeline import demo


def stable(value, hash_aliases=None):
    """Exclude actual clocks; canonicalize only hashes proven visually equivalent."""
    volatile = {"latency_ms", "latency_ms_median", "latency_ms_p95", "run_time_utc"}
    identities = {"image_sha256", "sample_sha256", "dataset_sha256", "content_sha256"}
    aliases = hash_aliases or {}
    if isinstance(value, dict):
        return {
            k: aliases.get(v, v) if k in identities and isinstance(v, str) else stable(v, aliases)
            for k, v in value.items()
            if k not in volatile
        }
    if isinstance(value, list):
        return [stable(v, aliases) for v in value]
    return value


def align_samples(actual, expected, actual_root, expected_root, strict_bytes=False):
    """Check every field and pixel before allowing compression-only hash differences.

    Both recorded file hashes are independently checked against their actual PNG bytes.
    Original files and reports are never rewritten to pretend their hashes are equal.
    """
    assert len(actual) == len(expected), "Sample count differs"
    aliases = {}
    for new, old in zip(actual, expected, strict=True):
        assert {k: v for k, v in new.items() if k != "image_sha256"} == {
            k: v for k, v in old.items() if k != "image_sha256"
        }, f"Sample metadata differs: {new['sample_id']}"
        new_path, old_path = actual_root / new["image_path"], expected_root / old["image_path"]
        assert file_digest(new_path) == new["image_sha256"], "Generated file hash invalid"
        assert file_digest(old_path) == old["image_sha256"], "Committed file hash invalid"
        with Image.open(new_path) as a, Image.open(old_path) as b:
            assert a.size == b.size and a.convert("RGB").tobytes() == b.convert("RGB").tobytes(), (
                f"Decoded pixels differ: {new['sample_id']}"
            )
        if strict_bytes:
            assert new["image_sha256"] == old["image_sha256"], "PNG bytes differ in strict mode"
        aliases[new["image_sha256"]] = old["image_sha256"]
        aliases[digest(new)] = digest(old)
    aliases[digest(actual)] = digest(expected)
    return aliases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-bytes",
        action="store_true",
        help="Require the same PNG codec as the committed run",
    )
    args = parser.parse_args()
    config = read_json(Path("configs/demo.json"))
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        result = demo(config, root / "data", root / "reports", Path("schemas/sample.schema.json"))
        aliases = {}
        dataset_aliases = {}
        for relative in (Path("."), Path("augmentation")):
            actual = read_jsonl(root / "data" / relative / "samples.jsonl")
            expected = read_jsonl(Path("data/sample") / relative / "samples.jsonl")
            aliases.update(
                align_samples(
                    actual,
                    expected,
                    root / "data" / relative,
                    Path("data/sample") / relative,
                    args.strict_bytes,
                )
            )
            dataset_aliases[digest(actual)] = digest(expected)
        assert stable(result, aliases) == stable(read_json(Path("reports/demo/summary.json"))), (
            "Stable summary differs"
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
            assert stable(read_jsonl(root / "reports" / name), aliases) == stable(
                read_jsonl(Path("reports/demo") / name)
            ), name
        generated_report = (root / "reports/EXPERIMENT_REPORT.md").read_text()
        for actual_hash, expected_hash in dataset_aliases.items():
            generated_report = generated_report.replace(actual_hash, expected_hash)
        assert generated_report == Path("reports/demo/EXPERIMENT_REPORT.md").read_text()
    print(
        "PASS: every pixel, metadata field, label, prediction, stable metric, queue and report reproduced; all actual file hashes verified"
        + (
            "; strict PNG bytes identical"
            if args.strict_bytes
            else "; compression-only identity differences permitted after pixel equality"
        )
    )


if __name__ == "__main__":
    main()
