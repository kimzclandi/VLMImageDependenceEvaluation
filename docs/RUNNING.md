# 当前实验运行说明 / Running the current experiment

## 已保存结果回放 / Saved-generation replay

使用[首页安装命令](../README.zh-CN.md#查看与运行)创建独立环境，然后运行：

```bash
python scripts/verify_grounding.py
streamlit run dashboard.py --server.address 127.0.0.1
```

默认显示「视觉贡献干预 v3」。这是从已有模型输出重算指标，不是新的推理。CI 还回放历史规则流程并检查软件契约；CI 通过不代表重新运行了神经模型。

The default viewer and verification command use the current saved image-intervention experiment. CI also checks the historical rule workflow; it does not rerun neural inference.

## 真实模型执行 / Actual model inference

需要独立 Python 3.12 环境与[冻结协议](GROUNDING_V3_PROTOCOL.md)对应的 SmolVLM 快照。依赖安装方式：

```bash
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python -r requirements-vlm-lock.txt
```

模型 revision 为 `7e3e67edbbed1bf9888184d9df282b700a323964`。协议中的 `/path/to/fixed/snapshot` 须替换为实际下载并核验的本地目录；程序核验每个模型文件和执行源文件。不得用浮动 latest 权重替换。

已发布生成不可覆盖。2026-09-19 的维护改变了运行源码，历史协议仍绑定原源码：重跑历史模型实验请在独立 checkout 使用 `0b0a143fe995a31cb47a997707d85156656549cb`，归档原结果目录并保留原协议，再按协议执行 `python -m flywheel.grounding run --snapshot ...`。已有记录只核验并复用。当前源码不绕过冻结检查；新协议需要新的输出和适当的独立数据。不要删除失败或把缓存回放记作新模型运行。保存结果核验不包含这一步。

Use the exact frozen snapshot and preserve reference generations in a separate checkout before a fresh run. Existing observations are verified and reused, not silently overwritten.

## 当前代码的最小真实推理 / Current-code smoke

在上述独立推理环境安装完成后，可以只执行一张既有 dev 合成图像，不接触 holdout，不改写历史实验：

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=src .venv-vlm/bin/python scripts/smoke_local_vlm.py \
  --snapshot /path/to/fixed/snapshot --output work/smoke-new
```

该命令逐文件核对固定模型快照、核对输入图片哈希、实际执行一次 CPU 生成，保存带日期、当前源码哈希、依赖版本和原始输出的 `run.json`。已有输出目录拒绝覆盖。模型文件必须已准备好；命令不下载权重。这仅验证执行链路，不报告新质量收益，不等于重新运行 270 次实验。

## 历史入口 / Historical workflows

- 第一轮 72 题提示比较：[复现说明](REAL_VLM_REPRODUCE.md)。历史脚本会重写结果，实际重推必须先建立独立 checkout；只看结果无需运行它。与当前 90 题图像干预分开。
- `flywheel demo`：读取 metadata 的规则原型；只用于历史流程复现，不加载 SmolVLM，不训练模型。已有目录会被拒绝；使用新的独立输出：`flywheel demo --data-dir work/rule-replay/data --report-dir work/rule-replay/reports`。
- Dashboard 可切换三条历史/当前实验记录，不能将它们的分数串成模型学习曲线。
