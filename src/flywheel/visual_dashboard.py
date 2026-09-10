"""Separate real-model evidence view, without loading neural dependencies."""

from pathlib import Path

import streamlit as st

from flywheel.io import read_json, read_jsonl


def show(root: Path):
    st.title("真实 VLM · 桌面视觉评测")
    st.caption("SmolVLM-256M · 图像 + 问题 · CPU · 未训练 · 合成桌面场景")
    report = root / "reports/real_vlm"
    if not (report / "summary.json").exists():
        st.info("实验运行中，协议已冻结。")
        return
    summary = read_json(report / "summary.json")
    split = st.selectbox("评测集", ["holdout", "dev"])
    a, b = st.columns(2)
    for col, arm in ((a, "baseline"), (b, "observe")):
        col.metric(arm + " accuracy", f"{summary[split][arm]['accuracy']:.1%}")
        col.metric(arm + " format validity", f"{summary[split][arm]['format_validity']:.1%}")
    st.write("同图配对比较；错误和缺失输出保留在分母。格式合法不等于视觉判断正确。")
    st.table(
        [
            {
                "任务": task,
                "基础提示": f"{summary[split]['baseline']['tasks'][task]:.1%}",
                "观察提示": f"{summary[split]['observe']['tasks'][task]:.1%}",
            }
            for task in ("counting", "existence", "spatial")
        ]
    )
    with st.expander("配对统计与原始指标"):
        st.json(summary[split])
    st.info(
        "保留集两提示均 22/36；开发集多数答案先验也为 22/36。未证明提示改善或视觉 grounding 收益。"
    )
    st.subheader("真实失败 → 待人工复核")
    queue = [q for q in read_jsonl(report / "review_queue.jsonl") if q["split"] == split]
    if queue:
        selected = st.selectbox("失败样本", [f"{q['sample_id']} / {q['arm']}" for q in queue])
        q = queue[[f"{q['sample_id']} / {q['arm']}" for q in queue].index(selected)]
        row = next(
            r
            for r in read_jsonl(root / "data/visual_v2/samples.jsonl")
            if r["sample_id"] == q["sample_id"]
        )
        st.image(str(root / "data/visual_v2" / row["image_path"]), width=512)
        st.write(row["question"])
        st.json(q)
    st.warning("根因均待验证。仅开发集失败生成平移样本，未用于训练，不声称能力收益。")
    st.metric("已生成可追溯样本", summary["augmentation_count"])
    with st.expander("冻结协议与环境"):
        st.json(read_json(report / "protocol.json"))
        st.json(read_json(report / "environment.json"))
