"""Validate frozen execution settings and cache records before model execution."""

import math
from pathlib import Path

from flywheel.io import digest, read_json
from flywheel.local_vlm import MODEL, PROMPTS, REVISION


def validate_protocol(protocol, rows):
    expected = {
        "model": MODEL,
        "revision": REVISION,
        "prompts": PROMPTS,
        "max_new_tokens": 16,
        "do_sample": False,
        "device": "cpu",
        "dtype": "float32",
        "attention": "eager",
        "dataset_sha256": digest(rows),
        "n": len(rows),
        "families": len({r["family"] for r in rows}),
        "dev_families": len({r["family"] for r in rows if r["split"] == "dev"}),
        "holdout_families": len({r["family"] for r in rows if r["split"] == "holdout"}),
    }
    for field, value in expected.items():
        if protocol.get(field) != value:
            raise ValueError(f"Frozen contract mismatch: {field}")


def load_cache(path: Path, key: str, image_sha256: str):
    """A damaged, failed or misidentified cache is a miss, never a scored prediction."""
    try:
        record = read_json(path)
        if not isinstance(record, dict):
            return None
        latency = record.get("latency_seconds")
        if (
            record.get("cache_key") != key
            or record.get("image_sha256") != image_sha256
            or record.get("error") is not None
            or not isinstance(record.get("raw_output"), str)
            or isinstance(latency, bool)
            or not isinstance(latency, (int, float))
            or not math.isfinite(latency)
            or latency < 0
        ):
            return None
        return record
    except (OSError, ValueError):
        return None
