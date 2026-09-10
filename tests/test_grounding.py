import copy

import pytest
from PIL import Image

from flywheel.grounding import ARMS, audit, build, score, summarize
from flywheel.io import file_digest


def test_balanced_family_and_interventions(tmp_path):
    rows = build(tmp_path)
    report = audit(rows, tmp_path)
    assert len(rows) == 90 and report["families"] == 30
    assert not report["cross_split_near_duplicates"]
    byid = {r["sample_id"]: r for r in rows}
    outputs = []
    for r in rows:
        for arm in ARMS:
            sha = (
                r["image_sha256"]
                if arm == "real"
                else byid[r["donor_id"]]["image_sha256"]
                if arm == "mismatch"
                else file_digest(tmp_path / "blank.png")
            )
            outputs.append(
                dict(
                    sample_id=r["sample_id"],
                    arm=arm,
                    image_sha256=sha,
                    raw_output=r["ground_truth"] if arm == "real" else "invalid",
                    error=None,
                )
            )
    result = summarize(score(rows, outputs, tmp_path))
    assert result["holdout"]["real"]["accuracy"] == 1
    assert result["holdout"]["real_vs_blank"]["macro_delta"] == 1
    assert result["holdout"]["real_vs_blank"]["ci95"] == [1, 1]
    missing = score(rows, outputs[:-1], tmp_path)
    assert len(missing) == 270
    assert sum(r["error"] == "missing_output" for r in missing) == 1
    with pytest.raises(ValueError, match="Duplicate"):
        score(rows, outputs + [outputs[0]], tmp_path)
    bad = copy.deepcopy(outputs)
    bad[0]["image_sha256"] = "forged"
    with pytest.raises(ValueError, match="image"):
        score(rows, bad, tmp_path)
    rows[0]["donor_id"] = rows[0]["sample_id"]
    with pytest.raises(ValueError, match="donor"):
        audit(rows, tmp_path)


def test_corrupted_pixels_rejected(tmp_path):
    rows = build(tmp_path)
    Image.new("RGB", (512, 384)).save(tmp_path / rows[0]["image_path"])
    with pytest.raises(ValueError, match="pixels"):
        audit(rows, tmp_path)
