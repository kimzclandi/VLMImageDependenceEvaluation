# Contributing

Start with the current saved-generation replay (`python scripts/verify_grounding.py`); the default Dashboard opens the image-intervention experiment. Preserve the separate historical rule workflow when changing shared components. Keep image/question/answer contracts aligned, test known positive and negative controls, and preserve scene-family splits. Do not add private data or credentials.

```bash
python -m pip install -c requirements-lock.txt -e '.[dashboard,dev]'
ruff check .
ruff format --check .
pytest -q
python scripts/verify_grounding.py
python scripts/check_reproducibility.py
```

Changes to data semantics, adapters or answer parsing must explain the affected metric denominator and include a meaningful regression test. Change dataset/generator/prompt versions when semantics change. New training or external API results must identify actual data, model snapshot, commands, configuration, costs if available and limitations. Never relabel a mock experiment as a real model result.

Reports contain measured timestamps and latency; those can vary. Stable data, image hashes, predictions, metrics and decisions should reproduce in the pinned environment. Use a new output directory for exploratory runs rather than overwriting published evidence. Discuss larger architectural changes before adding heavy dependencies.

## Community and documentation checks

Use the issue forms for reproducible bugs and scoped feature requests. Include actual
validation results in the PR template. Run `python3 .github/scripts/check_docs.py`
after editing entry-point documents. See [community conduct](CODE_OF_CONDUCT.md) and
the [maintenance guide](docs/MAINTAINING.md).
