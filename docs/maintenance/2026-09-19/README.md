# Maintenance on 2026-09-19

These engineering changes postdate the existing experiments. No model training, new inference result or quality gain is claimed.

- Duplicate input IDs now fail before scoring, instead of counting the same question twice.
- Final grounding analysis refuses incomplete generations before writing immutable scores/summary. Missing outputs still count as failures in the diagnostic scoring function; resume generation before final publication.
- The historical rule demo requires new, disjoint data/report directories. CLI generation and report commands reject existing targets before executing, including before any API request.

```bash
flywheel demo --data-dir work/replay-new/data --report-dir work/replay-new/reports
```

This command executes metadata rules, not SmolVLM inference. The existing 270 saved generations are rescored with unchanged denominators and metrics. Source bytes referenced by the historical grounding freeze are retained under `baseline/` as `.txt` and still checked against their original hashes. Original predictions, reports and protocols are unchanged. Historical model reruns must use their original source revision; current code must not bypass the source freeze or relabel old holdout results as independent validation.

本次本地验证：70 项测试通过；命令和修改后源码摘要见 [validation.json](validation.json)。这不是未推送提交的远端 CI 结果。

[单张 dev 图像的真实 CPU 生成](evidence/inference-smoke.json) 包含原始输出、权重版本、输入哈希、当前源码哈希和时间；只验证当前调用链，不计算新的质量提升。
