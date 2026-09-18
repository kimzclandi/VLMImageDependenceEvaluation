# 实验历史与可选附件 / Research history

| 阶段 / Track | 问题与结论 / Scope |
|---|---|
| 当前视觉干预 | [报告](GROUNDING_V3_REPORT.md)、[协议](GROUNDING_V3_PROTOCOL.md)：90题，270次真实模型生成；有限视觉贡献，以空间题为主，无训练 |
| 第一轮提示比较 | [报告](REAL_VLM_EXPERIMENT.md)、[复现](REAL_VLM_REPRODUCE.md)：72题、144次生成，holdout两种提示均61.1%，被答案先验追平；不是当前45题保留集结果 |
| metadata规则原型 | [报告](EXPERIMENT_REPORT.md)、[原始记录](../reports/demo/)：规则直接读取场景metadata，41.7%→90.3%不是模型学习，计数回归导致REJECT |

These tracks use different datasets or mechanisms. Their scores do not form a model-learning curve. The current track uses actual SmolVLM inference on synthetic images; the historical rule track does not.

## 可选材料

[数据策略](DATA_STRATEGY.md)、[早期产品说明](PRODUCT_BRIEF.md)与[企业方案/RACI](PROJECT_MANAGEMENT.md)属于原型或设计附件，不是已实施的企业项目。[视觉干预方法](GROUNDING_V3_METHOD.md)、[第一轮方法](REAL_VLM_METHOD.md)和[规则流程说明](RULE_PIPELINE_NOTES.md)记录各轮方法、假设和验证边界。

历史[规则界面截图](../assets/dashboard.png)及[规则指标截图](../assets/dashboard-metrics.png)保持原样，不能作为当前模型实验截图。
