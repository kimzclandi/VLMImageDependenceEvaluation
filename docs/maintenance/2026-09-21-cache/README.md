# API cache integrity — 2026-09-21

API cache entries now contain a schema version, request key, complete reply and reply checksum. The request key binds endpoint, model, image, question, prompt/version and generation/cost parameters. Cache reads check identity, checksum, reply fields and finite nonnegative usage/cost metadata. Successful writes use a same-directory temporary file, flush/fsync and atomic replacement; interrupted replacement preserves an existing entry.

Legacy bare-reply caches, copied entries, modified payloads and malformed metadata become cache misses. **In optional API mode a miss triggers a new potentially billable request.** Keep old caches if needed for historical inspection; no migration pretends they have verified provenance. Offline demo and saved-evidence checks do not call the API.

Malformed provider usage is rejected and not cached. Invalid model-generated answer JSON remains a scoring failure; it is not converted into a successful answer by this change. SHA-256 detects accidental corruption and mismatch, not deliberate forgery by someone able to rewrite both data and checksum.

All new tests use HTTP mock transport and temporary cache directories. No paid API request, training or new model-quality evaluation was performed. Historical records remain unchanged. See `validation.json` for completed checks.
