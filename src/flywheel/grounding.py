"""Version 3: balanced counterfactual families and preregistered image interventions."""

import argparse
import fcntl
import importlib.metadata
import random
import time
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from flywheel.io import digest, file_digest, read_json, write_json
from flywheel.local_vlm import MODEL, PROMPTS, REVISION, LocalVLM, VisualInput
from flywheel.visual_experiment import parse

DATA = Path("data/visual_v3")
OUT = Path("reports/grounding_v3")
ARMS = ("real", "blank", "mismatch")
SEED = 911203


def immutable(path, value):
    if path.exists():
        if read_json(path) != value:
            raise ValueError(f"Immutable artifact changed: {path}")
    else:
        write_json(path, value)


def build(root):
    rng = random.Random(SEED)
    rows = []
    for split in ("dev", "holdout"):
        for task in ("counting", "existence", "spatial"):
            for family in range(5):
                fid = digest([SEED, split, task, family])[:16]
                positions = [
                    (100 + rng.randrange(35), 95 + rng.randrange(30)),
                    (340 + rng.randrange(35), 95 + rng.randrange(30)),
                    (100 + rng.randrange(35), 260 + rng.randrange(30)),
                    (340 + rng.randrange(35), 260 + rng.randrange(30)),
                ]
                rng.shuffle(positions)
                variants = range(5) if task == "counting" else range(2)
                for v in variants:
                    sid = digest([fid, v])[:20]
                    im = Image.new("RGB", (512, 384), "white")
                    d = ImageDraw.Draw(im)
                    objects = []
                    if task == "spatial":
                        coords = sorted(positions[:], key=lambda p: p[0])
                        objects = [
                            ("red", "circle", coords[0 if v else -1]),
                            ("blue", "square", coords[-1 if v else 0]),
                        ]
                        q = "Is the red circle to the left of the blue square? Compare centers. Answer yes or no."
                    else:
                        for k, xy in enumerate(positions):
                            color = "red" if (k < v if task == "counting" else k == 0) else "blue"
                            shape = (
                                "square" if task == "existence" and k == 0 and v == 0 else "circle"
                            )
                            objects.append((color, shape, xy))
                        q = (
                            "How many red circles are visible? Answer an integer from 0 to 4."
                            if task == "counting"
                            else "Is there a red circle? Answer yes or no."
                        )
                    for color, shape, (x, y) in objects:
                        box = (x - 27, y - 27, x + 27, y + 27)
                        (d.ellipse if shape == "circle" else d.rectangle)(box, fill=color)
                    image = f"images/{sid}.png"
                    (root / "images").mkdir(parents=True, exist_ok=True)
                    im.save(root / image)
                    rows.append(
                        dict(
                            sample_id=sid,
                            family=fid,
                            split=split,
                            task=task,
                            question=q,
                            ground_truth=str(v) if task == "counting" else ("yes" if v else "no"),
                            image_path=image,
                            image_sha256=file_digest(root / image),
                            scene=objects,
                            parent_id=None,
                            generation_seed=SEED,
                            label_source="deterministic geometry oracle",
                            version="visual_v3",
                        )
                    )
    for r in rows:
        donors = [
            s for s in rows if s["family"] == r["family"] and s["ground_truth"] != r["ground_truth"]
        ]
        donor = rng.choice(donors)
        r["donor_id"] = donor["sample_id"]
        r["donor_gold"] = donor["ground_truth"]
    Image.new("RGB", (512, 384), "white").save(root / "blank.png")
    return rows


def audit(rows, root):
    byid = {r["sample_id"]: r for r in rows}
    if len(byid) != len(rows):
        raise ValueError("Duplicate sample")
    families, hashes = {}, set()
    for r in rows:
        if families.setdefault(r["family"], r["split"]) != r["split"]:
            raise ValueError("Family leakage")
        if r["image_sha256"] in hashes or file_digest(root / r["image_path"]) != r["image_sha256"]:
            raise ValueError("Duplicate or changed pixels")
        hashes.add(r["image_sha256"])
        donor = byid[r["donor_id"]]
        if (
            donor["family"] != r["family"]
            or donor["split"] != r["split"]
            or donor["ground_truth"] == r["ground_truth"]
            or donor["question"] != r["question"]
        ):
            raise ValueError("Invalid counterfactual donor")
    distributions = {}
    for split in ("dev", "holdout"):
        distributions[split] = {}
        for task in ("counting", "existence", "spatial"):
            counts = Counter(
                r["ground_truth"] for r in rows if r["split"] == split and r["task"] == task
            )
            if len(set(counts.values())) != 1 or len(counts) != (5 if task == "counting" else 2):
                raise ValueError("Unbalanced answer coverage")
            distributions[split][task] = dict(counts)
    # Foreground-sensitive near duplicate audit: normalized RGB MAE, not background-dominated pHash.
    images = {r["sample_id"]: Image.open(root / r["image_path"]).convert("RGB") for r in rows}
    near = []
    minimum = 1.0
    for a in (r for r in rows if r["split"] == "dev"):
        for b in (r for r in rows if r["split"] == "holdout"):
            mae = sum(
                ImageStat.Stat(
                    ImageChops.difference(images[a["sample_id"]], images[b["sample_id"]])
                ).mean
            ) / (3 * 255)
            minimum = min(minimum, mae)
            if mae < 0.002:
                near.append([a["sample_id"], b["sample_id"], mae])
    if near:
        raise ValueError(
            "Cross-split near duplicate; dataset design must be revised before inference"
        )
    return dict(
        distributions=distributions,
        cross_split_near_duplicates=near,
        min_cross_split_rgb_mae=minimum,
        near_threshold=0.002,
        families=len(families),
        images=len(rows),
        limitations="Shared generator/templates; family isolation is not out-of-distribution evidence. MAE does not exclude semantic near-duplicates.",
    )


def snapshot_identity(snapshot):
    return {p.name: file_digest(p) for p in sorted(snapshot.iterdir()) if p.is_file()}


def sources():
    return {
        p: file_digest(Path(p))
        for p in (
            "src/flywheel/grounding.py",
            "src/flywheel/local_vlm.py",
            "src/flywheel/visual_experiment.py",
            "src/flywheel/io.py",
        )
    }


def freeze(snapshot):
    if (OUT / "protocol.json").exists():
        raise ValueError("Already frozen")
    rows = build(DATA)
    immutable(DATA / "samples.json", rows)
    immutable(DATA / "audit.json", audit(rows, DATA))
    immutable(
        OUT / "protocol.json",
        dict(
            frozen_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            dataset=digest(rows),
            blank_sha256=file_digest(DATA / "blank.png"),
            model=MODEL,
            revision=REVISION,
            snapshot=snapshot_identity(snapshot),
            sources=sources(),
            versions={
                p: importlib.metadata.version(p)
                for p in ("torch", "transformers", "Pillow", "tokenizers")
            },
            prompt=PROMPTS["baseline"],
            parameters=dict(
                max_new_tokens=16,
                do_sample=False,
                device="cpu",
                dtype="float32",
                attention="eager",
                threads=4,
            ),
            arms=list(ARMS),
            seed=SEED,
            primary="holdout task-macro accuracy real minus blank; all questions including errors",
            secondary="real minus mismatch (scored against ORIGINAL gold), format, task slices, paired fixes/regressions, output sensitivity",
            statistical_unit="scene family; 2000 paired family bootstrap draws stratified by task; seed 911203",
            decision="Evidence of visual contribution only if real-minus-blank macro CI lower bound > 0 and real > mismatch; descriptive synthetic scope",
            stopping="Run all 270 generations once, retain errors; no holdout-based changes or model/prompt search",
            mismatch="Seeded other variant of same family; identical question, provably different answer; score original gold, separately report donor consistency",
            prior="dev-majority by task, lexicographic tie; constant question within task cannot encode variant label",
            leakage="No text, IDs or filenames in pixel tensor/prompt. Four objects for counting/existence; wide horizontal center separation for spatial. All variants stay in family split.",
        ),
    )


def score(rows, outputs, root=DATA):
    byid = {r["sample_id"]: r for r in rows}
    expected = {(r["sample_id"], a) for r in rows for a in ARMS}
    found = {}
    for o in outputs:
        key = o["sample_id"], o["arm"]
        if key not in expected or key in found:
            raise ValueError("Duplicate/unexpected output")
        r = byid[o["sample_id"]]
        sha = (
            r["image_sha256"]
            if o["arm"] == "real"
            else byid[r["donor_id"]]["image_sha256"]
            if o["arm"] == "mismatch"
            else file_digest(root / "blank.png")
        )
        if o["image_sha256"] != sha:
            raise ValueError("Wrong intervention image")
        found[key] = o
    scores = []
    for r in rows:
        for arm in ARMS:
            o = found.get((r["sample_id"], arm), dict(raw_output="", error="missing_output"))
            pred = None if o["error"] else parse(o["raw_output"], r["task"])
            scores.append(
                dict(
                    sample_id=r["sample_id"],
                    family=r["family"],
                    task=r["task"],
                    split=r["split"],
                    arm=arm,
                    prediction=pred,
                    correct=pred == r["ground_truth"],
                    valid=pred is not None,
                    gold=r["ground_truth"],
                    donor_gold=r["donor_gold"],
                    raw_output=o["raw_output"],
                    error=o["error"],
                )
            )
    return scores


def summarize(scores):
    result = {}
    for split in ("dev", "holdout"):
        part = [s for s in scores if s["split"] == split]
        stats = {}
        for arm in ARMS:
            p = [s for s in part if s["arm"] == arm]
            tasks = {
                t: dict(
                    n=len(q := [s for s in p if s["task"] == t]),
                    correct=sum(s["correct"] for s in q),
                    accuracy=sum(s["correct"] for s in q) / len(q),
                    valid=sum(s["valid"] for s in q) / len(q),
                )
                for t in ("counting", "existence", "spatial")
            }
            stats[arm] = dict(
                n=len(p),
                correct=sum(s["correct"] for s in p),
                accuracy=sum(s["correct"] for s in p) / len(p),
                valid=sum(s["valid"] for s in p) / len(p),
                task_macro_accuracy=sum(t["accuracy"] for t in tasks.values()) / 3,
                tasks=tasks,
                system_errors=sum(s["error"] is not None for s in p),
            )
        real = {s["sample_id"]: s for s in part if s["arm"] == "real"}
        for arm in ("blank", "mismatch"):
            p = [s for s in part if s["arm"] == arm]
            rng = random.Random(SEED)
            grouped = {t: {} for t in ("counting", "existence", "spatial")}
            for s in p:
                grouped[s["task"]].setdefault(s["family"], []).append(
                    int(real[s["sample_id"]]["correct"]) - int(s["correct"])
                )
            boot = []
            for _ in range(2000):
                boot.append(
                    sum(
                        sum(sum(v) / len(v) for v in rng.choices(list(g.values()), k=len(g)))
                        / len(g)
                        for g in grouped.values()
                    )
                    / 3
                )
            boot.sort()
            stats["real_vs_" + arm] = dict(
                macro_delta=stats["real"]["task_macro_accuracy"]
                - stats[arm]["task_macro_accuracy"],
                ci95=[boot[49], boot[1949]],
                fixed=sum(real[s["sample_id"]]["correct"] and not s["correct"] for s in p),
                regressed=sum(s["correct"] and not real[s["sample_id"]]["correct"] for s in p),
                raw_output_changed=sum(
                    real[s["sample_id"]]["raw_output"] != s["raw_output"] for s in p
                ),
                both_valid_prediction_changed=sum(
                    real[s["sample_id"]]["valid"]
                    and s["valid"]
                    and real[s["sample_id"]]["prediction"] != s["prediction"]
                    for s in p
                ),
            )
        stats["dev_majority_prior"] = dict(
            micro_accuracy=1 / 3,
            macro_accuracy=0.4,
            rule="counting=0, existence=no, spatial=no (dev tie broken lexicographically)",
        )
        result[split] = stats
    return result


def run(snapshot, limit=None):
    protocol = read_json(OUT / "protocol.json")
    rows = read_json(DATA / "samples.json")
    if (
        protocol["dataset"] != digest(rows)
        or protocol["sources"] != sources()
        or protocol["snapshot"] != snapshot_identity(snapshot)
        or protocol["blank_sha256"] != file_digest(DATA / "blank.png")
    ):
        raise ValueError("Frozen protocol drift")
    if protocol["versions"] != {p: importlib.metadata.version(p) for p in protocol["versions"]}:
        raise ValueError("Environment drift")
    audit(rows, DATA)
    byid = {r["sample_id"]: r for r in rows}
    identity = digest(protocol)
    model = None
    executed = 0
    with (OUT / ".run.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for r in rows:
            for arm in ARMS:
                path = OUT / "records" / f"{r['sample_id']}-{arm}.json"
                im = DATA / (
                    r["image_path"]
                    if arm == "real"
                    else byid[r["donor_id"]]["image_path"]
                    if arm == "mismatch"
                    else "blank.png"
                )
                key = digest([identity, r["sample_id"], arm, file_digest(im), r["question"]])
                if path.exists():
                    old = read_json(path)
                    if old["key"] != key:
                        raise ValueError("Stale cache")
                    # Errors retained as observations, never a successful cached inference.
                    continue
                if model is None:
                    model = LocalVLM(snapshot)
                start = time.perf_counter()
                try:
                    raw, error = (
                        model.predict(VisualInput(im.read_bytes(), r["question"]), "baseline"),
                        None,
                    )
                except Exception as exc:
                    raw, error = "", type(exc).__name__
                immutable(
                    path,
                    dict(
                        sample_id=r["sample_id"],
                        arm=arm,
                        image_sha256=file_digest(im),
                        key=key,
                        raw_output=raw,
                        error=error,
                        latency_seconds=time.perf_counter() - start,
                        protocol=identity,
                    ),
                )
                executed += 1
                print(f"saved {r['sample_id']} {arm}", flush=True)
                if limit is not None and executed >= limit:
                    return
    analyze()


def analyze():
    rows = read_json(DATA / "samples.json")
    outputs = [read_json(p) for p in sorted((OUT / "records").glob("*.json"))]
    scores = score(rows, outputs)
    immutable(OUT / "scores.json", scores)
    immutable(
        OUT / "summary.json",
        dict(
            results=summarize(scores),
            complete=len(outputs) == len(rows) * 3,
            observed=len(outputs),
            expected=len(rows) * 3,
            training=False,
        ),
    )
    failures = []
    for s in scores:
        if s["split"] == "dev" and not s["correct"] and s["arm"] == "real":
            paired = [p for p in scores if p["sample_id"] == s["sample_id"]]
            failures.append(
                dict(
                    **s,
                    symptom="system"
                    if s["error"]
                    else "format"
                    if not s["valid"]
                    else "answer_mismatch",
                    competing_hypotheses=[
                        "visual representation inadequate",
                        "answer prior dominates",
                        "task instruction misunderstood",
                    ],
                    intervention_results=paired,
                    root_cause_status="unresolved; intervention is behavioral evidence, not internal localization",
                    production_decision="Do not auto-augment or train this VLM from this evidence",
                    review_status="pending human review",
                )
            )
    immutable(OUT / "dev_failures.json", failures)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["freeze", "run", "analyze"])
    p.add_argument("--snapshot", type=Path)
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    if a.action == "freeze":
        freeze(a.snapshot)
    elif a.action == "run":
        run(a.snapshot, a.limit)
    else:
        analyze()


if __name__ == "__main__":
    main()
