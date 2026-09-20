# Visual-input interventions in a small VLM

![Project wordmark](.github/project-header.svg)

[![CI](https://github.com/kimzclandi/vlm-data-flywheel-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/kimzclandi/vlm-data-flywheel-lab/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/kimzclandi/vlm-data-flywheel-lab?style=flat)](https://github.com/kimzclandi/vlm-data-flywheel-lab/stargazers) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[中文介绍与运行](README.zh-CN.md)

Does a correct answer depend on the image? This personal research project compares original, blank and mismatched images using a fixed SmolVLM-256M model on controlled synthetic counting, existence and spatial-relation questions. **Inference was actually run; no model was trained or fine-tuned.** The `real` arm means the original synthetic image, not a camera-captured scene.

The repository implements scene generation, a pixels-and-question adapter, paired interventions, scoring that retains failures, and a results viewer. Development and holdout examples are separated by scene family.

## Features

- Synthetic scene generation and scene-family isolation.
- Original, blank and mismatched image interventions with a fixed model.
- Failure-preserving scoring and saved-generation browsing.

## Project history (added 2026-09-20)

According to the maintainer’s account, early work began locally around April 2026, before the project was consolidated and uploaded to GitHub. This approximate starting point does not date every feature or experiment in the current repository. Subsequent implementations, experiments and maintenance retain their actual version and run dates.

## Current results

90 questions from 30 scene families, with 270 CPU generations across three input conditions. The holdout contains 45 questions from 15 families: 25 counting, 10 existence and 10 spatial questions. All-question accuracy and equal-weight task-macro accuracy therefore have different denominators.

| Image input | All-question holdout accuracy | Three-task macro accuracy |
|---|---:|---:|
| Original (`real`) | 20/45 = 44.4% | 54.7% |
| Blank | 15/45 = 33.3% | 40.0% |
| Mismatched | 10/45 = 22.2% | 25.3% |

Original minus blank task-macro accuracy is +14.67 percentage points, with a paired scene-family bootstrap 95% interval of [+8.00, +19.33]. The contribution mainly comes from spatial questions (90% versus 50%); existence stays at 50%, and original-image counting accuracy is 24%. This supports limited visual-input contribution in this synthetic setting, not general grounding, robot capability or training gains. Invalid answers remain in the denominator.

[Experiment report (Chinese)](docs/GROUNDING_V3_REPORT.md) · [Frozen protocol](docs/GROUNDING_V3_PROTOCOL.md) · [Raw generations and metrics](reports/grounding_v3/)

## Quick Start

Run from the repository root in a separate environment; preserve any existing environment. Installation needs network access. Verification and browsing use saved generations and require no model download or inference.

### Installation / 安装

```bash
git clone https://github.com/kimzclandi/vlm-data-flywheel-lab.git
cd vlm-data-flywheel-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock.txt -e '.[dashboard,dev]'
```

### Usage / 使用示例

```bash
python scripts/verify_grounding.py
streamlit run dashboard.py --server.address 127.0.0.1
```

The Dashboard opens **「视觉贡献干预 v3」** by default. The verification script checks the 270 saved generations, denominators, pairing and metrics. [Running guide](docs/RUNNING.md) separates this replay from actual inference with fixed weights in a separate Python 3.12 environment. The historical `flywheel demo` command runs metadata rules, not this model experiment.

![Saved visual-input intervention results](assets/grounding-v3-dashboard.png)

The screenshot shows this saved experiment, not a new inference or training run.

## Implementation and attribution

Repository work includes [interventions and scoring](src/flywheel/grounding.py), the [model input adapter](src/flywheel/local_vlm.py), family isolation and immutable records. SmolVLM and its pretrained weights come from Hugging Face; execution uses PyTorch and Transformers. Code, tests and documentation were developed with AI assistance.

[Research history and optional materials](docs/RESEARCH_INDEX.md) separate the earlier prompt comparison, metadata-rule prototype, and method/design attachments. The historical rule score change of 41.7%→90.3% is not a learning gain; the candidate was **REJECTED** for a counting regression. Original records remain available.

## Limitations

Clean 2D shapes, fixed colors and sizes, and a shared generator constrain the result. Each task has only five holdout families. Fixed-size objects permit shortcuts such as color area. No real-camera, OOD, robot or training benefit has been established. Sensitivity to an image does not by itself show correct understanding.

Code: [MIT](LICENSE). Original data/images: [CC0-1.0](data/LICENSE). The model retains its upstream license. [Contributing](CONTRIBUTING.md).

[2026-09-19 工程维护与验证边界](docs/maintenance/2026-09-19/README.md)

[2026-09-21 工程维护与验证](docs/maintenance/2026-09-21/README.md)

2026-09-21: [缓存完整性与恢复验证 / Cache integrity maintenance](docs/maintenance/2026-09-21-cache/README.md).

## Contributing / 参与贡献

[贡献指南](CONTRIBUTING.md) · [行为准则](CODE_OF_CONDUCT.md) · [结构与维护](docs/MAINTAINING.md)

[反馈问题](https://github.com/kimzclandi/vlm-data-flywheel-lab/issues/new?template=bug_report.yml) · [建议功能](https://github.com/kimzclandi/vlm-data-flywheel-lab/issues/new?template=feature_request.yml)

## License

Project code: [MIT](LICENSE). Original generated images/data: [CC0-1.0](data/LICENSE); model weights retain their upstream license.
