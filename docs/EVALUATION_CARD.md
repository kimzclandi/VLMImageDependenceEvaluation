# Evaluation card

## Objective and population

Validate the engineering and decision process on a small original 2D tabletop generator. The population is this generator's clean, labeled scenes. The deployed task of a robot in the physical world is outside this evaluation's population.

Default base set: 240 examples / 120 families; frozen holdout 72 / 36 families; dev 168 / 84. Six tasks × 12 holdout examples each. Original task coverage is uniform; difficulty is object count, not an empirical psychometric calibration. Task/question templates and palettes remain shared between splits, so holdout is **within-generator**, not distribution-shift testing.

## Model contract and evaluation separation

`ReferenceAdapter(v1/v2)` reads metadata and structured query but never `ground_truth`. It delegates exact symbolic solving after applying documented query defects. v1 ignores shape in existence, size/relation in selection, and reverses above/below. v2 repairs these but introduces large-only counting. These intentional controls test the pipeline; they do not measure perception, language understanding or learning.

The optional API path sends image bytes and rendered question plus a fixed system prompt, never the scene metadata, query or oracle answer. It uses user-selected model/endpoint; no external model was called for committed results. Payload isolation is tested with HTTP MockTransport, not provider access.

## Metrics and denominators

- Exact Match compares the parsed answer string with the canonical truth (before whitespace/case normalization). It does **not** compare the JSON wrapper with the truth.
- Normalized accuracy lowercases/strips whitespace, canonicalizes integer strings and sorts ID sets. Only JSON with exactly one `answer` field of string/int type is accepted; booleans, free text, duplicate IDs and out-of-domain answer types are rejected. Unknown object IDs count as incorrect selections, not infrastructure errors.
- All N requested samples remain in the accuracy denominator, including request errors, refusals and parse failures. API/refusal error rate counts `error_status`; unparseable rate counts `parse_error` after a successful request. They are separate diagnostics.
- Slices: task, difficulty, split and tags, each with n, family count, accuracy and CI. Tags overlap; never sum their n as total population.
- Median and p95 are recorded from real wall-clock call duration. Cached calls have `cache_hit=true`, attempts=0 and zero incremental estimated cost; cached token fields describe the original response. Network/model latency comparisons must exclude cache hits and align retry policy.
- Cost is estimated from explicit input/output prices per million tokens and returned usage. Missing prices/usage produce null, not zero. Retries with unreported server-side usage may incur unknown costs; the estimate is not an invoice or spending cap.

## Uncertainty and regression

`bootstrap` resamples whole scene families with replacement using a fixed seed, computes each resampled sample-weighted mean, sorts 1,000 replicate means, and reports the 2.5% and 97.5% percentile indices. One-family/empty slices return null intervals. Family grouping prevents paired images from doubling nominal independent evidence. Shared templates still cause dependence, and a 36-family holdout remains small.

`compare` requires the same unique sample IDs and identical sample content hashes. It computes per-example deltas (new_correct−old_correct) and resamples families for a paired CI. Correct→incorrect and incorrect→correct IDs are saved. Candidate release is rejected if **any task's observed accuracy declines beyond config tolerance** (default 0). This is a conservative descriptive guardrail, not a test of statistical significance and not a correction for multiple comparisons. A confidence interval above zero for total improvement cannot override a harmful slice decline.

## Judge and calibration

No LLM-as-a-Judge is used: these finite answers have a transparent oracle. Human review applies to ambiguity, annotation quality and root-cause hypotheses, not opaque scoring. `review_queue.csv` can be edited and re-evaluated with `--reviews`; reviewed categories never silently change ground truth or accuracy. Correct label edits require a new dataset version.

If open-ended tasks are introduced: use blinded independent experts, at least two raters on a calibration subset, adjudicate disagreement, compare judge agreement by slice, randomize answer order, and test repeated runs. Check self-preference (judge's own model family), position bias, verbosity preference, safety/refusal bias, language differences and run-to-run instability. Predefine a human audit budget and failure thresholds before using judge scores for promotion. No calibration experiment is claimed here.

## Leakage, limits and interpretation

The public holdout is reproducibility evidence, not a secret benchmark. Do not optimize future training against it and then claim fresh generalization. Selection uses only dev errors; augmentation never feeds the holdout. Output cache keys include endpoint, model, prompt, parameters, prices, image and question. Provider aliases can drift; pin model snapshots when possible and invalidate cache for fresh inference.

Appropriate: regression engineering, structured evaluation, provenance, product tradeoffs and data-queue demonstrations. Inappropriate: SOTA comparisons, real-world object recognition, safety certification, grasp success, physics/world-model prediction or causal claims that more data improved a neural model.
