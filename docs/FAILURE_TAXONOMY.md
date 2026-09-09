# Failure taxonomy and review protocol

An answer mismatch is an observed symptom. A root cause is a hypothesis requiring additional evidence. The classifier assigns a primary task-based label only; it does not infer hidden model cognition. Every automatic semantic label is marked `provisional`.

## Categories

| Type | Definition and example | Rule / evidence needed | Possible root cause | First intervention | Common confusion |
|---|---|---|---|---|---|
| perception_error | Visible property/object misrecognized; blue square read as green | Human visual audit plus focused object/property probes; **not auto-inferred** | Resolution, palette ambiguity, visual encoder | Inspect image/labels; collect perception contrasts; model analysis | attribute_binding_error |
| spatial_reasoning_error | Correct entities but wrong relation; above/below inverted | Auto hypothesis for a spatial task mismatch; confirm object recognition separately | Coordinate convention or relational reasoning | Relation-controlled data; clarify prompt convention | perception_error, ambiguous_sample |
| attribute_binding_error | Correct attributes combined with wrong entity; red circle confused with red square | Auto hypothesis for existence/counterfactual mismatch; confirm attributes individually | Compositional binding or attention shortcut | One-attribute contrasts and near matches | perception_error, distractor_susceptibility |
| counting_error | Wrong number of matching objects; small instances omitted | Auto hypothesis for count-task mismatch; inspect inclusion predicate | Counting, filter omission or visual omission | Count-by-condition strata; zero-count cases | perception_error, instruction_following_error |
| instruction_following_error | One instruction condition dropped; selecting large and small despite “small” | Auto hypothesis for target/multi-condition selection mismatch | Condition parsing, conjunction or output semantics | Factorized condition tests, prompt clarification, targeted contrasts | attribute_binding_error, output_format_error |
| distractor_susceptibility | Prediction fails only after irrelevant/similar objects are added | Human compares matched before/after predictions; **not inferred from distractor tag alone** | Attention interference or shortcut | Controlled distractor sets; preserve target | perception_error, attribute_binding_error |
| output_format_error | JSON invalid or answer violates expected domain | Deterministic parser; e.g. free text, boolean, duplicate selected ID | Prompt contract, serialization or model formatting | Prompt/parser contract; retry policy if explicitly evaluated | instruction_following_error |
| abstention_or_refusal | Provider explicitly refuses the benign synthetic task | Adapter message.refusal sets error_status=refusal; arbitrary “I refuse” text is only malformed output until reviewed | Safety over-refusal, uncertainty, unsupported input | Inspect refusal and policy applicability, not blindly force compliance | system_or_api_error, output_format_error |
| system_or_api_error | No usable inference because HTTP/network/response-envelope failure | Adapter error status; HTTP 401/429/5xx, timeout | Credentials, rate limit, network, malformed server response | Repair infrastructure first; preserve denominator | abstention_or_refusal |
| ambiguous_sample | More than one reasonable interpretation under spec | Human adjudication; e.g. ambiguous relation boundary or unreadable ID | Prompt/data spec ambiguity | Quarantine and clarify evaluation spec | annotation_error, perception_error |
| annotation_error | Ground truth disagrees with unambiguous scene/query | Oracle validation fails or independent reviewer demonstrates wrong label | Generator/annotation bug | Fix labels in new dataset version; replay evaluation | ambiguous_sample, model error |

Correct answers have `failure_type=null`. Precedence: explicit refusal → system error → parser error → correct → semantic task hypothesis. Categories such as perception/distractor/annotation require additional evidence and can be assigned by human review. Multiple causes may coexist; this MVP stores a primary label plus evidence note, not a complete causal graph.

## Review loop

1. Open the image, question, query, gold answer and raw output in Failure review.
2. First check data readability and annotation, then API/format issues, then semantic hypotheses.
3. Edit a row in `reports/demo/review_queue.csv`: fill `failure_type` with an allowed category and `note` with a specific observation. Do not include reviewer personal information.
4. Re-evaluate into a **new local run**, retaining the original evidence:

```bash
flywheel evaluate --outputs reports/demo/v1_outputs.jsonl --reviews reports/demo/review_queue.csv --report-dir reports/local/reviewed
flywheel prioritize --old-scores reports/local/reviewed/scores.jsonl --report-dir reports/local/reviewed
```

5. Review changes taxonomy and production eligibility, not the saved truth or accuracy. Annotation repairs require a new dataset, regenerated hashes and new predictions; content alignment checks intentionally prevent applying old predictions to edited samples.

For an enterprise pilot, double-label a stratified subset, measure agreement by category, adjudicate systematic disagreements and audit difficult/rare failure categories. No human calibration or external annotator work has been performed for this repository.
