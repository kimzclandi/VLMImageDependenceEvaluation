from pathlib import Path

import pytest

from flywheel.io import read_json, read_jsonl, write_json
from flywheel.visual_integrity import load_cache, validate_protocol

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_new_tokens", 32),
        ("do_sample", True),
        ("device", "mps"),
        ("dtype", "float16"),
        ("attention", "sdpa"),
        ("model", "other"),
        ("n", 71),
        ("dev_families", 11),
    ],
)
def test_protocol_drift(field, value):
    protocol = read_json(ROOT / "reports/real_vlm/protocol.json")
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")
    validate_protocol(protocol, rows)
    protocol[field] = value
    with pytest.raises(ValueError, match=field):
        validate_protocol(protocol, rows)


def test_corrupt_and_failed_caches_are_misses(tmp_path):
    path = tmp_path / "cache.json"
    assert load_cache(path, "key", "image") is None
    path.write_text("{broken")
    assert load_cache(path, "key", "image") is None
    good = dict(
        cache_key="key", image_sha256="image", error=None, raw_output="yes", latency_seconds=1.0
    )
    write_json(path, good)
    assert load_cache(path, "key", "image") == good
    for field, value in [
        ("cache_key", "other"),
        ("image_sha256", "stale"),
        ("error", "runtime"),
        ("raw_output", None),
        ("latency_seconds", -1),
        ("latency_seconds", True),
    ]:
        write_json(path, {**good, field: value})
        assert load_cache(path, "key", "image") is None
