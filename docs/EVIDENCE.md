# Evidence: the gap Radius fills

Snapshot: **26 October 2026**. Every claim below links to a primary source that
was read on that date. Where the evidence is about GitLab itself, the link is a
GitLab doc, issue or support article so a judge can re-check it in one click.

## 1. The market signal: adoption is high, trust is not

| Finding | Number | Source |
| --- | --- | --- |
| Developers using AI in their work | **90%** | [DORA, State of AI-assisted Software Development 2025](https://dora.dev/research/2025/dora-report/) |
| Report little or no trust in AI-generated code | **30%** | [DORA 2025](https://www.thoughtworks.com/content/dam/thoughtworks/documents/report/tw_report_state_of_ai_assisted_software_development_2025.pdf) |
| Never interact with AI in agent mode | **61%** | [DORA 2025](https://www.thoughtworks.com/content/dam/thoughtworks/documents/report/tw_report_state_of_ai_assisted_software_development_2025.pdf) |
| Actively distrust AI accuracy vs. trust it | **46% vs 33%** | [Stack Overflow Developer Survey 2025 — AI](https://survey.stackoverflow.co/2025/ai) |
| Say AI output is "almost right, but not quite" | **45%** | [Stack Overflow 2025](https://stackoverflow.co/company/press/archive/stack-overflow-2025-developer-survey/) |
| Spend more time fixing AI-generated code | **66%** | [Stack Overflow 2025](https://stackoverflow.blog/2025/12/29/developers-remain-willing-but-reluctant-to-use-ai-the-2025-developer-survey-results-are-here/) |
| Would still ask a human when they do not trust AI | **75%** | [Stack Overflow 2025](https://survey.stackoverflow.co/2025/ai) |

DORA's own conclusion is the thesis of this project: AI is an **amplifier** of
an organisation's existing strengths and weaknesses, and the returns come from
the system around the tool, not the tool alone
([DORA 2025](https://dora.dev/research/2025/dora-report/)).

**Gap G1 — the trust gap.** Teams do not need a smarter model; they need a
bounded, inspectable way to let a model act. Radius encodes the boundary in the
repository (`autonomy.yaml`) and enforces it in CI, so trust is produced by
evidence instead of confidence.

## 2. The autonomy ceiling in current agent products

### GitHub Copilot cloud agent stops at a draft pull request

GitHub's own risk documentation states the agent:

- "cannot mark its pull requests as 'Ready for review' and cannot approve or
  merge a pull request";
- requires human review before merging;
- does not run Actions workflows until a human clicks **Approve and run
  workflows**.

Source: [GitHub Docs — Risks and mitigations for Copilot cloud agent](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/risks-and-mitigations)

This is a deliberate and sensible safety choice, but it means the *delivery*
half of the lifecycle still belongs to a human. The agent can write code; it
cannot be trusted to finish the job.

### GitLab's foundational flows stop at the merge request

GitLab's built-in flows cover code review, pipeline repair and vulnerability
resolution. They create or update merge requests and comments; they do not own a
post-merge deploy, an SLO check or a rollback. Source:
[Foundational flows](https://docs.gitlab.com/user/duo_agent_platform/flows/foundational_flows/).

### GitLab has no native scheduler and no bot-initiated triggers

- "All trigger event types require a human user to perform the triggering
  action. A non-human user such as a bot user, service account user, or another
  flow, cannot activate a trigger." The only exception is the documented
  **chain trigger**: a session's completion action can set a work item status,
  and that status change can start the next flow.
  ([Triggers](https://docs.gitlab.com/user/duo_agent_platform/triggers/))
- Time-based triggers do not exist. The workaround in the public issue is a CI
  scheduled pipeline that invokes the workflow with **a long-lived personal
  access token from a human user**, which the issue itself calls out as a
  security problem.
  ([gitlab-org/gitlab#590618](https://gitlab.com/gitlab-org/gitlab/-/work_items/590618))
- Custom agents cannot be used as trigger actions at all; only flows and
  external agents can.
  ([GitLab Support article](https://support.gitlab.com/hc/en-us/articles/27093601984540-Custom-Agent-Not-Appearing-in-Duo-Agent-Platform-Trigger-Configuration))

**Gap G4 — the orchestration gap.** A hands-off loop has to be built from the
few chainable events GitLab actually allows. Radius does that explicitly: one
human action (work item created), then chain triggers and pipeline events carry
the loop. No cron, no stored human PAT.

### External agents weaken the security boundary

GitLab documents that external agents do **not** get prompt-injection scanning,
have limited network isolation, and delegate security controls to the
third-party provider
([External agents — security considerations](https://docs.gitlab.com/user/duo_agent_platform/agents/external/)).
Radius uses native custom flows, so the policy and the evidence stay inside the
platform.

## 3. The post-merge blind spot

A green pipeline proves that tests passed, not that production is healthy. None
of the agent products above ship a general **deploy → observe → decide →
rollback** loop with a machine-readable budget:

- code agents stop at the PR/MR;
- CI systems execute whatever the pipeline says, including a bad deploy;
- observability tools detect incidents after they reach users.

**Gap G3 — the feedback gap.** Radius treats the canary as the unit of
autonomy: 25% of traffic, explicit error/latency/spend budgets, and an automatic
return to the last known-good revision when a budget is breached.

## 4. The governance gap

There is no portable, reviewable contract that says what an agent may do in
production. Policies live in dashboards, wiki pages or a human's head. GitLab
custom flows themselves require **Maintainer or Owner** to create and enable
([Custom flows](https://docs.gitlab.com/user/duo_agent_platform/flows/custom/)),
which shows how coarse the current permission model is: it is all-or-nothing at
the project role level.

**Gap G5 — the accountability gap.** Radius makes the contract a file in the
repo, versioned with the code, checked by `policy/check.py` in CI (hard gate)
and read by the agents (soft gate), with a JSON evidence pack per run.

## 5. Gap → feature → verification

| Gap | Evidence | Radius feature | How it is verified |
| --- | --- | --- | --- |
| G1 trust | 30% low/no trust; 46% distrust accuracy | `autonomy.yaml` budgets; policy engine exits 2 on breach | `policy/tests/test_policy.py`; `verify:policy` CI job |
| G2 autonomy ceiling | Copilot cannot merge; foundational flows stop at MR | Release Captain merges only when policy allows | flow source + `verify:policy`; live flow run (runbook) |
| G3 post-merge blind spot | CI green ≠ production healthy | canary + SLO evaluation + automatic rollback | `scripts/canary.py`; breach run: 19/30 errors, rollback verified |
| G4 orchestration | no cron; bots cannot trigger | one human action; chain trigger on work item status; MR marked ready; pipeline events | `docs/STAGES.md`, trigger config in `docs/RUNBOOK.md` |
| G5 accountability | policies live outside the repo | versioned contract + `evidence/canary.json` + `evidence/REPORT.md` | `govern:report` CI job; evidence artifact |
| G6 security of external agents | no prompt scanning, limited isolation | native custom flows only | flow sources use no external agent |

## 6. What we measured ourselves (not a claim from a vendor)

| Check | Result | Where |
| --- | --- | --- |
| Unit + contract tests | **15 passed** | `pytest -q` |
| Policy: healthy deploy | allow, exit 0 | `policy/check.py` |
| Policy: 60% error rate | deny, exit 2, reason `error_budget` | `policy/check.py` |
| Policy: merge during freeze | deny, exit 2, reason `freeze_window` | `policy/check.py` |
| Canary breach | 19/30 requests failed (63.3%), policy denied promotion, rollback verified to `baseline-fd56add3`, live channel = `baseline` | `evidence/canary.json` |
| Canary healthy | 15 requests, policy allowed, candidate promoted | `evidence/canary-clean.json` |
| Nine-stage report | generated with a link per stage | `evidence/REPORT.md` |

The canary runs a real second process built from the wheel, drives real HTTP
traffic through the service, injects a deterministic fault, and checks the
revision and build channel reported by `/health` after rollback. It is not a
mocked boolean. The first pipeline in a fresh project has no previous package,
so it records a **seed run** (`outcome.seeded = true`) instead of faking a
rollback; every later pipeline rolls back to the previous published wheel.

## 7. Threats to validity (what a judge should discount)

- **Production is simulated on the CI runner.** The canary is a real process
  with real traffic, but it is not multi-node or behind a load balancer. The
  contract and the decision logic are production-shaped; the infrastructure is
  not.
- **The breach sample is 30 requests.** That is enough to cross a 2% error
  budget decisively, but it is not a statistical SLO measurement. A real
  deployment would use a longer window and a proper SLI.
- **The flows must be registered in the GitLab UI.** They are versioned here as
  source of truth because GitLab's config-path trigger is behind a disabled
  feature flag. Registration needs Maintainer/Owner; see the runbook.
- **Credits are finite.** Each agent session consumes GitLab Credits; the demo
  is designed to need two sessions, not a loop.
- **One service, one language.** Radius demonstrates the governance model; it
  is not a general-purpose deployment platform.

## 8. What we deliberately did not build

- **No Google Cloud deployment.** Path A does not require it. Skipping the +0.2
  bonus bought ~3 hours for the rollback proof and the video.
- **No cron or external scheduler.** That would paper over gap G4 instead of
  demonstrating the platform-native chain.
- **No external model provider.** Native flows keep prompt scanning and
  isolation inside GitLab.
- **No automatic promotion on a failed canary.** The whole point is that the
  budget wins over the agent's optimism.
