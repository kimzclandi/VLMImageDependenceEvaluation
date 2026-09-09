# Public GitHub publication verification

Repository: https://github.com/kimzclandi/vlm-data-flywheel-lab

The owner authenticated GitHub CLI and explicitly authorized creating this public project. The new repository was created without modifying any other repository. Default branch is `main`; project topics were set. The initial seven-stage implementation history was preserved, followed by CI diagnostics, a portability fix and publication documentation.

## Remote content checks

`scripts/verify_remote.py` compared the remote default-branch commit with local HEAD and checked the exact bytes of 11 key README, code, documentation, test, workflow, report and screenshot files. It also retrieved the README anonymously from raw.githubusercontent.com. These checks passed on the initial publication and are rerun after final documentation updates.

For the current checkout, reproduce the read-only verification with:

```bash
python scripts/verify_remote.py kimzclandi/vlm-data-flywheel-lab
```

## Hosted CI evidence

The implementation fix at commit `9f8690081afb2899b536a41161115a1c237c16c7` passed the full hosted Linux/Python 3.14 workflow:

https://github.com/kimzclandi/vlm-data-flywheel-lab/actions/runs/34348667770

Checks included pinned dependency installation, Ruff lint/format, committed-evidence reproduction, offline demo execution, 38 tests (including Dashboard AppTest), dataset validation, publishable-content scan and evidence artifact upload. This is actual hosted execution, not a local-test substitute. Later documentation commits trigger the same workflow; see current branch status at https://github.com/kimzclandi/vlm-data-flywheel-lab/actions .

## Failure, diagnosis and repair

The first run failed at strict data-hash reproduction:
https://github.com/kimzclandi/vlm-data-flywheel-lab/actions/runs/34348199491

The diagnostic run identified only base/augmentation content hash differences, and the first sample differed only in its PNG file hash. Decoded pixels matched. macOS Pillow used `1.3.1.zlib-ng`; Linux used `1.3` zlib, with FreeType `2.14.3` in both. The diagnostic evidence is retained:
https://github.com/kimzclandi/vlm-data-flywheel-lab/actions/runs/34348388967

The fix does not skip validation or discard arbitrary hashes. It independently validates both actual PNG file hashes, checks every decoded RGB pixel and every metadata/label field, and only then aligns derived sample/dataset identities for comparison. It still requires identical predictions, stable metrics, priority queue, augmentations and report text. Stored evidence remains unchanged. New negative tests ensure changed pixels, labels and invalid hashes cannot pass.

`python scripts/check_reproducibility.py --strict-bytes` additionally requires identical compressed PNG bytes and passed in the original local codec environment. The portable default passed on hosted Linux. This distinction between file identity and visual/data equivalence is now documented in the README and Data Card.

No real VLM inference, neural training, real-robot result or online business impact is implied by successful publication or CI.
