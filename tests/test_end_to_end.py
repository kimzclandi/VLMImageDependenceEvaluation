from pathlib import Path

from flywheel.augmentation import OPERATORS, fingerprint
from flywheel.io import read_jsonl
from flywheel.pipeline import demo


def test_offline_end_to_end_and_augmentation_integrity(tmp_path, config):
    config = {**config, "groups_per_task": 9, "selection_budget": 12}
    result = demo(
        config, tmp_path / "data", tmp_path / "reports", Path("schemas/sample.schema.json")
    )
    assert result["sample_count"] == 108
    assert result["holdout_regression"]["gate"] == "REJECT"
    assert result["holdout_regression"]["delta"] > 0
    samples = read_jsonl(tmp_path / "data/samples.jsonl")
    aug = read_jsonl(tmp_path / "data/augmentation/samples.jsonl")
    by_id = {s["sample_id"]: s for s in samples}
    assert set(r["mutation"] for r in aug) == set(OPERATORS)
    assert {fingerprint(r) for r in aug}.isdisjoint({fingerprint(r) for r in samples})
    for row in aug:
        assert row["split"] == "augmentation"
        assert by_id[row["parent_id"]]["split"] == "dev"
        if row["mutation"] == "counterfactual":
            assert row["answer_changed"]
        if row["mutation"] == "attribute_substitution":
            assert not row["answer_changed"]
    for version in ("v1", "v2"):
        outputs = read_jsonl(tmp_path / f"reports/{version}_outputs.jsonl")
        assert len(outputs) == 108
        assert all("ground_truth" not in row for row in outputs)
        assert all(row["latency_ms"] >= 0 for row in outputs)
    assert (tmp_path / "reports/EXPERIMENT_REPORT.md").exists()
