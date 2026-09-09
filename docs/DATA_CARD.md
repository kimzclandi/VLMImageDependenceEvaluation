# Data card: tabletop-v1

**Source and license:** original procedural scenes produced by this repository; generated images and JSONL use CC0-1.0 (`data/LICENSE`). Code is MIT. No third-party image corpus, people, faces, company or school content.

## Composition and intended use

Default: 240 samples, 120 paired scene families, 6 equally weighted task buckets (40 samples each). Each task has 20 groups and two samples per group. Seed 42. Dev: 168 samples / 84 families. Holdout: 72 samples / 36 families. `group % 3 == 2` defines holdout before any model call. Difficulty is generated with `(group // 3) % 3`, independently of split assignment: 96 easy, 72 medium, 72 hard across the original dataset.

All related originals/variants remain in one split. Images can repeat *within* a family for swapped spatial queries, but never across splits. `sample_id` includes seed, task, group and variant; content hashes are authoritative because IDs alone do not distinguish every generator configuration.

## Visual and answer semantics

512×384 RGB image, 4/5/7 nonoverlapping objects at jittered grid centers; red, blue, green or yellow; circles, squares or triangles. “Small” has bounding half-width 18 pixels, “large” 27 pixels. `x` grows right, `y` grows down. Left/right/above/below compare centers strictly; adjacent means Euclidean center distance ≤150 px. Object IDs are printed below shapes. No physical depth, occlusion or hidden objects. The gray frame and text are not query objects.

Spatial pairs swap subject and reference; adjacency is symmetric and therefore intentionally answer-preserving. Other original pairs change only o1's color. Attribute/counterfactual existence labels flip yes→no. Counting pairs may be 1→0 or differ by one in a color-only set. Select answers list **every** matching ID, sorted lexicographically, or `none`.

## Schema

Machine schema: `schemas/sample.schema.json`; validation also checks actual file hashes, full decoded raster correspondence, question/query agreement, geometry, identities and oracle labels. File hashes identify encoded PNG bytes; reproducibility across different lossless PNG codecs is tested with exact decoded RGB equality before aligning derived hashes for comparison.

| Field | Meaning |
|---|---|
| sample_id / group_id / parent_id | unique instance / split family / lineage |
| image_path / image_sha256 | dataset-relative PNG path / hash of actual file bytes |
| question / ground_truth | rendered English query / canonical string answer |
| task_type / difficulty / tags | capability, controlled object-count difficulty, descriptive slices |
| scene_metadata | dimensions and objects with id, color, shape, size, x, y |
| query | executable query specification used by oracle; not sent to API |
| data_source / generator_version | original procedural source / semantic generator version |
| dataset_version / split | frozen dataset label / dev, holdout or augmentation |
| annotation_confidence | 1.0 = passed synthetic structural checks, **not human confidence** |
| mutation / answer_changed | operator and whether augmentation changed oracle answer |

`scene_metadata`, `query`, `ground_truth` are privileged evaluation data. The real API payload contains only question + image; reference adapters intentionally receive metadata and must never be described as visual models.

## Cleaning, deduplication and quality

Reject malformed schemas, duplicate sample IDs, repeated scene+query fingerprints, bad labels, hash mismatches, unsafe paths and object/label collisions. Reject any base image crossing dev/holdout. Generate augmentation only from selected dev parents, recompute labels, and reject fingerprints already in original or accepted augmented pools. Split-family identity is inherited.

Color substitution jointly permutes scene/query and should preserve answer. Counterfactual augmentation must change oracle answer through one object property or one relation token. Other operators can preserve or change labels; `answer_changed` records which. Check `augmentation/manifest.json` for accepted/skipped operators. No fabricated annotations.

## Known bias and retention

ID selection, clean grid, limited vocabulary and a fixed color palette create strong shortcuts. Difficulty is a controlled construction factor, not an empirically calibrated human/model difficulty score. This dataset is for pipeline validation. Public holdout must not be repeatedly optimized against and cited as fresh evidence. Keep versioned manifests and reports; create a new seed and restricted holdout for future real experiments. Do not overwrite a published evidence version without changing generator/data version and rerunning QA.
