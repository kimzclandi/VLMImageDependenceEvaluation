# 具身 VLM 数据飞轮实验室

面向数据闭环研发岗位：将视觉评测失败转为可复核、可追溯的数据生产记录，并用隔离的保留集检验方法差异。

本仓库有两条独立证据链：**真实 SmolVLM 图像推理**与**历史 metadata 规则流程演示**。两者都没有训练模型；规则得分变化及增强数据数量都不能包装成训练收益。

## 真实 VLM 实验

- 公开 SmolVLM-256M，固定权重 revision 与 SHA-256；本机 CPU、免费离线推理，无 API 密钥。
- 新建 24 个合成桌面场景族、72 道问题：颜色计数、属性存在性、空间关系。开发/保留各 12 族、36 题，不复用道路昼夜标签实验。
- 先提交冻结协议，再进行基础提示与明确观察提示的 144 次同图配对生成；不使用有限答案解码，不做保留集驱动调参。
- 图像加问题的独立输入接口；全部原始输出、失败分母、格式指标、任务切片与环境收据可查。
- 错误进入待人工复核队列，症状与根因分开；仅开发集错误驱动可追溯平移样本生产，未用于训练。

[实际结果与限制](docs/REAL_VLM_EXPERIMENT.md) · [原始输出](reports/real_vlm/outputs.jsonl) · [逐题评分](reports/real_vlm/scores.jsonl) · [冻结协议](reports/real_vlm/protocol.json) · [模型卡](docs/REAL_VLM_MODEL_CARD.md) · [泄漏审计](docs/REAL_VLM_DATA_AUDIT.md)

**本轮结果：保留集 61.1% → 61.1%，未支持提示改进假设。开发集多数答案先验同样达到 61.1%，不能据此声称视觉 grounding 收益。**

## 保留的规则历史

240 条原样本、120 个场景族、6 类任务，18 个开发父样本与 108 条增强。metadata 规则候选保留集总体准确率 **41.7% → 90.3%**，但计数 **100% → 41.7%**，因此 **REJECT**。这证明流程能发现切片退化，不证明模型学习收益。[历史报告](docs/EXPERIMENT_REPORT.md)

![历史规则 Dashboard](assets/dashboard.png)

## 运行

原有 Python 3.14 环境和启动方式保持不变：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock.txt -e '.[dashboard,dev]'
flywheel demo
pytest -q
streamlit run dashboard.py
```

Dashboard 左侧明确切换「规则流程演示（历史）」与「真实 VLM 评测」，无需加载模型即可浏览已提交证据。

真实实验使用独立环境，不移动或覆盖旧 `.venv`：

```bash
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python -r requirements-vlm-lock.txt
PYTHONPATH=src .venv-vlm/bin/python scripts/run_visual_experiment.py
PYTHONPATH=src .venv/bin/python scripts/analyze_visual_experiment.py
```

首次下载公开固定权重；之后可以离线运行。复跑会写结果目录，保留参考结果请使用独立 checkout。[完整复现说明](docs/REAL_VLM_REPRODUCE.md)

## 岗位能力与证据

| 能力 | 可检查实现 |
|---|---|
| 数据质量与防泄漏 | 场景族/图像隔离、随机 ID、哈希审计、明确边界样本 |
| 模型验证 | 固定协议、同图配对、失败不丢分母、格式与语义分开 |
| 数据挖掘 | 真实失败队列、可观察症状、待验证根因、dev-only 生产 |
| 可靠流水线 | 固定权重与环境、输入白名单、缓存失效、异常不缓存、数据血缘 |
| 工程交付 | 单元测试、界面验收、历史回归、GitHub Actions |

[面试指南与主动回忆](docs/REAL_VLM_INTERVIEW.md) · [流水线代码](scripts/run_visual_experiment.py) · [模型适配器](src/flywheel/local_vlm.py) · [Actions](https://github.com/kimzclandi/vlm-data-flywheel-lab/actions)

范围仅为小型合成桌面场景。未验证真实相机、机器人控制、训练收益、人工降本或生产级规模。代码 MIT，原创数据 CC0-1.0，模型遵循上游 Apache-2.0。
