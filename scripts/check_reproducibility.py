"""Regenerate in a temporary directory and compare stable artifacts, not clocks."""

import tempfile
from pathlib import Path

from PIL import Image, features

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
        expected = stable(read_json(Path("reports/demo/summary.json")))
        if stable(result) != expected:

            def differences(a, b, path="summary"):
                if isinstance(a, dict) and isinstance(b, dict):
                    return [
                        d
                        for key in a.keys() | b.keys()
                        for d in differences(a.get(key), b.get(key), path + "." + key)
                    ]
                if a != b:
                    return [path]
                return []

            print("Differing stable fields:", differences(stable(result), expected), flush=True)
            generated = read_jsonl(root / "data/samples.jsonl")
            committed = read_jsonl(Path("data/sample/samples.jsonl"))
            print(
                "First sample differing fields:",
                differences(generated[0], committed[0], "sample"),
                flush=True,
            )
            original_image = Image.open(Path("data/sample") / committed[0]["image_path"]).convert(
                "RGB"
            )
            generated_image = Image.open(root / "data" / generated[0]["image_path"]).convert("RGB")
            print(
                "First image identical decoded pixels:",
                original_image.tobytes() == generated_image.tobytes(),
                flush=True,
            )
            print(
                "Pillow codec versions:",
                {name: features.version(name) for name in ("freetype2", "zlib")},
                flush=True,
            )
            raise AssertionError("Stable evidence differs; see diagnostic fields above")
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
