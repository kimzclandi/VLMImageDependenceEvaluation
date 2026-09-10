import copy
from dataclasses import fields
from pathlib import Path

import pytest

from flywheel.io import read_jsonl
from flywheel.local_vlm import VisualInput, cache_key
from flywheel.visual_experiment import audit, parse, produce, score

ROOT = Path(__file__).resolve().parents[1]


def test_pixels_only_boundary():
    assert {f.name for f in fields(VisualInput)} == {"image", "question"}
    with pytest.raises(TypeError):
        VisualInput(b"png", "question", ground_truth="yes")


def test_cache_invalidates_every_input():
    x = VisualInput(b"png", "q")
    original = cache_key(x, "baseline", {"revision": "a", "weights": "x"})
    assert original != cache_key(
        VisualInput(b"changed", "q"), "baseline", {"revision": "a", "weights": "x"}
    )
    assert original != cache_key(
        VisualInput(b"png", "new"), "baseline", {"revision": "a", "weights": "x"}
    )
    assert original != cache_key(x, "observe", {"revision": "a", "weights": "x"})
    assert original != cache_key(x, "baseline", {"revision": "b", "weights": "x"})
    assert original != cache_key(x, "baseline", {"revision": "a", "weights": "y"})


@pytest.mark.parametrize(
    "raw,task,expected",
    [
        ("Yes.", "existence", "yes"),
        ("yes or no", "existence", None),
        ("There are 2", "counting", None),
        ("2", "counting", "2"),
        ("", "spatial", None),
        ("5", "counting", None),
    ],
)
def test_strict_parser(raw, task, expected):
    assert parse(raw, task) == expected


def test_missing_errors_denominator_and_duplicates():
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")[:1]
    scores = score(rows, [])
    assert len(scores) == 2 and not any(s["correct"] for s in scores)
    output = {
        "sample_id": rows[0]["sample_id"],
        "arm": "baseline",
        "raw_output": rows[0]["ground_truth"],
        "error": "runtime",
        "image_sha256": rows[0]["image_sha256"],
    }
    assert not any(s["correct"] for s in score(rows, [output]))
    with pytest.raises(ValueError):
        score(rows, [output, output])


def test_family_and_image_leakage():
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")
    audit(rows, ROOT / "data/visual_v2")
    bad = copy.deepcopy(rows)
    bad[0]["split"] = "holdout"
    with pytest.raises(ValueError, match="leakage"):
        audit(bad, ROOT / "data/visual_v2")
    bad = copy.deepcopy(rows)
    bad[0]["family"] = "new-family"
    bad[0]["split"] = "holdout"
    with pytest.raises(ValueError, match="leakage"):
        audit(bad, ROOT / "data/visual_v2")


def test_holdout_never_produces(tmp_path):
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")
    scores = score(rows, [])
    for s in scores:
        s.update(valid=True, error=None)
    queue, children = produce(rows, scores, tmp_path)
    assert children and all(c["split"] == "dev" and c["parent_id"] for c in children)
    assert all(not q["production_eligible"] for q in queue if q["split"] == "holdout")
    assert all(
        c["ground_truth"]
        == next(r["ground_truth"] for r in rows if r["sample_id"] == c["parent_id"])
        for c in children
    )


def test_forged_holdout_score_cannot_produce(tmp_path):
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")
    scores = score(rows, [])
    target = next(s for s in scores if s["split"] == "holdout")
    target.update(split="dev", valid=True, error=None)
    with pytest.raises(ValueError, match="provenance"):
        produce(rows, scores, tmp_path)
    assert not list(tmp_path.rglob("*.png"))


def test_stale_image_output_rejected():
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")[:1]
    output = {
        "sample_id": rows[0]["sample_id"],
        "arm": "baseline",
        "raw_output": rows[0]["ground_truth"],
        "error": None,
        "image_sha256": "stale",
    }
    with pytest.raises(ValueError, match="identity"):
        score(rows, [output])


def test_duplicate_input_rows_rejected():
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")[:1]
    with pytest.raises(ValueError, match="Duplicate"):
        score(rows + rows, [])
