#!/usr/bin/env bash
# Publishes only this new named repository; never overwrites an existing remote.
set -euo pipefail
cd "$(dirname "$0")/.."
gh auth status
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Commit reviewed changes before publishing.' >&2
  exit 1
fi
if git remote get-url origin >/dev/null 2>&1; then
  echo 'origin already exists; inspect it manually rather than overwriting it.' >&2
  exit 1
fi
python scripts/privacy_check.py
owner="$(gh api user --jq .login)"
repo="$owner/vlm-data-flywheel-lab"
gh repo create "$repo" --public --source=. --remote=origin --push \
  --description 'Reproducible synthetic tabletop evaluation, failure triage and data strategy workflow. Offline reference demonstration; no model training claims.'
gh repo edit "$repo" --add-topic vlm --add-topic embodied-ai --add-topic data-flywheel \
  --add-topic model-evaluation --add-topic synthetic-data --add-topic ai-product-management \
  --add-topic failure-analysis
python scripts/verify_remote.py "$repo"
