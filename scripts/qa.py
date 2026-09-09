"""Execute the local acceptance gate and save a compact, portable QA receipt."""

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from privacy_check import scan

from flywheel.io import write_json


def main() -> None:
    commands = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "pytest", "-q"],
        [sys.executable, "-m", "flywheel.cli", "validate"],
        [sys.executable, "scripts/check_reproducibility.py"],
    ]
    results = []
    for command in commands:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        printable = "python " + " ".join(command[1:])
        print(printable, "PASS" if completed.returncode == 0 else "FAIL")
        results.append(
            {
                "command": printable,
                "returncode": completed.returncode,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
            }
        )
        if completed.returncode:
            print(completed.stdout, completed.stderr)
    privacy = scan()
    passed = all(r["returncode"] == 0 for r in results) and not privacy["issues"]
    write_json(
        Path("reports/qa.json"),
        {
            "utc": datetime.now(UTC).isoformat(),
            "status": "PASS" if passed else "FAIL",
            "checks": results,
            "privacy": privacy,
            "remote_actions": "not checked by local QA; see reports/PUBLICATION.md and live GitHub Actions",
        },
    )
    print("Local acceptance:", "PASS" if passed else "FAIL")
    raise SystemExit(not passed)


if __name__ == "__main__":
    main()
