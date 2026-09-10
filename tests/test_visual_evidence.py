"""Verify committed actual evidence without downloading a model in CI."""

from pathlib import Path

import pytest

from flywheel.io import digest, file_digest, read_json, read_jsonl
from flywheel.local_vlm import WEIGHT_SHA256
from flywheel.visual_experiment import score, summarize

ROOT = Path(__file__).resolve().parents[1]


def test_saved_evidence_integrity():
    report = ROOT / "reports/real_vlm"
    if not (report / "summary.json").exists():
        pytest.skip("Inference still running")
    rows = read_jsonl(ROOT / "data/visual_v2/samples.jsonl")
    protocol = read_json(report / "protocol.json")
    assert digest(rows) == protocol["dataset_sha256"]
    assert read_json(report / "environment.json")["weights_sha256"] == WEIGHT_SHA256
    outputs = read_jsonl(report / "outputs.jsonl")
    assert len(outputs) == 144
    images = {r["sample_id"]: r["image_sha256"] for r in rows}
    assert all(o["image_sha256"] == images[o["sample_id"]] for o in outputs)
    scores = score(rows, outputs)
    assert scores == read_jsonl(report / "scores.jsonl")
    actual = read_json(report / "summary.json")
    for split, metrics in summarize(scores).items():
        assert metrics == actual[split]
    for name, sha in read_json(report / "artifact_manifest.json").items():
        assert file_digest(ROOT / name) == sha, name
