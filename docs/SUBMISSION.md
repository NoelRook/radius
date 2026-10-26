# Devpost submission copy

## Basics

- **Project name:** Radius
- **Tagline:** Agents ship to production. A blast-radius budget decides how far they can go.
- **Track:** Path A — Start Fresh
- **Autonomy level:** Hands-off
- **Repository:** https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase
- **Video:** <add public YouTube URL, under 3:00>
- **License:** MIT (visible in the project's About section)

## Short description (for the card, ~200 characters)

Radius is a nine-stage autonomous delivery loop for GitLab Duo. One human creates a work item; agents plan, code, merge, canary, measure and roll back inside an enforceable error/latency/spend budget.

## Long description

Software agents can write code. They still cannot be trusted to finish the delivery. GitHub's own cloud agent cannot mark a pull request ready, approve it or merge it; a human must press the button. GitLab's foundational flows stop at the merge request. The data explains why: 90% of developers use AI, but 30% report little or no trust in its output (DORA 2025), while 46% actively distrust AI accuracy versus 33% who trust it (Stack Overflow 2025).

Radius closes that gap by making autonomy a **budget**, not a prompt.

The repository contains `autonomy.yaml`: error rate, p95 latency, daily spend, maximum change size, data classes, freeze windows and the blast radius. `policy/check.py` is a deterministic gate over that contract, with tests and two exit codes that mean something: `0` allow, `2` deny.

One human creates a work item. The **Radius Triage & Plan** flow reads the contract, writes the smallest bounded change, commits it to a feature branch, opens the merge request and posts a plan that quotes the budget, rollback path and `Human actions required: 0`. No assignment, no second click, no status chain.

The **Radius Release Captain** flow starts on `Merge request → Created`. It computes the diff size, runs the policy gate, then merges through the flow service account's Git credential. That merge path is deliberate: the flow's API token is scoped to `ai_workflows`, and ambient flows do not receive project CI/CD variables, so a human PAT is not required and no long-lived token is stored in the flow.

The merged pipeline runs all nine lifecycle stages: plan, create, verify, package, secure, release, configure, monitor, govern.

The monitor stage is the part that matters. It builds the previous commit's wheel as the **stable** revision and the current wheel as the **candidate**. It sends baseline traffic, injects a controlled 60% error fault, sends 30 requests, and asks the policy engine whether promotion is allowed. On a breach, it stops the candidate, restarts the stable revision on the live port, and verifies that `/health` reports the stable revision **and** build channel. The evidence is a JSON file with the policy checks, the error rate, the wheel hashes and the live revision after rollback.

The verified run: issue #3 → Triage session 10056015 → MR !9 → Release session 10056111 → merge `1506fbc8` → pipeline 2989901218 → **16/30 requests failed (53.3%)** → policy **DENY** (`error_budget`, limit 2%) → **rollback_verified=true** to `baseline-d5274e72`, channel `baseline`. The release gate comment ends with `Decision: ROLLED BACK` and `Human actions required: 0`.

No human merges. No human rolls back. The budget decides.

Radius is deliberately small: a FastAPI service, a policy engine, a canary harness, two custom flows and a nine-stage pipeline. That is the point. The governance layer is portable; the service is replaceable.

## How we used GitLab Duo Agent Platform

- **Custom flow — Radius Triage & Plan.** Trigger: Work item → Created (Issue). Tools: `get_work_item`, `get_work_item_notes`, `create_work_item_note`, `get_repository_file`, `find_files`, `read_file`, `run_command`, `create_merge_request`. It reads `autonomy.yaml`, edits the service, commits to `radius/auto-<iid>`, opens the MR and posts the plan. It never merges.
- **Custom flow — Radius Release Captain.** Trigger: Merge request → Created. Tools: `run_command`, `get_work_item`, `create_work_item_note`, `get_pipeline_failing_jobs`, `get_job_logs`, `get_repository_file`, `create_commit`, `update_merge_request`. It runs the policy gate, merges via the service account's Git credential, polls the main pipeline, downloads the canary artifact, and posts the release gate.
- **Triggers.** Two triggers, both created in the project: Work item Created → Triage; Merge request Created → Release Captain. No cron, no bot mention, no assignment step.
- **Platform constraints handled.** Ambient flows do not receive CI/CD variables; the flow API token is scoped to `ai_workflows`; custom flows require Maintainer/Owner to register. The design works within all three instead of pretending they do not exist.
- **Why two flows, not more.** Each custom flow creates its own agents and cannot call another custom flow. Triage therefore owns plan + create, and Release Captain owns verify-to-govern, with the pipeline carrying the deterministic work.

## Most Stages Covered claim

| Stage | Automation | Evidence |
| --- | --- | --- |
| plan | Triage flow reads the contract and posts a bounded plan | issue #3 `## Radius plan`, `plan:contract` job |
| create | Triage flow commits the change and opens MR !9 | branch `radius/auto-3`, MR !9 |
| verify | pytest, ruff, coverage, policy tests, Python 3.9 parity | `verify:*` jobs |
| package | wheel + CycloneDX SBOM, published to the generic registry | `package:wheel`, `package:publish` |
| secure | gitleaks, pip-audit, semgrep | `secure:*` jobs |
| release | GitLab Release on `main` | `release:create` |
| configure | rendered runtime config from the contract | `configure:render` |
| monitor | canary + controlled fault + policy + verified rollback | pipeline 2989901218, job 17470242282 |
| govern | nine-stage report, evidence pack, release gate | `govern:report`, `## Radius release gate` note |

## Why it should win

- **Technological implementation:** a tested policy engine, a real two-process canary, a rollback verified by revision and build channel, a flow that survives Python 3.9 without PyYAML, and a pipeline whose stage names match the lifecycle.
- **Design:** one contract, one decision CLI, one evidence pack. A human can read the outcome in ten seconds.
- **Potential impact:** platform teams can grant merge/deploy rights to agents with limits they can defend in a review, instead of choosing between full autonomy and no autonomy.
- **Innovation:** the unit of autonomy is a budgeted canary, not a pull request. Rollback is part of the agent loop, not an incident runbook.
- **Presentation:** one human action, a visible plan, a red canary, an automatic rollback and a nine-stage evidence table in under three minutes.

## Built with

GitLab Duo Agent Platform (custom flows, triggers, ambient coding environment), GitLab CI/CD, FastAPI, Python 3.12 and 3.9, pytest, ruff, gitleaks, semgrep, pip-audit, CycloneDX.

## What is next

- A real SLO window (1h/6h) instead of a 30-request canary.
- Per-service contracts in a monorepo, with the policy engine as a reusable CI component.
- A GitLab-native scheduler for periodic drift checks (the platform gap tracked in gitlab-org/gitlab#590618).
- Signed evidence bundles and an attestation step before promotion.

## Honest limitations

Production is a canary process on the CI runner, not a multi-node cluster. The error budget is measured over 30 requests. The two custom flows must be registered once in the UI by a Maintainer/Owner (the hackathon role allowed it). The merge uses the flow service account's Git credential because protected `main` allows Developer push; the API-token path is blocked by the `ai_workflows` scope. The first pipeline after a fresh clone records a seed run because no previous package exists yet; the verified run above is a real rollback against the previous commit.
