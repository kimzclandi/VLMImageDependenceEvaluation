"""Read-only verification of a public remote's exact HEAD and required artifacts."""

import base64
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


def api(endpoint: str):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], text=True))


def main() -> None:
    repo = sys.argv[1]
    info = api(f"repos/{repo}")
    assert not info["private"], "Repository is not public"
    branch = info["default_branch"]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert api(f"repos/{repo}/commits/{branch}")["sha"] == head, "Remote HEAD differs"
    required = [
        "README.md",
        "README.zh-CN.md",
        "src/flywheel/pipeline.py",
        "src/flywheel/adapters.py",
        "docs/DATA_STRATEGY.md",
        "docs/EXPERIMENT_REPORT.md",
        "dashboard.py",
        "tests/test_end_to_end.py",
        ".github/workflows/ci.yml",
        "reports/demo/summary.json",
        "assets/dashboard.png",
    ]
    for name in required:
        remote = api(f"repos/{repo}/contents/{name}?ref={head}")
        assert base64.b64decode(remote["content"]) == Path(name).read_bytes(), name
    # No credentials in this read: confirms the README is publicly retrievable.
    request = urllib.request.Request(
        f"https://raw.githubusercontent.com/{repo}/{head}/README.md",
        headers={"User-Agent": "flywheel-public-verification"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.read() == Path("README.md").read_bytes()
    print(
        f"Verified public repository, exact HEAD and {len(required)} key artifacts: {info['html_url']}"
    )
    subprocess.run(
        ["gh", "run", "list", "--repo", repo, "--commit", head, "--limit", "3"], check=True
    )
    print(
        "Workflow existence is verified; inspect run status separately before claiming CI passed."
    )


if __name__ == "__main__":
    main()
