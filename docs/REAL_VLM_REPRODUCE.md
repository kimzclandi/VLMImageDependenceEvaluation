# 真实实验复现

保留原 `.venv` 及 `flywheel demo`。真实实验独立使用 `.venv-vlm`，从仓库根目录运行：

```bash
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python -r requirements-vlm-lock.txt
PYTHONPATH=src .venv-vlm/bin/python scripts/run_visual_experiment.py
```

首次运行从 Hugging Face 下载固定 revision 的公开模型到忽略的 `work/hf`。无需密钥。可传 `--snapshot /path/to/snapshot` 使用已有权重；脚本记录权重与配置摘要。参考运行复用了本机已有固定 revision 缓存，无网络推理。

已提交 `data/visual_v2` 和冻结协议，不要在同一版本重新运行 `--freeze`。该命令在协议存在时拒绝覆盖；维护者需在全新实验版本中冻结新假设。本轮协议在 commit `b9f9bd0` 冻结，早于模型结果。

运行会重建 `reports/real_vlm` 结果文件；如需要保留已提交的参考输出，先在独立 checkout 运行。同机重跑使用 `work/visual_cache`，缓存键包含图像字节、完整问题、提示、协议、权重与处理器配置、依赖版本。异常不缓存。缓存保留原始推理耗时，不能把缓存读取时间写成模型延迟。跨平台浮点及库差异可能造成不同生成结果，固定版本不保证跨硬件逐字一致。

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python scripts/check_reproducibility.py
.venv/bin/python scripts/privacy_check.py
.venv/bin/streamlit run dashboard.py
```

Dashboard 左侧选择「真实 VLM 评测」或「规则流程演示（历史）」。CI 验证原规则可复现性、真实实验数据合同/分母/缓存/解析和已存证据；CI 不下载或重新推理真实权重。真实模型运行证据以本地实际输出和环境记录为准。
