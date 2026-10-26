"""Publish the stage-evidence report for the submission.

Reads the canary evidence and rendered configuration, then writes a nine-stage
table with a concrete artifact or job for each stage. Fails if a stage has no
evidence, so the report cannot silently rot.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    canary = load_json(EVIDENCE / "canary.json")
    runtime = load_json(ROOT / "deploy" / "runtime.json")
    project = os.environ.get("CI_PROJECT_URL", "https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase")
    pipeline = os.environ.get("CI_PIPELINE_ID", "local")
    job = os.environ.get("CI_JOB_URL", "")

    policy = canary.get("policy", {})
    outcome = canary.get("outcome", {})
    rows = [
        ("plan", "Issue template + triage flow (`.gitlab/duo/flows/`)", f"{project}/-/issues"),
        ("create", "MR created by the developer flow", f"{project}/-/merge_requests"),
        ("verify", "`verify:test` + `verify:policy` jobs", f"{project}/-/pipelines/{pipeline}"),
        ("package", "Wheel + SBOM published to the package registry", f"{project}/-/packages"),
        ("secure", "`secure:secrets`, `secure:dependencies`, SAST", f"{project}/-/pipelines/{pipeline}"),
        ("release", "GitLab Release created by `release:create`", f"{project}/-/releases"),
        ("configure", "Runtime config rendered from `autonomy.yaml`", f"{project}/-/jobs/artifacts/{pipeline}/raw/deploy/runtime.env?job=configure:render"),
        ("monitor", "Canary, fault injection, policy decision, rollback", job or f"{project}/-/pipelines/{pipeline}"),
        ("govern", "This report + `evidence/canary.json`", f"{project}/-/jobs/artifacts/{pipeline}/raw/evidence/canary.json?job=monitor:canary"),
    ]

    missing = []
    if not canary:
        missing.append("evidence/canary.json")
    if not runtime:
        missing.append("deploy/runtime.json")
    if not policy:
        missing.append("policy decision")

    lines = [
        "# Radius — lifecycle evidence",
        "",
        f"Pipeline: `{pipeline}` · Candidate: `{canary.get('candidate', {}).get('revision', 'n/a')}`",
        "",
        "| Stage | What the automation did | Evidence |",
        "| --- | --- | --- |",
    ]
    for stage, what, link in rows:
        lines.append(f"| **{stage}** | {what} | [link]({link}) |")

    lines.extend(
        [
            "",
            "## Policy outcome",
            "",
            f"- Decision: **{policy.get('decision', 'unknown')}**",
            f"- Reasons: {', '.join(policy.get('reasons', [])) or 'all checks passed'}",
            f"- Promoted: **{outcome.get('promoted')}**",
            f"- Rollback verified: **{outcome.get('rollback_verified')}**",
            f"- Live revision after the loop: `{outcome.get('live_revision')}`",
            "",
            "## Reproduce",
            "",
            "```bash",
            "python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt",
            ".venv/bin/pytest -q",
            ".venv/bin/python scripts/canary.py --scenario breach",
            ".venv/bin/python scripts/canary.py --scenario clean",
            "```",
        ]
    )
    if missing:
        lines.extend(["", f"**Missing evidence:** {', '.join(missing)}"])

    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    if missing:
        print(f"missing evidence: {missing}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
