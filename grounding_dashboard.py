"""Read-only balanced grounding evidence; no neural runtime required."""

from pathlib import Path

import streamlit as st

from flywheel.io import read_json


def show(root: Path):
    out = root / "reports/grounding_v3"
    st.title("图像是否真正帮助答对？")
    st.caption("真实 SmolVLM-256M 推理 · 平衡反事实场景 · 90 题 / 30 场景族 · 无训练")
    if not (out / "summary.json").exists():
        st.info("协议已冻结；完整推理结束后展示结果。")
        return
    summary = read_json(out / "summary.json")
    split = st.selectbox("数据划分", ["holdout", "dev"])
    result = summary["results"][split]
    cols = st.columns(3)
    for col, arm in zip(cols, ["real", "blank", "mismatch"], strict=True):
        col.metric(arm + " · 任务宏平均", f"{result[arm]['task_macro_accuracy']:.1%}")
        col.caption(
            f"全分母：{result[arm]['correct']}/{result[arm]['n']}；格式合法 {result[arm]['valid']:.1%}"
        )
    st.caption("简单先验：任务宏平均 40%，全题准确率 33.3%。错配图像也按原问题原答案评分。")
    st.table(
        [
            {
                "任务": task,
                **{
                    arm: f"{result[arm]['tasks'][task]['accuracy']:.1%}"
                    for arm in ["real", "blank", "mismatch"]
                },
            }
            for task in ["counting", "existence", "spatial"]
        ]
    )
    paired = result["real_vs_blank"]
    st.write(
        f"真实 − 空白：{paired['macro_delta'] * 100:.2f} 个百分点；场景族 bootstrap 区间 [{paired['ci95'][0] * 100:.2f}, {paired['ci95'][1] * 100:.2f}]。"
    )
    st.warning(
        "输出随图像改变，只证明行为敏感；只有正确率的配对改善才能支持视觉贡献。该实验仍仅覆盖同一合成生成器。"
    )
    with st.expander("配对变化与完整分母"):
        st.json(result)
    rows = read_json(root / "data/visual_v3/samples.json")
    scores = read_json(out / "scores.json")
    candidates = [r for r in rows if r["split"] == split]
    sid = st.selectbox("查看反事实与原始输出", [r["sample_id"] for r in candidates])
    row = next(r for r in rows if r["sample_id"] == sid)
    donor = next(r for r in rows if r["sample_id"] == row["donor_id"])
    a, b = st.columns(2)
    a.image(
        str(root / "data/visual_v3" / row["image_path"]),
        caption="原图 · gold=" + row["ground_truth"],
    )
    b.image(
        str(root / "data/visual_v3" / donor["image_path"]),
        caption="错配图 · donor gold=" + donor["ground_truth"],
    )
    st.write(row["question"])
    st.dataframe([r for r in scores if r["sample_id"] == sid], hide_index=True)
    st.caption("自动诊断队列未完成人工复核；不自动生成训练数据。")
    with st.expander("冻结协议"):
        st.json(read_json(out / "protocol.json"))
