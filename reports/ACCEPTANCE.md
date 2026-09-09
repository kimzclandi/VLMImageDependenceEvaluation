# Local acceptance receipt

Status: **local deliverable verified; public GitHub publication blocked by missing CLI authentication**.

## Executed checks

| Requirement | Result | Evidence |
|---|---|---|
| Original data generation | PASS: 240 samples / 120 families | data/sample/manifest.json |
| Image and metadata correspondence | PASS: schema, hashes, full raster re-render comparison and independent center-pixel tests | flywheel validate; tests/test_data.py |
| Structured baseline outputs | PASS: v1/v2 each 240 outputs, no gold input field | reports/demo/v1_outputs.jsonl; v2_outputs.jsonl |
| Actual metrics and uncertainty | PASS: task/difficulty/split/tag slices, errors, parse failures, latency, cost fields, cluster bootstrap | reports/demo/summary.json |
| Failure taxonomy and human review | PASS: automatic provisional categories, export and review ingestion tests | review_queue.csv; tests/test_evaluation.py |
| Explainable prioritization | PASS: 94 dev failures scored, 18 diverse families selected | priority_queue.jsonl |
| Augmentation | PASS: 108 unique examples, six operators ×18, no original-content duplicates | data/sample/augmentation/manifest.json |
| Fixed-set regression | PASS: candidate rejected; counting loses 7/12 holdout successes | summary.json → holdout_regression |
| Dashboard | PASS: actual local server on loopback; 4 workspaces checked in browser and AppTest | assets/dashboard.png; dashboard-metrics.png; failure-review.png; data-production.png |
| Unit/integration/end-to-end/UI tests | PASS: 34 tests | python -m pytest -q |
| README command parity | PASS: pinned install, demo, generate, validate, infer, evaluate, prioritize, compare, reproducibility and QA executed | CLI outputs; scripts/qa.py |
| Lint / format / dependencies | PASS: Ruff check/format, pip check | reports/qa.json |
| Privacy | PASS: publishable-content scan; no detected credential or personal-path patterns; screenshots inspected | scripts/privacy_check.py; reports/qa.json |
| CI syntax/configuration | PASS: YAML parsed locally, expected job/steps checked; shell script syntax checked | .github/workflows/ci.yml; bash -n scripts/publish.sh |
| CI remote execution | NOT RUN | GitHub CLI not authenticated |
| Public repository / remote files | NOT CREATED / NOT VERIFIED | docs/PUBLISHING.md |

The CI YAML check is local structural validation, not a hosted workflow execution. Secret scanning is heuristic, not a proof that no conceivable sensitive content exists. Source and generated images are original project artifacts; no personal photo or private dataset was added.

## Measured result, carefully stated

Fixed holdout n=72 / 36 scene families: metadata-rule v1 30/72 (41.7%), v2 65/72 (90.3%). Paired delta +48.6 pp, cluster bootstrap interval [+30.6, +65.3] pp. Counting falls from 12/12 to 5/12, so the candidate is rejected. These are deliberately different deterministic rules; no neural model learned from augmentation.

Production uses 18 dev parent families: 10 instruction-following and 8 target-selection, producing 60 and 48 respective augmented samples. This allocation reflects configured priority weights and the dominant v1 failure mode; it is not proof of optimal training-data allocation. All other capabilities remain in the fixed regression suite.

## Visual inspection

Inspected the actual rendered overview metrics, capability/failure charts, failure image/question/gold/output, production parent/one-attribute counterfactual, data distributions, and configuration/provenance workspace. Also inspected the six-task generated scene gallery. Saved screenshots are browser captures, not design mockups. Long JSON evidence and the production queue intentionally scroll within the UI.

## Reproducibility boundary

Dataset JSON, PNG hashes, predictions, stable metrics, selected queue, augmentations and Markdown report reproduce under the pinned local environment. Timestamps and measured latency are real and intentionally excluded from exact comparisons. Source file hashes and dependency lock hash are saved in reports/demo/environment.json. The broader OS/Python matrix has not been run locally.

## Remaining external step

Authenticate with `gh auth login`, then from the project environment run `bash scripts/publish.sh`. The script will create only the new named public repository, set topics, push the staged history and compare remote HEAD/key files, including an anonymous README retrieval. Inspect actual Actions status afterwards. No credentials need to be sent through this chat.
