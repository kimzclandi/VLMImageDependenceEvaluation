# Publishing documentation updates

The existing repository is [kimzclandi/vlm-image-ablation](https://github.com/kimzclandi/vlm-image-ablation). Check the remote, branch, working tree and remote HEAD before editing. Preserve uncommitted work and frozen research files; use a separate checkout when needed.

After local checks and a reviewed commit:

```bash
git push origin main
python scripts/verify_remote.py kimzclandi/vlm-image-ablation
gh run list --limit 3
```

The verifier compares the remote HEAD and selected file bytes with local files, then retrieves the README without credentials. It lists Actions runs but does not certify success: check the run attached to the exact new commit. Do not force-push or refresh research hashes to accommodate changed evidence.

The [original publication record](../reports/PUBLICATION.md) is historical. `scripts/publish.sh` is retained for the original first-publication workflow; it creates a new repository and must not be rerun for updates to this existing repository. Authentication belongs in local credential storage, never in documents or chat.
