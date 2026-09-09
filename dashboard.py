"""Evidence-first Streamlit dashboard. All displayed values come from saved runs."""

import os
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from flywheel.io import read_json, read_jsonl, safe_path

ROOT = Path(__file__).resolve().parent
REPORT = Path(os.environ.get("FLYWHEEL_REPORT_DIR", str(ROOT / "reports/demo")))
DATA = Path(os.environ.get("FLYWHEEL_DATA_DIR", str(ROOT / "data/sample")))
st.set_page_config(page_title="Embodied VLM · Data Flywheel Lab", page_icon="◈", layout="wide")
st.html("""<style>
[data-testid="stHeader"] {display:none;}
.block-container {max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem;}
h1,h2,h3 {letter-spacing: -.035em;}
[data-testid="stMetric"] {background:#f4f7fb;border:1px solid #e1e8f0;border-radius:12px;padding:18px;}
[data-testid="stMetricLabel"] {color:#607187;}
[data-testid="stMetricValue"] {font-weight:700;color:#10243a;}
.kicker {color:#087f8c;font-size:12px;font-weight:800;letter-spacing:.16em;}
.lede {color:#617186;font-size:17px;max-width:950px;line-height:1.6;margin-bottom:20px;}
.rail {background:#10243a;color:#cce5ea;padding:14px 20px;border-radius:10px;font-size:13px;word-spacing:3px;}
</style>""")
if not (REPORT / "summary.json").exists():
    st.info("Generate evidence first: flywheel demo")
    st.stop()
summary = read_json(REPORT / "summary.json")
samples = read_jsonl(DATA / "samples.jsonl")
by_id = {s["sample_id"]: s for s in samples}
queue = read_jsonl(REPORT / "priority_queue.jsonl")
old, new = (read_jsonl(REPORT / f"{v}_scores.jsonl") for v in ("v1", "v2"))
augmented = read_jsonl(DATA / "augmentation/samples.jsonl")

with st.sidebar:
    st.markdown("### ◈ FLYWHEEL LAB")
    st.caption("MODEL EVALUATION → DATA DECISIONS")
    page = st.radio(
        "Workspace", ["Overview", "Failure review", "Data production", "Evidence & configuration"]
    )
    st.divider()
    st.markdown("**Experiment**")
    st.code("metadata-reference\nv1 → v2", language=None)
    st.caption(
        "Deterministic rules · Privileged metadata\n\nNo model training or external VLM inference."
    )
    st.markdown("**Dataset**")
    st.caption(
        f"{summary['config']['dataset_version']} · seed {summary['config']['seed']}\n\n{summary['group_count']} scene families · 6 tasks"
    )
    st.divider()
    st.caption(
        "Release decisions use a fixed holdout. Data production uses development failures only."
    )

st.html('<div class="kicker">EMBODIED AI / DATA STRATEGY WORKBENCH</div>')
st.title("Embodied VLM Data Flywheel Lab")
st.html(
    '<div class="lede">Turn model failures into auditable data decisions. Inspect capability gaps, prioritize production, and check every release for regressions.</div>'
)
st.html(
    '<div class="rail">GENERATE → EVALUATE → TRIAGE → PRIORITIZE → AUGMENT → REGRESSION GATE</div>'
)
st.caption(
    "PIPELINE VALIDATION ONLY · The reference adapters read metadata, not pixels. Higher scores do not demonstrate learned model improvement."
)


def bars(
    frame: pd.DataFrame, category: str, value: str, series: str | None = None, percent: bool = True
) -> None:
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            y=alt.Y(f"{category}:N", title=None, sort=None, axis=alt.Axis(labelLimit=200)),
            x=alt.X(
                f"{value}:Q",
                title="Accuracy" if percent else "Samples",
                scale=alt.Scale(domain=[0, 1]) if percent else alt.Undefined,
                axis=alt.Axis(format=".0%" if percent else "d"),
            ),
            tooltip=list(frame.columns),
        )
    )
    if series:
        chart = chart.encode(
            yOffset=f"{series}:N",
            color=alt.Color(
                f"{series}:N",
                scale=alt.Scale(domain=list(frame[series].unique()), range=["#9aaabd", "#008c95"]),
                legend=alt.Legend(orient="top", title=None),
            ),
        )
    else:
        chart = chart.encode(color=alt.value("#008c95"))
    st.altair_chart(
        chart.properties(height=max(180, len(frame[category].unique()) * 52)).configure_view(
            strokeWidth=0
        ),
        width="stretch",
    )


if page == "Overview":
    a, b, c, d = st.columns(4)
    a.metric(
        "Evaluation samples",
        summary["sample_count"],
        f"{summary['group_count']} scene families",
        delta_color="off",
    )
    b.metric(
        "Fixed holdout · v1 → v2",
        f"{summary['metrics']['v2']['split']['holdout']['accuracy']:.1%}",
        f"{summary['holdout_regression']['delta'] * 100:+.1f} pp",
        delta_color="off",
    )
    c.metric(
        "Targeted production",
        summary["augmentation"]["generated"],
        f"{summary['selected_parents']} dev parents",
        delta_color="off",
    )
    d.metric(
        "Candidate release gate",
        summary["holdout_regression"]["gate"],
        "Counting regression",
        delta_color="inverse",
    )
    st.warning(
        "Release blocked: the candidate's total score rises, but its counting rule loses correct answers. Inspect slices before promoting a version."
    )
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Capability comparison")
        st.caption("FIXED HOLDOUT · same sample IDs and image hashes in both runs")
        records = [
            {"Task": task.replace("_", " ").title(), "Version": version, "Accuracy": values[key]}
            for task, values in summary["holdout_regression"]["task_slices"].items()
            for version, key in (("v1 reference", "old"), ("v2 candidate", "new"))
        ]
        bars(pd.DataFrame(records), "Task", "Accuracy", "Version")
    with right:
        st.subheader("Failure signals")
        st.caption("PROVISIONAL TRIAGE · not a causal diagnosis")
        frame = pd.DataFrame(
            [
                {"Failure": k.replace("_error", "").replace("_", " "), "Count": v}
                for k, v in summary["failure_counts_v1_dev"].items()
            ]
        )
        bars(frame, "Failure", "Count", percent=False)
        lo, hi = summary["holdout_regression"]["paired_ci95"]
        st.info(
            f"Paired delta 95% CI: {lo * 100:+.1f} to {hi * 100:+.1f} pp. Bootstrap resamples scene families; it does not measure real-world generalization."
        )
    st.subheader("Difficulty slices")
    records = [
        {"Difficulty": level, "Version": version, "Accuracy": stats["accuracy"], "n": stats["n"]}
        for version in ("v1", "v2")
        for level, stats in summary["metrics"][version]["difficulty"].items()
    ]
    bars(pd.DataFrame(records), "Difficulty", "Accuracy", "Version")
    st.caption(
        "Difficulty panel includes both dev and holdout; it is descriptive. Holdout capability comparison above drives the release gate."
    )

elif page == "Failure review":
    st.subheader("Inspect a failure, preserve the evidence")
    c1, c2, c3 = st.columns(3)
    version = c1.selectbox("Reference version", ["v1", "v2"])
    split = c2.selectbox("Split", ["dev", "holdout"])
    task = c3.selectbox("Capability", ["All", *sorted({s["task_type"] for s in samples})])
    rows = [
        r
        for r in (old if version == "v1" else new)
        if not r["correct"] and r["split"] == split and (task == "All" or r["task_type"] == task)
    ]
    if not rows:
        st.success("No failed cases in this slice.")
    else:
        sid = st.selectbox("Sample ID", [r["sample_id"] for r in rows])
        row, sample = next(r for r in rows if r["sample_id"] == sid), by_id[sid]
        left, right = st.columns([1, 1.2])
        with left:
            st.image(
                str(safe_path(DATA, sample["image_path"])),
                caption=f"{sample['task_type']} · {sample['difficulty']} · {sample['split']}",
                width="stretch",
            )
        with right:
            st.markdown(f"**Question**\n\n{sample['question']}")
            c1, c2 = st.columns(2)
            c1.metric("Ground truth", sample["ground_truth"])
            c2.metric("Parsed prediction", row["parsed_answer"] or "unparsed")
            st.markdown(f"**Provisional label:** `{row['failure_type']}`")
            st.caption(row["classification_reason"])
            st.code(row["raw_output"], language="json")
            st.caption(f"Latency: {row['latency_ms']:.4f} ms · metadata rule execution only")
        with st.expander("Scene metadata, query and trace identity"):
            st.json(
                {
                    "query": sample["query"],
                    "scene": sample["scene_metadata"],
                    "image_sha256": sample["image_sha256"],
                    "sample_sha256": row["sample_sha256"],
                }
            )
    st.download_button(
        "Download dev review queue",
        (REPORT / "review_queue.csv").read_bytes(),
        "review_queue.csv",
        "text/csv",
    )
    st.caption(
        "Fill failure_type and note, then run the documented evaluate --reviews command. Reviews never silently modify labels or original measurements."
    )

elif page == "Data production":
    st.subheader("An explainable queue, a bounded production budget")
    st.caption(
        "Only dev failures are eligible. Scores use configurable task value, frequency, severity, novelty, regression and a production-cost proxy."
    )
    selected_only = st.checkbox("Show selected parents only", value=True)
    rows = [r for r in queue if r["selected"] or not selected_only]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Sample": r["sample_id"],
                    "Capability": r["task_type"],
                    "Priority": r["priority_score"],
                    "Selected": r["selected"],
                }
                for r in rows
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    if rows:
        sid = st.selectbox("Explain a priority score", [r["sample_id"] for r in rows])
        st.json(next(r for r in rows if r["sample_id"] == sid))
    left, right = st.columns(2)
    with left:
        st.markdown("#### Production mix")
        bars(
            pd.DataFrame(
                [
                    {"Operator": k.replace("_", " "), "Count": v}
                    for k, v in summary["augmentation"]["operator_counts"].items()
                ]
            ),
            "Operator",
            "Count",
            percent=False,
        )
    with right:
        st.markdown("#### Dev pool before / after augmentation")
        before = Counter(s["task_type"] for s in samples if s["split"] == "dev")
        after = before + Counter(s["task_type"] for s in augmented)
        frame = pd.DataFrame(
            [
                {"Task": task.replace("_", " "), "Pool": pool, "Count": count}
                for pool, values in (("Before", before), ("After", after))
                for task, count in values.items()
            ]
        )
        bars(frame, "Task", "Count", "Pool", percent=False)
    if augmented:
        aid = st.selectbox("Inspect generated augmentation", [r["sample_id"] for r in augmented])
        aug = next(r for r in augmented if r["sample_id"] == aid)
        parent = by_id[aug["parent_id"]]
        left, right = st.columns(2)
        left.image(
            str(safe_path(DATA, parent["image_path"])),
            caption="Parent · " + parent["ground_truth"],
            width="stretch",
        )
        right.image(
            str(safe_path(DATA / "augmentation", aug["image_path"])),
            caption=aug["mutation"] + " · " + aug["ground_truth"],
            width="stretch",
        )
        st.write(aug["question"])
    st.caption(
        "Augmentation results are selected-slice diagnostics. No training consumes these data in this experiment."
    )

else:
    st.subheader("Reproducibility and run evidence")
    st.json(
        {
            "dataset_sha256": summary["dataset_sha256"],
            "config_sha256": summary["config_sha256"],
            "experiment_type": summary["experiment_type"],
        }
    )
    with st.expander("Experiment configuration", expanded=True):
        st.json(summary["config"])
    with st.expander("Validation and software environment"):
        st.json(read_json(REPORT / "validation.json"))
        st.json(read_json(REPORT / "environment.json"))
    with st.expander("All metrics: tags, errors, parsing, latency and cost"):
        st.json(summary["metrics"])
    st.download_button(
        "Download experiment report",
        (REPORT / "EXPERIMENT_REPORT.md").read_bytes(),
        "EXPERIMENT_REPORT.md",
        "text/markdown",
    )
    st.markdown(
        "**Evidence boundaries:** original synthetic images; metadata-privileged baselines; no neural training; no external API measurements; machine timings vary. See Data Card and Evaluation Card before interpreting scores."
    )
