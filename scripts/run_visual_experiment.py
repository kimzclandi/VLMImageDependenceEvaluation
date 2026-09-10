"""Run from repo root with PYTHONPATH=src; freeze before inference, retain raw outputs."""

import argparse
import importlib.metadata
import platform
import time
from pathlib import Path

from flywheel.io import digest, file_digest, read_json, read_jsonl, write_json, write_jsonl
from flywheel.local_vlm import MODEL, PROMPTS, REVISION, LocalVLM, VisualInput, cache_key
from flywheel.visual_experiment import VERSION, audit, build, produce, score, summarize

p = argparse.ArgumentParser()
p.add_argument("--freeze", action="store_true")
p.add_argument("--snapshot", type=Path)
args = p.parse_args()
root = Path("data/visual_v2")
out = Path("reports/real_vlm")
protocol_path = out / "protocol.json"
if args.freeze:
    if protocol_path.exists():
        raise SystemExit("Protocol already frozen; do not overwrite")
    rows = build(root)
    protocol = {
        "dataset_version": VERSION,
        "dataset_sha256": digest(rows),
        "model": MODEL,
        "revision": REVISION,
        "prompts": PROMPTS,
        "max_new_tokens": 16,
        "do_sample": False,
        "device": "cpu",
        "dtype": "float32",
        "attention": "eager",
        "seed": 91027,
        "n": 72,
        "families": 24,
        "dev_families": 12,
        "holdout_families": 12,
        "hypothesis": "Explicit object inspection improves visual judgments over the short baseline.",
        "primary": "paired holdout accuracy, all 36 questions incl errors",
        "secondary": "format validity, task accuracy, paired fixes/regressions; descriptive only",
        "stopping": "one fixed comparison; no holdout-driven revisions",
        "decoding": "unconstrained greedy; same output budget; strict whole-answer parser",
        "production": "dev answer mismatches only, max six distinct families, translation augmentation; no training",
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_json(protocol_path, protocol)
    print("Frozen", digest(protocol))
    raise SystemExit()
protocol = read_json(protocol_path)
rows = read_jsonl(root / "samples.jsonl")
if (
    digest(rows) != protocol["dataset_sha256"]
    or protocol["prompts"] != PROMPTS
    or protocol["revision"] != REVISION
):
    raise ValueError("Frozen contract changed")
audit(rows, root)
if args.snapshot is None:
    from huggingface_hub import snapshot_download

    args.snapshot = Path(
        snapshot_download(
            MODEL,
            revision=REVISION,
            cache_dir="work/hf",
            allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md"],
        )
    )
versions = {
    n: importlib.metadata.version(n) for n in ("torch", "transformers", "Pillow", "tokenizers")
}
identity = {
    "protocol_sha256": digest(protocol),
    "weights_sha256": file_digest(args.snapshot / "model.safetensors"),
    "versions": versions,
    "python": platform.python_version(),
    "machine": platform.machine(),
    "snapshot_config_sha256": digest(
        {f.name: file_digest(f) for f in args.snapshot.iterdir() if f.is_file()}
    ),
}
write_json(out / "environment.json", identity)
model = LocalVLM(args.snapshot)
outputs = []
# Both arms interleaved for each sample; no intermediate accuracy is inspected.
for r in rows:
    for arm in ("baseline", "observe"):
        item = VisualInput((root / r["image_path"]).read_bytes(), r["question"])
        key = cache_key(item, arm, identity)
        cache = Path("work/visual_cache") / (key + ".json")
        if cache.exists():
            record = read_json(cache)
        else:
            start = time.perf_counter()
            try:
                raw = model.predict(item, arm)
                error = None
            except Exception as exc:
                raw = ""
                error = type(exc).__name__
            record = {
                "raw_output": raw,
                "error": error,
                "latency_seconds": time.perf_counter() - start,
                "cache_key": key,
                "image_sha256": r["image_sha256"],
            }
            if error is None:
                write_json(cache, record)
        outputs.append({**record, "sample_id": r["sample_id"], "arm": arm})
        write_jsonl(out / "outputs.jsonl", outputs)
    print(f"Completed {len(outputs)}/144", flush=True)
scores = score(rows, outputs)
write_jsonl(out / "scores.jsonl", scores)
queue, children = produce(rows, scores, root / "augmentation")
write_jsonl(out / "review_queue.jsonl", queue)
summary = summarize(scores)
summary.update(
    protocol_sha256=digest(protocol),
    augmentation_count=len(children),
    review_queue_count=len(queue),
    training_performed=False,
)
write_json(out / "summary.json", summary)
write_json(
    out / "artifact_manifest.json",
    {
        str(f): file_digest(f)
        for base in (root, out)
        for f in sorted(base.rglob("*"))
        if f.is_file() and f.name != "artifact_manifest.json"
    },
)
print(summary)
