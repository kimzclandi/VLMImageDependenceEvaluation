> 本页保留原规则演示/实施方案历史。新增真实 VLM 评测见 [实验报告](REAL_VLM_EXPERIMENT.md)、[复现说明](REAL_VLM_REPRODUCE.md) 与 [方法说明](REAL_VLM_METHOD.md)。真实推理已单独实现；无训练收益声明。

# Experiment report: deterministic reference comparison

> Actual code execution on original synthetic data. Both baselines read privileged scene metadata. No VLM was trained or evaluated. Rule changes were specified in advance; augmentation did not train v2.

## Question and hypothesis

Can a reproducible evaluation-to-data workflow discover known rule defects, produce valid targeted samples and reject a candidate whose overall score rises while counting regresses? The expected negative control is the v2 large-only counting rule.

## Provenance

- Dataset: `tabletop-v1`; SHA-256 `d02d58731255d6df2f977aca74ca3285bc74d865d1bbe37008531091e8ffea63`
- Configuration SHA-256: `7a690751b477c4559ec9815d8e8bdab24331579f8da47c00d8cd117a8b80239f`
- Seed: 42; prompt: `tabletop-json-v1`; models: `metadata-reference-NOT-VLM/v1` and `/v2`.
- Command: `flywheel demo --config configs/demo.json --data-dir data/sample --report-dir reports/demo`
- Input: `data/sample/samples.jsonl`; outputs/scores: `reports/demo/{v1,v2}_{outputs,scores}.jsonl`.
- Exact software versions: `reports/demo/environment.json`; file hashes: `reports/demo/artifact_manifest.json`.

## Fixed holdout results

| Task | n | v1 | v2 | Delta (pp) |
|---|---:|---:|---:|---:|
| attribute_binding | 12 | 50.0% | 100.0% | +50.0 |
| counterfactual | 12 | 50.0% | 100.0% | +50.0 |
| counting | 12 | 100.0% | 41.7% | -58.3 |
| instruction_following | 12 | 0.0% | 100.0% | +100.0 |
| spatial_relation | 12 | 50.0% | 100.0% | +50.0 |
| target_selection | 12 | 0.0% | 100.0% | +100.0 |

Paired accuracy delta: **+48.6 pp**, 95% scene-family bootstrap interval [+30.6, +65.3] pp. Candidate gate: **REJECT**. Regressed slices: counting.

The interval describes this small synthetic generator distribution, not real robots. Multiple slices are descriptive; the conservative release rule rejects any observed task drop. All capability slices are checked, including those not targeted by the data queue.

## Failure-to-data decision

From dev only: 18 diverse parent families selected; 108 novel augmentations accepted; 0 candidates skipped after bounded retries. Holdout families never enter production. Augmentation performance is a diagnostic selected slice, not independent evidence of improvement.

| Operator | Accepted |
|---|---:|
| counterfactual | 18 |
| hard_negative | 18 |
| curriculum | 18 |
| attribute_substitution | 18 |
| spatial_perturbation | 18 |
| distractor_injection | 18 |

## Traceable dev failures

| Sample | Question | Ground truth | v1 parsed | Provisional classification |
|---|---|---|---|---|
| `s42-spatial_relation-003-a` | Is o1 below o2? Answer yes or no. | no | yes | spatial_reasoning_error |
| `s42-attribute_binding-000-b` | Is there a green circle object? Answer yes or no. | no | yes | attribute_binding_error |
| `s42-target_selection-000-a` | Select every small red square object. Return sorted object IDs separated by commas, or none. | o1 | o1,o2 | instruction_following_error |

## Interpretation and next decision

The workflow hypothesis is supported if data validation succeeds and the intentional counting regression is detected. A higher aggregate score does not justify release. Reject v2, fix the counting rule for pipeline validation, and next evaluate a real VLM with pixels-only inputs on a newly frozen holdout before making any model-quality claim.

No measured outcome here establishes that synthetic data improves a neural model. There is no training job, no external model run, no human-verified causal label, and no real-robot success metric. v1/v2 timing is measured CPU rule execution and must not be compared with VLM latency.

## Full evidence

See `summary.json` for dev/holdout/all/augmentation metrics and configuration; `priority_queue.jsonl` for every score factor; `review_queue.csv` for human triage; `validation.json` for generated-data checks; and `v*_scores.jsonl` for per-sample results.
