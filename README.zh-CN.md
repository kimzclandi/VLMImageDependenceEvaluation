# 视觉语言模型的图像依赖性评测

![项目标识](.github/project-header.svg)

[![CI](https://github.com/kimzclandi/VLMImageDependenceEvaluation/actions/workflows/ci.yml/badge.svg)](https://github.com/kimzclandi/VLMImageDependenceEvaluation/actions/workflows/ci.yml)

[English](README.md)

使用固定 SmolVLM-256M，在可控合成图像上比较原图、空白图和错配图输入：同一个问题的正确回答究竟有多少依赖图像？实验包含计数、存在性和空间关系，按场景族划分开发集与保留集。**模型实际执行了推理；没有训练或微调。**

仓库实现了合成场景、像素与问题输入接口、配对干预、全分母评分和结果浏览。`real` 表示原题对应的合成图像，不是相机采集的真实场景。

## 项目沿革（2026-09-20 补记）

根据维护者对本地开发过程的说明，相关早期工作约于 2026 年 4 月开始在本地开展，之后集中整理并上传 GitHub。该月份是早期工作的近似起点，不表示当前全部功能和实验在当时已完成。后续实现、实验与维护保留各自的实际版本及运行日期。

## 当前结果

90 题、30 个场景族，三种输入共 270 次 CPU 生成。保留集为 45 题、15 族；计数 25 题，存在性与空间各 10 题，因此全部题目准确率与三任务等权宏平均不同。

| 图像输入 | 全部保留题准确率 | 三任务宏平均 |
|---|---:|---:|
| 原图（real） | 20/45 = 44.4% | 54.7% |
| 空白图（blank） | 15/45 = 33.3% | 40.0% |
| 错配图（mismatch） | 10/45 = 22.2% | 25.3% |

原图−空白的宏平均差为 +14.67 个百分点，场景族配对 bootstrap 95% 区间为 [+8.00, +19.33]。视觉贡献主要来自空间题（90% 对 50%）；存在题均为 50%，计数原图为 24%。结果支持这个合成设置中的有限视觉输入贡献，不能外推通用 grounding、机器人能力或训练收益。全部格式失败仍计入分母。

[实验报告](docs/GROUNDING_V3_REPORT.md) · [冻结协议](docs/GROUNDING_V3_PROTOCOL.md) · [原始生成与统计](reports/grounding_v3/)

## 快速开始 / Quick Start

从仓库根目录建立独立环境；已存在的环境不要覆盖。首次安装需要网络，以下回放与浏览不下载模型、不调用推理。

### 安装 / Installation

```bash
git clone https://github.com/kimzclandi/VLMImageDependenceEvaluation.git
cd VLMImageDependenceEvaluation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock.txt -e '.[dashboard,dev]'
```

### 使用示例 / Usage

```bash
python scripts/verify_grounding.py
streamlit run dashboard.py --server.address 127.0.0.1
```

Dashboard 默认打开 **「视觉贡献干预 v3」**，重算脚本校验 270 次已保存生成及其分母、配对和指标。真实模型从零运行需固定权重及独立 Python 3.12 环境，见[运行说明](docs/RUNNING.md)；历史 `flywheel demo` 是 metadata 规则流程，不是当前模型实验。

![合成图像上的视觉干预实验界面](assets/grounding-v3-dashboard.png)

截图来自已保存的视觉干预实验；它不代表新一次推理或训练。

## 实现与贡献范围

本仓库实现[干预与评分](src/flywheel/grounding.py)、[模型输入适配](src/flywheel/local_vlm.py)、场景族隔离及不可覆盖记录。SmolVLM 模型和预训练权重来自 Hugging Face，模型执行使用 PyTorch/Transformers；代码、测试与文档使用 AI 辅助开发。

[历史实验与附件](docs/RESEARCH_INDEX.md)分别收录第一轮提示比较、metadata 规则原型和方法说明与设计材料。规则的 41.7%→90.3% 是规则变更效果，不是模型学习收益；计数回归导致历史候选 **REJECT**，原始记录保留。

## 主要限制

图像为干净二维形状、固定颜色与尺寸，开发/保留集共享生成器。每任务仅五个保留场景族；固定尺寸还允许颜色面积等捷径。未验证真实相机、OOD 泛化、真机任务或训练效果。输出随图像变化不等于正确理解图像。

代码 [MIT](LICENSE)，原创图像/数据 [CC0-1.0](data/LICENSE)，模型遵循上游许可。[贡献与维护说明](CONTRIBUTING.md)。

[2026-09-19 工程维护与验证边界](docs/maintenance/2026-09-19/README.md) · [当前代码单张图像推理](docs/RUNNING.md#当前代码的最小真实推理--current-code-smoke)

[2026-09-21 工程维护与验证](docs/maintenance/2026-09-21/README.md)

2026-09-21: [缓存完整性与恢复验证 / Cache integrity maintenance](docs/maintenance/2026-09-21-cache/README.md).

## 参与贡献

[贡献指南](CONTRIBUTING.md) · [行为准则](CODE_OF_CONDUCT.md) · [维护与发布](docs/MAINTAINING.md)

## License

代码：[MIT](LICENSE)。原创数据：[CC0-1.0](data/LICENSE)。模型遵循各自上游许可。

[项目名称与兼容性说明 / Naming and compatibility](docs/NAMING.md)
