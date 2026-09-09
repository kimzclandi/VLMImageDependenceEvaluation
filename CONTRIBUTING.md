# Contributing

Reproduce the offline workflow before changing it. Keep image/question/answer contracts aligned, test known positive and negative controls, and preserve scene-family splits. Do not add private data or credentials.

```bash
python -m pip install -c requirements-lock.txt -e '.[dashboard,dev]'
ruff check .
ruff format --check .
pytest -q
python scripts/check_reproducibility.py
```

Changes to data semantics, adapters or answer parsing must explain the affected metric denominator and include a meaningful regression test. Change dataset/generator/prompt versions when semantics change. New training or external API results must identify actual data, model snapshot, commands, configuration, costs if available and limitations. Never relabel a mock experiment as a real model result.

Reports contain measured timestamps and latency; those can vary. Stable data, image hashes, predictions, metrics and decisions should reproduce in the pinned environment. Use a new output directory for exploratory runs rather than overwriting published evidence. Discuss larger architectural changes before adding heavy dependencies.
