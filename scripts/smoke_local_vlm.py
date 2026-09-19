"""One dev-image CPU inference with existing fixed weights, separate from frozen experiments."""

import argparse
import importlib.metadata
import time
from datetime import UTC, datetime
from pathlib import Path

from flywheel.io import digest, file_digest, read_json, write_json
from flywheel.local_vlm import MODEL, REVISION, LocalVLM, VisualInput


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output directory")
    protocol = read_json(Path("reports/grounding_v3/protocol.json"))
    rows = read_json(Path("data/visual_v3/samples.json"))
    if digest(rows) != protocol["dataset"]:
        raise ValueError("Frozen sample identity changed")
    for name, expected in protocol["snapshot"].items():
        if file_digest(args.snapshot / name) != expected:
            raise ValueError(f"Fixed snapshot mismatch: {name}")
    row = next(row for row in rows if row["split"] == "dev")
    image = Path("data/visual_v3") / row["image_path"]
    if file_digest(image) != row["image_sha256"]:
        raise ValueError("Input image changed")
    args.output.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "running",
        "started_utc": datetime.now(UTC).isoformat(),
        "scope": "One existing dev image, actual CPU generation; no training or independent quality evaluation",
        "model": MODEL,
        "revision": REVISION,
        "sample_id": row["sample_id"],
        "image_sha256": row["image_sha256"],
        "question": row["question"],
        "source_sha256": {
            str(path): file_digest(path)
            for path in (Path("scripts/smoke_local_vlm.py"), Path("src/flywheel/local_vlm.py"))
        },
        "packages": {name: importlib.metadata.version(name) for name in protocol["versions"]},
    }
    write_json(args.output / "run.json", result)
    started = time.perf_counter()
    try:
        model = LocalVLM(args.snapshot)
        result["raw_output"] = model.predict(
            VisualInput(image.read_bytes(), row["question"]), "baseline"
        )
        result["status"] = "complete"
    except BaseException as exc:
        result.update(status="failed", error=repr(exc))
        raise
    finally:
        result.update(
            finished_utc=datetime.now(UTC).isoformat(), wall_seconds=time.perf_counter() - started
        )
        write_json(args.output / "run.json", result)
    print(
        "Completed one dev-image generation; see the separate run.json (not a quality experiment)."
    )


if __name__ == "__main__":
    main()
