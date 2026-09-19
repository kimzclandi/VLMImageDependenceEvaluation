"""Recompute all v3 metrics from original output records; no model execution."""

from collections import Counter
from pathlib import Path

from flywheel.grounding import ARMS, DATA, OUT, audit, score, sources, summarize
from flywheel.io import digest, file_digest, read_json

rows = read_json(DATA / "samples.json")
protocol = read_json(OUT / "protocol.json")
assert digest(rows) == protocol["dataset"]
assert sources() == protocol["sources"]
audit(rows, DATA)
records = [read_json(p) for p in sorted((OUT / "records").glob("*.json"))]
assert len(records) == len(rows) * len(ARMS)
byid = {r["sample_id"]: r for r in rows}
for record in records:
    r = byid[record["sample_id"]]
    assert record["protocol"] == digest(protocol)
    expected = digest(
        [digest(protocol), r["sample_id"], record["arm"], record["image_sha256"], r["question"]]
    )
    assert record["key"] == expected
    assert record["latency_seconds"] >= 0
scores = score(rows, records)
assert scores == read_json(OUT / "scores.json")
assert summarize(scores) == read_json(OUT / "summary.json")["results"]
# Derive the prior from dev only, rather than trusting hard-coded percentages.

prior = {
    t: sorted(
        Counter(r["ground_truth"] for r in rows if r["split"] == "dev" and r["task"] == t).items(),
        key=lambda x: (-x[1], x[0]),
    )[0][0]
    for t in ("counting", "existence", "spatial")
}
hold = [r for r in rows if r["split"] == "holdout"]
assert sum(prior[r["task"]] == r["ground_truth"] for r in hold) / len(hold) == 1 / 3
if (OUT / "artifact_manifest.json").exists():
    for name, sha in read_json(OUT / "artifact_manifest.json").items():
        assert file_digest(Path(name)) == sha, name
print(
    f"Verified {len(records)} original generations, all denominators, pairing, metrics, priors and frozen source identities"
)
