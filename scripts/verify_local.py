"""Local verification entry point.

Runs exactly what CI runs, minus the network-dependent jobs, so a change can be
checked before it is pushed. Usage:

    python3 scripts/verify_local.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(label: str, command: list[str]) -> None:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def main() -> int:
    run("unit tests", [PYTHON, "-m", "pytest", "-q"])
    run("policy allow", [PYTHON, "policy/check.py", "--action", "deploy", "--now", "2026-10-26T12:00:00Z"])
    run(
        "policy deny on bad canary",
        [PYTHON, "policy/check.py", "--action", "promote", "--now", "2026-10-26T12:00:00Z", "--error-rate", "0.6"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
