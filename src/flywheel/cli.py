"""Command-line entry points. Run from the repository root."""

import argparse
import importlib.metadata
import logging
import platform
from pathlib import Path

from flywheel.adapters import APIAdapter, ReferenceAdapter
from flywheel.data import generate, validate
from flywheel.evaluation import compare, infer, load_reviews, score, summarize
from flywheel.io import file_digest, read_json, read_jsonl, write_json, write_jsonl
from flywheel.pipeline import demo
from flywheel.strategy import prioritize


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["demo", "generate", "validate", "infer", "evaluate", "prioritize", "compare"],
    )
    parser.add_argument("--config", type=Path, default=Path("configs/demo.json"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/demo"))
    parser.add_argument("--adapter", choices=["reference", "api"], default="reference")
    parser.add_argument("--version", choices=["v1", "v2"], default="v1")
    parser.add_argument("--outputs", type=Path, default=Path("reports/local/outputs.jsonl"))
    parser.add_argument("--old-scores", type=Path, default=Path("reports/demo/v1_scores.jsonl"))
    parser.add_argument("--new-scores", type=Path, default=Path("reports/demo/v2_scores.jsonl"))
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--api-cache", type=Path, default=Path(".cache-api"))
    parser.add_argument(
        "--input-price", type=float, help="USD per million input tokens, provider-specific"
    )
    parser.add_argument("--output-price", type=float, help="USD per million output tokens")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = read_json(args.config)
    if config["groups_per_task"] < 3 or config["bootstrap_replicates"] < 100:
        parser.error("At least 3 groups/task and 100 bootstrap replicates required")
    schema = Path("schemas/sample.schema.json")
    targets = {
        "generate": [args.data_dir],
        "infer": [args.outputs],
        "evaluate": [args.report_dir / "scores.jsonl", args.report_dir / "metrics.json"],
        "prioritize": [args.report_dir / "priority_queue.jsonl"],
        "compare": [args.report_dir / "comparison.json"],
    }
    for target in targets.get(args.command, []):
        if target.exists():
            parser.error(f"Refusing to overwrite {target}; choose a new output path")
    if args.command == "demo":
        result = demo(config, args.data_dir, args.report_dir, schema)
        versions = {
            name: importlib.metadata.version(name) for name in ("pillow", "jsonschema", "httpx")
        }
        for name in ("streamlit", "pytest", "ruff", "pandas", "altair"):
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                pass
        write_json(
            args.report_dir / "environment.json",
            {
                "python": platform.python_version(),
                "system": platform.system(),
                "machine": platform.machine(),
                "packages": versions,
                "source_sha256": {
                    str(p): file_digest(p) for p in sorted(Path("src/flywheel").glob("*.py"))
                },
                "dependency_lock_sha256": file_digest(Path("requirements-lock.txt")),
            },
        )
        evidence = {
            p.name: file_digest(p)
            for p in sorted(args.report_dir.iterdir())
            if p.is_file() and p.name != "artifact_manifest.json"
        }
        write_json(args.report_dir / "artifact_manifest.json", evidence)
        print(
            f"Generated {result['sample_count']} samples; {result['augmentation']['generated']} augmentations; candidate {result['holdout_regression']['gate']}"
        )
        return
    if args.command == "generate":
        generate(args.data_dir, config)
        return
    samples = read_jsonl(args.data_dir / "samples.jsonl")
    if args.command == "validate":
        print(validate(samples, args.data_dir, schema))
    elif args.command == "infer":
        validate(samples, args.data_dir, schema)
        adapter = (
            ReferenceAdapter(args.version)
            if args.adapter == "reference"
            else APIAdapter.from_env(
                args.api_cache,
                config["prompt_version"],
                input_price=args.input_price,
                output_price=args.output_price,
            )
        )
        try:
            write_jsonl(
                args.outputs, infer(samples, args.data_dir, adapter, config["prompt_version"])
            )
        finally:
            if isinstance(adapter, APIAdapter):
                adapter.close()
    elif args.command == "evaluate":
        reviews = load_reviews(args.reviews) if args.reviews else None
        if reviews and not set(reviews).issubset({s["sample_id"] for s in samples}):
            raise ValueError("Review contains unknown sample IDs")
        rows = score(samples, read_jsonl(args.outputs), reviews)
        write_jsonl(args.report_dir / "scores.jsonl", rows)
        write_json(args.report_dir / "metrics.json", summarize(rows, config))
    elif args.command == "prioritize":
        write_jsonl(
            args.report_dir / "priority_queue.jsonl",
            prioritize(samples, read_jsonl(args.old_scores), config),
        )
    else:
        write_json(
            args.report_dir / "comparison.json",
            compare(read_jsonl(args.old_scores), read_jsonl(args.new_scores), config),
        )


if __name__ == "__main__":
    main()
