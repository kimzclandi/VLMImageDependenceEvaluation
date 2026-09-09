# GitHub publication

The project was built as an isolated repository with staged implementation commits. The available GitHub CLI reported **not logged in** during this delivery. No public repository, remote verification or hosted Actions success is claimed.

The user must authenticate their own GitHub account; no token should be pasted into a chat or committed file. From this repository:

```bash
gh auth login
source .venv/bin/activate
bash scripts/publish.sh
```

The publish script checks authentication, clean worktree and absence of origin, scans publishable files, creates only a **new** `vlm-data-flywheel-lab` public repository, pushes current history, sets topics and runs read-only remote verification. GitHub creation fails if that name already exists; it never deletes or force-pushes another repository. An existing origin is a stop condition requiring inspection, not permission to overwrite it.

`verify_remote.py OWNER/vlm-data-flywheel-lab` compares exact remote HEAD and key README/code/docs/image/workflow/report bytes against local files, and retrieves the raw README without credentials to confirm public access. It lists Actions runs but does not claim they succeeded. After publication, inspect:

```bash
gh run list --limit 3
gh run watch
```

If creation succeeds but network failure interrupts push/verification, inspect `git remote -v` and the target repository first. Retry `git push -u origin main` only after confirming origin points to the new project, then run the verifier. Do not rerun creation against another existing repository.

Local commit identity is a generic contributor identity to avoid exposing local account information. It is not an assertion about a GitHub account. A future authenticated owner may choose their own public commit identity for new work.
