"""Conservative tracked/publishable-content scan. Never print matched secrets."""

import re
import subprocess
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{24,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
    re.compile(r"(?:Cookie|Authorization):\s*(?:Bearer\s+)?[A-Za-z0-9_-]{20,}", re.I),
]


def scan() -> dict:
    raw = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    )
    files = sorted(set(path.decode() for path in raw.split(b"\0") if path))
    issues = []
    for name in files:
        path = Path(name)
        if not path.is_file():
            continue
        if name == ".env" or name.endswith("secrets.toml"):
            issues.append({"file": name, "issue": "sensitive configuration file"})
        if path.suffix.lower() in (".png", ".jpg", ".zip", ".bundle"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for index, pattern in enumerate(PATTERNS):
            if pattern.search(text):
                issues.append({"file": name, "issue": f"pattern_{index}"})
    return {
        "files_scanned": len(files),
        "issues": issues,
        "scope": "tracked and unignored publishable files; heuristic text scan, not a security guarantee",
    }


if __name__ == "__main__":
    import json

    result = scan()
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["issues"]))
