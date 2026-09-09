# 具身 VLM 数据飞轮实验室

这个项目展示训练策略产品经理如何把“模型选错对象”转化为**评测—失败归因—数据策略—数据生产—版本回归**的可验证闭环。

**真实性边界：**默认实验使用读取结构化场景 metadata 的确定性规则，不是真实 VLM，没有进行神经网络训练，也不能用规则版本差异声称模型学习能力提升。

![真实运行的 Dashboard](assets/dashboard.png)

## 已交付与实际结果

- 240 条原创程序化图像评测样本，120 个成对场景族、6 类任务；168 条开发集、72 条保留集，相关变体不跨 split。
- 结构化输出、严格解析、Exact Match/归一化匹配、任务/难度/标签切片、错误率、无法解析率、延迟、可选成本和按场景族 bootstrap 的置信区间。
- 11 类失败 taxonomy、可人工复核的 CSV、配置化优先级与多样性约束。
- 从 dev 选择 18 个父样本，生成 108 条反事实、hard negative、难度递进、属性替换、位置扰动和干扰物增强数据。
- 保留集规则对照：41.7% → 90.3%，但计数 100% → 41.7%，因此候选版本被 **REJECT**。重点是门禁识别了退化，不是模型经过训练后提升。
- 四个 Dashboard 页面、单元/端到端/API MockTransport/AppTest 测试、可复现报告与 Git 历史。

## 五分钟运行

使用已验证的 Python 3.14，在仓库根目录执行。首次安装需要联网，安装后核心流程离线运行。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock.txt -e '.[dashboard,dev]'
flywheel demo
pytest -q
streamlit run dashboard.py
```

打开 [本地 Dashboard](http://127.0.0.1:8501)。英文 README 的 [Quick Start](README.md#9-quick-start) 提供分阶段命令。真实模型接入是可选能力，需要自行配置环境密钥与兼容模型，见 [API 说明](docs/API_ADAPTER.md)；仓库结果未调用真实 API。

## 招聘者建议阅读顺序

1. [实验报告](docs/EXPERIMENT_REPORT.md)：实际结果、切片退化、是否支持假设与下一步。
2. [数据策略](docs/DATA_STRATEGY.md)：可复算评分、权重假设、数据配比、增强/回流/停止条件。
3. [核心闭环代码](src/flywheel/pipeline.py)：从生成到回归报告的真实调用链。

[产品定义](docs/PRODUCT_BRIEF.md) · [Data Card](docs/DATA_CARD.md) · [评测合同](docs/EVALUATION_CARD.md) · [错误体系](docs/FAILURE_TAXONOMY.md) · [项目分工](docs/PROJECT_MANAGEMENT.md) · [面试手册](docs/INTERVIEW_GUIDE.md)

## 30 秒讲法

我做了一个面向具身 VLM 的数据策略验证平台，串起评测、失败归因、样本优先级、针对性增强和版本回归。项目真实生成了 240 条评测样本和 108 条增强数据，并能在总体分数上涨时识别计数退化、拒绝候选版本。当前用明确标注的离线规则对照验证工程流程，没有把结果包装成真实大模型训练提升。

## 发布与边界

当前交付时 GitHub CLI 未登录，公开仓库尚未创建或验证；本地代码、数据和 Git 历史已保留。完成 `gh auth login` 后，运行 `bash scripts/publish.sh`，它只创建指定的新仓库并核对远端关键文件。见 [发布说明](docs/PUBLISHING.md)。不要把本地测试说成远程 Actions 成功。

未实现大规模训练、真实视觉实验、真机任务、世界模型、线上收益或供应商合作。下一步最有价值的是只输入图片/问题的真实 VLM 实验，然后以等预算随机数据为对照检验 targeted 数据是否带来独立测试收益。

代码采用 MIT；原创生成数据采用 CC0-1.0。
