# Radius

**Agents ship to production. A blast-radius budget decides how far they can go.**

[![GitHub CI](https://github.com/NoelRook/radius/actions/workflows/ci.yml/badge.svg)](https://github.com/NoelRook/radius/actions/workflows/ci.yml)
[![GitLab pipeline](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/badges/main/pipeline.svg)](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/pipelines)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Repository mirror.** The autonomous loop runs on GitLab Duo Agent Platform;
> the verified end-to-end run and nine-stage pipeline live in the
> [GitLab project](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase).
> This GitHub mirror runs the deterministic verification suite on every push.

Radius is a nine-stage autonomous delivery loop for GitLab Duo Agent Platform.
One human creates a work item. From there, agents plan, open a merge request,
run the nine-stage pipeline, pass security gates, merge, deploy a canary, measure
it against an error/latency/spend budget, and either promote or roll back — with
a JSON evidence pack for every decision.

The boundary is not a prompt. It is [`autonomy.yaml`](autonomy.yaml), a
versioned contract enforced by [`policy/check.py`](policy/check.py) in CI and
read by the agents.

> Built for **GitLab Transcend — Life After Code**, Path A (Start Fresh),
> **Hands-off** autonomy. No Google Cloud dependency.

## The problem, in numbers

- **90%** of developers use AI, but **30%** report little or no trust in its
  output ([DORA 2025](https://dora.dev/research/2025/dora-report/)).
- **46%** distrust AI accuracy versus **33%** who trust it; only **3%** highly
  trust it ([Stack Overflow 2025](https://survey.stackoverflow.co/2025/ai)).
- GitHub's own coding agent **cannot mark a PR ready, approve or merge**; a
  human must do it
  ([GitHub Docs](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/risks-and-mitigations)).
- GitLab has **no time-based triggers** and **bots cannot start flows**; the
  documented workaround needs a long-lived human PAT
  ([gitlab-org/gitlab#590618](https://gitlab.com/gitlab-org/gitlab/-/work_items/590618),
  [Triggers](https://docs.gitlab.com/user/duo_agent_platform/triggers/)).

Agents are capable enough to write the code. The missing piece is a way to let
them finish the job **without asking a human to be the merge button** — and
without trusting them blindly when production disagrees with CI.

Full evidence and gap analysis: [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

## The loop

```
human creates ONE work item
        │
        ▼  trigger: work item created
┌───────────────────────┐
│ Triage & Plan         │  reads autonomy.yaml, writes the change,
└──────────┬────────────┘  opens branch + merge request, posts the plan
           ▼  trigger: merge request created
┌───────────────────────┐
│ Release Captain       │  policy check → merge via Git credential
└──────────┬────────────┘  → watch pipeline → read canary evidence
           ▼  pipeline
 plan → create → verify → secure → package → release → configure → monitor → govern
                                              │            │
                                              │            ├─ canary against the stable revision
                                              │            ├─ error/latency budget
                                              │            └─ rollback + /health proof
                                              ▼
                                     evidence/canary.json
                                     evidence/REPORT.md
```

Every stage is a real job in [`.gitlab-ci.yml`](.gitlab-ci.yml); the stage table
with one evidence link per stage is [`docs/STAGES.md`](docs/STAGES.md).

## The contract

```yaml
spec:
  service:
    environment: production
    data_class: internal
  budgets:
    error_rate_max: 0.02          # 2%
    latency_p95_ms_max: 800
    spend_usd_per_day_max: 5.00
    change_lines_max: 400
    blast_radius: canary
    canary_traffic_percent: 25
  freeze_windows:
    - name: month-end-close
      starts_at: 2026-10-30T22:00:00Z
      ends_at:   2026-11-02T02:00:00Z
  escalation:
    require_human_for: [freeze_window, budget_breach, data_class_violation]
```

`policy/check.py` is a deterministic, dependency-light gate:

```bash
python policy/check.py --action promote --error-rate 0.60
# exit 2, "error_budget: error_rate=0.600 limit=0.020"
```

The same file is read by the agents, so the soft gate and the hard gate cannot
drift apart.

## What the demo shows

1. A human creates one work item from the **Radius ship** template.
2. The triage flow posts a plan that quotes the real budgets and chooses
   `PROCEED` or `ESCALATE`.
3. The Triage flow commits the smallest change to a branch and opens the MR.
4. The Release Captain checks the contract and merges through the Git
   credential available to the flow.
5. The pipeline builds a wheel, publishes it, runs a canary against the previous
   published revision, injects a controlled fault, and evaluates the budget.
6. The policy denies promotion. The harness stops the candidate, restarts the
   previous revision, and proves it with `/health`.
7. The Release Captain reads `evidence/canary.json` and comments the rollback
   with the live revision and the policy reason.

Then the presenter runs the healthy canary job manually to show the same loop
promoting a good revision. Two outcomes, one contract.

## Verification

```bash
python -m pytest -q          # 16 tests
ruff check .                 # clean
python scripts/canary.py --scenario breach --requests 20
python scripts/canary.py --scenario clean  --requests 15
python scripts/stage_report.py
```

Measured locally on 26 Oct 2026:

| Run | Result |
| --- | --- |
| End-to-end breach | Issue #3 → Triage session 10056015 → MR !9 → Release session 10056111 → pipeline [2989901218](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/pipelines/2989901218): **16/30 failed (53.3%)**, policy denied, **rollback verified** to `baseline-d5274e72` (channel `baseline`) |
| Earlier breach | 19/30 failed (63.3%), policy denied, rollback verified to `baseline-fd56add3` |
| Healthy | 15 requests, policy allowed, candidate **promoted** |
| Freeze | merge denied with `freeze_window` reason |

Evidence files are written to `evidence/` (JSON + Markdown) and uploaded by the
`monitor` and `govern` jobs.

## Judging map

| Criterion | What to look at |
| --- | --- |
| **Technological implementation** | real policy engine with tests, real two-process canary, automatic rollback verified by revision, nine CI stages, flow YAML linted in CI |
| **Design** | one contract file, one decision CLI, stage names that match the lifecycle, evidence pack a human can read in 10 seconds |
| **Potential impact** | directly addresses the 30–46% trust gap; lets platform teams grant merge/deploy rights with enforceable limits |
| **Innovation** | the unit of autonomy is a **budgeted canary**, not a PR; rollback is part of the agent loop, not an incident runbook |
| **Presentation** | one human action → visible plan → red canary → automatic rollback → evidence, in under 3 minutes |

## Repository layout

```
app/                 FastAPI demo service (/health, /quote, /work, /metrics, /admin/chaos)
policy/              deterministic contract engine + tests
scripts/             canary harness, config renderer, stage report, flow linter
.gitlab/duo/flows/   source of truth for the two custom flows
.gitlab/issue_templates/ship.md
autonomy.yaml        the contract
docs/                evidence, stage table, runbook
.gitlab-ci.yml       nine-stage pipeline
```

## Run it locally

Requires Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python scripts/canary.py --scenario breach --requests 20
python scripts/canary.py --scenario clean  --requests 15
```

No external services, no cloud account, no credentials.

## Registering the flows

The flow YAML in `.gitlab/duo/flows/` is the source of truth, but GitLab
requires custom flows to be created in the UI (Maintainer/Owner). Exact steps,
trigger configuration and the two-trigger setup are in
[`docs/FLOW_REGISTRATION.md`](docs/FLOW_REGISTRATION.md), with the full operating
runbook in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Limitations

- Production is a canary process on the CI runner, not a multi-node cluster.
- The error budget is measured over 30 requests, not a long SLI window.
- The flows need to be registered once in the UI; see the runbook.
- Radius is a reference implementation for one service, not a deployment
  platform.

## License

MIT — see [`LICENSE`](LICENSE).
