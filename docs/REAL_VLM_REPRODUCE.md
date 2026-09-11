# 历史提示比较：合成图像上的 SmolVLM 推理复现

本页对应第一轮 **72 题、144 次生成**的基础提示/观察提示比较。它不是当前 90 题视觉输入干预实验；当前结果回放见[运行说明](RUNNING.md)。两轮均使用合成图像和真实模型推理，没有训练模型。

## 先隔离原始记录，再执行模型

`scripts/run_visual_experiment.py` 会重写 `reports/real_vlm` 的环境、输出、评分与汇总，并写入 `data/visual_v2/augmentation`。其 `--freeze` 拒绝覆盖协议，不代表普通执行会保护原输出。**不要在保存参考结果的原工作区直接执行该脚本。**

若需要实际重推，从干净的已提交仓库建立独立 worktree；下列目录已存在时，命令会拒绝创建，应保留它并选择其他新目录。

```bash
git worktree add --detach ../vlm-prompt-replay HEAD
cd ../vlm-prompt-replay
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python -r requirements-vlm-lock.txt
PYTHONPATH=src .venv-vlm/bin/python scripts/run_visual_experiment.py
```

原工作区中的参考文件保持原样。新的执行副本会包含与 HEAD 不同的生成、耗时或环境记录；比较差异时保留这些变化，不将它们回写成新的历史参考，也不要刷新旧 artifact manifest 来掩盖差异。

首次运行从 Hugging Face 下载固定 revision 的公开模型到执行副本中忽略的 `work/hf`，无需密钥。可传 `--snapshot /path/to/snapshot` 使用已有权重；脚本记录权重与配置摘要。原参考运行复用了本机固定 revision 缓存，无网络推理。

已提交 `data/visual_v2` 和冻结协议，不要重新运行 `--freeze`。原协议在提交 `b9f9bd0` 冻结，早于模型结果。新假设需要单独协议，不能通过修改此协议变成原实验的继续运行。

## 缓存与结果解释

同机重跑使用执行副本中的 `work/visual_cache`。缓存键包含图像字节、完整问题、提示、协议、权重与处理器配置及依赖版本；异常不作为成功缓存。缓存保留原始推理耗时，不能把缓存读取时间写成模型延迟。

独立 worktree 默认不包含旧工作区忽略的缓存，所以首次执行通常需要真实推理。跨平台浮点及库差异可能造成生成变化，固定版本不保证跨硬件逐字一致。

## 只查看已提交的历史结果

无需运行上述模型脚本。使用[首页离线环境](../README.zh-CN.md#查看与运行)启动：

```bash
streamlit run dashboard.py --server.address 127.0.0.1
```

Dashboard 默认显示当前视觉输入干预；切换「真实 VLM 评测」查看第一轮提示比较，切换「规则流程演示（历史）」查看 metadata 原型。三者分数不能合成一条模型学习曲线。

CI 验证规则可复现性、真实实验的数据契约/分母/缓存/解析及已存记录，不下载或重新推理模型权重。此页整理仅核对执行路径，没有新增模型运行。
