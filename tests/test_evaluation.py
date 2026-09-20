import copy

import pytest

from flywheel.adapters import ReferenceAdapter
from flywheel.data import generate
from flywheel.evaluation import (
    bootstrap,
    compare,
    infer,
    load_reviews,
    normalize,
    parse,
    score,
    summarize,
)
from flywheel.strategy import prioritize


@pytest.mark.parametrize(
    ("raw", "kind", "answer"),
    [
        ('{"answer":" YES "}', "exists", " YES "),
        ('{"answer":2}', "count", "2"),
        ('{"answer":"o2, o1"}', "select", "o2, o1"),
        ('{"answer":true}', "exists", None),
        ('{"answer":-1}', "count", None),
        ('{"answer":"o1,o1"}', "select", None),
        ('{"answer":"yes","reason":"x"}', "exists", None),
        ("yes", "exists", None),
        ('{"answer":[]}', "select", None),
        ('{"answer":"maybe"}', "exists", None),
    ],
)
def test_answer_contract(raw, kind, answer):
    result, error = parse(raw, {"kind": kind})
    assert result == answer
    assert (error is None) == (answer is not None)
    assert normalize(" O2, o1 ") == "o1,o2"


def test_cluster_bootstrap_and_pairing():
    rows = [{"group_id": str(i), "correct": bool(i % 2)} for i in range(10)]
    assert bootstrap(rows, repeats=100) == bootstrap(rows + rows, repeats=100)
    assert bootstrap([], repeats=100) == [None, None]
    assert bootstrap(rows[:1], repeats=100) == [None, None]


def test_scoring_errors_denominators_and_human_review(tmp_path, config):
    samples = generate(tmp_path, config)
    outputs = infer(samples, tmp_path, ReferenceAdapter(), config["prompt_version"])
    outputs[0].update(error_status="http_429", parsed_answer=None)
    outputs[1].update(
        raw_output="invalid JSON", parse_error="output_format_error", parsed_answer=None
    )
    outputs[2].update(error_status="refusal", parsed_answer=None)
    rows = score(samples, outputs)
    assert [r["failure_type"] for r in rows[:3]] == [
        "system_or_api_error",
        "output_format_error",
        "abstention_or_refusal",
    ]
    overall = summarize(rows, config)["overall"]
    assert overall["n"] == 36 and overall["error_rate"] == pytest.approx(2 / 36)
    assert overall["unparseable_rate"] == pytest.approx(1 / 36)
    p = tmp_path / "review.csv"
    p.write_text(
        f"sample_id,failure_type,note\n{samples[0]['sample_id']},annotation_error,Manual label check\n"
    )
    reviewed = score(samples, outputs, load_reviews(p))
    assert reviewed[0]["failure_type"] == "annotation_error"
    assert reviewed[0]["correct"] == rows[0]["correct"]
    assert samples[0]["sample_id"] not in {
        r["sample_id"] for r in prioritize(samples, reviewed, config)
    }
    outputs[0]["sample_sha256"] = "different"
    with pytest.raises(ValueError, match="different sample"):
        score(samples, outputs)


def test_pair_regression_rejects_changed_data(tmp_path, config):
    samples = generate(tmp_path, config)
    v1 = score(samples, infer(samples, tmp_path, ReferenceAdapter("v1"), "p1"))
    v2 = score(samples, infer(samples, tmp_path, ReferenceAdapter("v2"), "p1"))
    result = compare(v1, v2, config)
    assert result["gate"] == "REJECT"
    assert "counting" in result["regressed_tasks"] and result["regressed_ids"]
    with pytest.raises(ValueError, match="identical"):
        compare(v1, v2[:-1], config)
    changed = copy.deepcopy(v2)
    changed[0]["sample_sha256"] = "not-frozen"
    with pytest.raises(ValueError, match="frozen"):
        compare(v1, changed, config)


def test_priority_weights_isolation_and_explanation(tmp_path, config):
    samples = generate(tmp_path, config)
    rows = score(samples, infer(samples, tmp_path, ReferenceAdapter("v1"), "p1"))
    queue = prioritize(samples, rows, config)
    by_id = {s["sample_id"]: s for s in samples}
    assert queue and all(by_id[r["sample_id"]]["split"] == "dev" for r in queue)
    selected = [r for r in queue if r["selected"]]
    assert len({by_id[r["sample_id"]]["group_id"] for r in selected}) == len(selected)
    for row in queue:
        expected = (
            sum(config["weights"][k] * v for k, v in row["factors"].items())
            / row["production_cost_proxy"]
        )
        assert row["priority_score"] == pytest.approx(expected, abs=1e-6)
    with pytest.raises(ValueError, match="sum to one"):
        prioritize(samples, rows, {**config, "weights": {"severity": 3}})


@pytest.mark.parametrize(
    "field,value",
    [
        ("parsed_answer", "fabricated"),
        ("raw_output", "not JSON"),
        ("parse_error", "output_format_error"),
        ("dataset_version", "another-dataset"),
    ],
)
def test_scoring_rejects_inconsistent_saved_output(tmp_path, config, field, value):
    samples = generate(tmp_path, config)
    outputs = infer(samples, tmp_path, ReferenceAdapter(), config["prompt_version"])
    outputs[0][field] = value
    with pytest.raises(ValueError):
        score(samples, outputs)
