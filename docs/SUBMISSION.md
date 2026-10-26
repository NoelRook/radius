# Devpost submission copy

## Basics

- **Project name:** Radius
- **Tagline:** Agents ship to production. A blast-radius budget decides how far
  they can go.
- **Track:** Path A — Start Fresh
- **Autonomy level:** Hands-off
- **Repository:** https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase
- **Video:** <add public YouTube URL, under 3:00>
- **License:** MIT (visible in the project's About section)

## Short description (for the card, ~200 characters)

Radius is a nine-stage autonomous delivery loop for GitLab Duo. One human
creates a work item; agents plan, code, review, merge, canary, measure and roll
back inside an enforceable error/latency/spend budget.

## Long description

Software agents can write code. They still cannot be trusted to finish the
delivery. GitHub's own cloud agent cannot mark a pull request ready, approve it
or merge it; a human must press the button. GitLab's foundational flows stop at
the merge request. And the data explains why: 90% of developers use AI, but 30%
report little or no trust in its output (DORA 2025), while 46% actively distrust
AI accuracy versus 33% who trust it (Stack Overflow 2025).

Radius closes that gap by making autonomy a **budget**, not a prompt.

The repository contains `autonomy.yaml`: error rate, p95 latency, daily spend,
maximum change size, data classes, freeze windows and the blast radius (a 25%
canary). `policy/check.py` is a deterministic gate over that contract, with
tests and two exit codes that mean something: `0` allow, `2` deny.

One human creates a work item. A custom triage flow reads the contract, writes a
bounded plan and hands off through a chain trigger. The Developer Flow opens a
merge request and marks it ready. The Release Captain checks the contract, merges
with auto-merge, then watches the post-merge pipeline. That pipeline runs all
nine lifecycle stages: plan, create, verify, package, secure, release,
configure, monitor, govern.

The monitor stage is the part that matters. It downloads the previous published
wheel as the stable revision and installs the new wheel as the candidate. It
sends baseline traffic, injects a 60% error fault, sends 30 requests, and asks
the policy engine whether promotion is allowed. On a breach, it stops the
candidate, restarts the stable revision on the live port, and verifies that
`/health` reports the stable revision and build channel. The evidence is a JSON
file with the policy checks, the error rate, the wheel hashes and the live
revision after rollback.

No human merges. No human rolls back. The budget decides.

Radius is deliberately small: a FastAPI service, a policy engine, a canary
harness, two custom flows and a nine-stage pipeline. That is the point. The
governance layer is portable; the service is replaceable.

## How we used GitLab Duo Agent Platform

- **Custom flow — Radius Triage & Plan.** Trigger: work item created. Reads the
  work item and `autonomy.yaml`, posts one plan, never writes code. Completion
  action sets the work item status.
- **Custom flow — Radius Release Captain.** Trigger: merge request marked ready.
  Runs the policy gate, merges with auto-merge, reads the canary artifact and
  comments the promote/rollback decision.
- **Foundational Developer Flow.** Trigger: work item status changed (the chain
  from triage). Creates the branch, code and merge request, then marks it ready.
- **Triggers.** Work item created → status changed → MR marked ready. No cron,
  no bot-initiated mention, no stored human PAT.
- **Tools.** `get_work_item`, `create_work_item_note`, `get_repository_file`,
  `run_command`, `get_pipeline_failing_jobs`, `get_logs_from_job`. The flows can
  read the repo, run `policy/check.py` and `glab`, and write the audit comment.

## Most Stages Covered claim

| Stage | Automation | Evidence |
| --- | --- | --- |
| plan | Triage flow reads the contract and posts a plan | `plan:contract`, issue note |
| create | Developer Flow opens the MR | MR in project |
| verify | pytest, ruff, coverage, policy tests | `verify:*` jobs |
| package | wheel + CycloneDX SBOM published to the registry | `package:wheel` |
| secure | gitleaks, pip-audit, semgrep | `secure:*` jobs |
| release | GitLab Release on `main` | `release:create` |
| configure | rendered runtime config from the contract | `configure:render` |
| monitor | canary + fault injection + policy + rollback | `monitor:canary` |
| govern | nine-stage report, evidence pack, escalation | `govern:report` |

## Why it should win

- **Technological implementation:** a tested policy engine, a real two-process
  canary, a rollback verified by revision and build channel, and a pipeline
  whose stage names match the lifecycle.
- **Design:** one contract, one decision CLI, one evidence pack. A human can read
  the outcome in ten seconds.
- **Potential impact:** platform teams can grant merge/deploy rights to agents
  with limits they can defend in a review, instead of choosing between full
  autonomy and no autonomy.
- **Innovation:** the unit of autonomy is a budgeted canary, not a pull request.
  Rollback is part of the agent loop, not an incident runbook.
- **Presentation:** one human action, a visible plan, a red canary, an automatic
  rollback and a nine-stage evidence table in under three minutes.

## Built with

GitLab Duo Agent Platform (custom flows, triggers, chain triggers, foundational
Developer Flow), GitLab CI/CD, FastAPI, Python 3.12, pytest, ruff, gitleaks,
semgrep, pip-audit, CycloneDX.

## What is next

- A real SLO window (1h/6h) instead of a 30-request canary.
- Per-service contracts in a monorepo, with the policy engine as a reusable CI
  component.
- A GitLab-native scheduler for periodic drift checks (the platform gap tracked
  in gitlab-org/gitlab#590618).
- Signed evidence bundles and an attestation step before promotion.

## Honest limitations

Production is a canary process on the CI runner, not a multi-node cluster. The
error budget is measured over 30 requests. The two custom flows must be
registered once in the UI by a Maintainer/Owner. The first pipeline records a
seed run because no previous package exists yet.
