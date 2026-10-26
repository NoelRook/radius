"""Assert that every lifecycle stage the submission claims is wired in CI.

This is a guard against documentation drift: if someone removes a job, the
pipeline fails instead of quietly dropping a stage from the story.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_STAGES = ["plan", "create", "verify", "package", "secure", "release", "configure", "monitor", "govern"]


def main() -> int:
    ci = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    stages_doc = (ROOT / "docs" / "STAGES.md").read_text(encoding="utf-8")

    missing_ci = [stage for stage in REQUIRED_STAGES if stage not in ci]
    missing_doc = [stage for stage in REQUIRED_STAGES if stage not in stages_doc]
    if missing_ci or missing_doc:
        print(f"missing from CI: {missing_ci}")
        print(f"missing from docs: {missing_doc}")
        return 1
    print(f"all {len(REQUIRED_STAGES)} lifecycle stages are wired and documented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
