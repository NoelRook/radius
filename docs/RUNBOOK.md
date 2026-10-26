# Runbook: register Radius on GitLab Duo Agent Platform

This is the only manual setup. Everything after it is the autonomous loop.
Estimated time: **20–30 minutes**, most of it waiting for the first pipeline.

## 0. Preflight (do this first — it is the project's biggest risk)

1. Open the project in GitLab: **Automate → Flows → New flow**.
   - If the button exists and the YAML editor opens, you have the required
     role. Continue.
   - If it is missing or disabled, you are **Developer** on the group and the
     platform requires **Maintainer/Owner** to create a custom flow. Stop and
     ask the hackathon organisers to grant Maintainer on
     `gitlab-ai-hackathon/transcend-october-2026/43225718` (or to create the two
     flows for you). Do not spend demo time fighting the permission model.
2. Check **Settings → Repository → Protected branches**:
   - If `main` is protected and only Maintainers may merge, add the two flow
     service accounts to **Allowed to merge** and **Allowed to push**, or
     unprotect `main` for the demo project. The agents act as service accounts
     with the Developer role; without this, auto-merge is blocked.
3. Check **Settings → CI/CD → Token Access** and the package registry are
   enabled (defaults on gitlab.com).
4. Check the GitLab Credits dashboard. You need roughly **4–8 credits** for the
   full demo (two flow sessions plus CI). Do not run loops while testing.

## 1. Register the two custom flows

For each file in `.gitlab/duo/flows/`:

1. **Automate → Flows → New flow**.
2. Name: `Radius Triage & Plan` / `Radius Release Captain`.
3. Description: one line from the file header.
4. Paste the entire YAML into the editor.
5. **Create flow**, then **Enable** it for this project.
6. Open the flow and copy the **service account** name
   (`ai-<flow-name>-<group>`); you will see it in the trigger picker.

The repository YAML is the source of truth; CI lints it with
`scripts/lint_flows.py` on every pipeline.

## 2. Enable the Developer Flow

1. **Automate → Flows** → find the foundational **Developer Flow**.
2. Enable it for the project.
3. Confirm it can create branches, commits and merge requests (default tools).

The Developer Flow is the only component that writes application code. Radius
does not reimplement coding; it governs what happens after the code exists.

## 3. Create the three triggers

Open **Automate → Triggers → New trigger** for each row.

| # | Trigger name | Event | Flow | Completion action |
| --- | --- | --- | --- | --- |
| 1 | `radius-triage` | Work item → **Created** (type: Issue) | Radius Triage & Plan | **Set work item status → Ready for dev** |
| 2 | `radius-develop` | Work item → **Status changed** → `Ready for dev` | Developer Flow | **Mark merge requests as ready** |
| 3 | `radius-release` | Merge request → **Marked ready** | Radius Release Captain | None |

Why this shape: GitLab does not allow cron triggers, and a bot cannot start a
trigger by mentioning a service account. The documented exception is a
**chain trigger**: the completion action of one session changes a work item
status, and that status change starts the next flow. Triggers 1→2→3 are that
chain. The only human action is creating the work item.

If the trigger UI does not offer "Set work item status" or "Mark merge requests
as ready", the platform version is older than 18.8. Stop and check
**Help → About**; the project needs the chain-trigger behaviour.

## 4. First run: seed the package registry

1. Create an issue with the **Radius ship** template.
2. Watch the issue: the triage flow posts `## Radius plan` with the real budgets
   and `Decision: PROCEED`.
3. The Developer Flow opens an MR and marks it ready.
4. The Release Captain runs `policy/check.py`, merges with auto-merge, and waits
   for the default-branch pipeline.
5. The pipeline runs all nine stages. Because there is no previous package yet,
   `monitor:canary` records `outcome.seeded = true` and does **not** claim a
   rollback. This is intentional and visible in the evidence.
6. The Release Captain comments `Decision: PROMOTED` only if the policy allowed
   the healthy canary; on the first run it should report the seed outcome
   instead. If it cannot find evidence, it says so.

## 5. Second run: the real rollback

Create a second issue (or push a trivial commit to `main`). Now the previous
package exists, so `monitor:canary`:

1. downloads the previous wheel as **stable**;
2. installs the new wheel as **candidate**;
3. sends 10 baseline requests, injects a 60% error fault, sends 30 requests;
4. gets `deny` from `policy/check.py` (`error_budget`);
5. stops the candidate, restarts the stable wheel on the live port;
6. verifies `/health` reports the stable **revision and channel**;
7. uploads `evidence/canary.json` and `evidence/REPORT.md`.

The Release Captain reads the evidence and comments
`Decision: ROLLED BACK` with the live revision. No human touched the merge
button.

## 6. Verify it worked

In the pipeline:

- `verify:test` → 15 passed, coverage report.
- `verify:policy` → allow, deny (error budget), deny (freeze).
- `secure:secrets`, `secure:deps`, `secure:sast` → visible security stage.
- `package:wheel` → wheel + SBOM in the package registry.
- `release:create` → a GitLab Release on `main`.
- `configure:render` → `deploy/runtime.json`.
- `monitor:canary` → artifacts `evidence/canary.json`, `canary.md`.
- `govern:report` → `evidence/REPORT.md` with all nine stages.

Useful checks:

```bash
curl -s "https://gitlab.com/api/v4/projects/87459456/pipelines?ref=main&per_page=1"
curl -s "https://gitlab.com/api/v4/projects/87459456/packages?package_type=generic"
```

The project is public, so these work without a token.

## 7. Failure playbook

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| No "New flow" button | Developer role, flow creation needs Maintainer/Owner | Ask organisers for Maintainer; do not fake the flow |
| Flow created but not selectable in a trigger | Flow not enabled for the project | Project → Automate → Flows → Enable |
| Trigger never fires | Bot/service account tried to start it; only chain status changes are allowed | Use the completion action, not a mention from another flow |
| Release Captain cannot merge | `main` protected to Maintainers, or auto-merge disabled | Add the service account to allowed-to-merge, or unprotect `main` |
| `monitor:canary` exits 4 | No previous package and `--allow-seed` missing | Keep `--allow-seed`; the next run will have a baseline |
| `monitor:canary` exits 3 | Rollback health check failed | Treat as a real failure; inspect `evidence/canary.json` and the candidate log |
| Credits hit zero | Too many flow sessions | Stop; the demo needs two sessions, not a loop |
| `release:create` fails on tag | Tag protected or already exists | Change the tag pattern or delete the stale tag |

## 8. Demo recording plan (under 3 minutes)

| Time | Shot |
| --- | --- |
| 0:00–0:20 | Problem numbers on screen: 90% adoption, 30% low trust, 46% distrust accuracy; GitHub agent cannot merge |
| 0:20–0:35 | `autonomy.yaml` on screen; highlight error budget, canary 25%, freeze window |
| 0:35–0:55 | Create one issue from the Radius template; say "this is the only human action" |
| 0:55–1:20 | Triage plan comment appears; point at the quoted budgets and `PROCEED` |
| 1:20–1:40 | MR created and marked ready; Release Captain policy check and auto-merge |
| 1:40–2:20 | Pipeline: red canary, `error_budget` denial, rollback, `evidence/canary.json` showing `baseline-v0` live |
| 2:20–2:40 | Healthy manual job promotes the next revision (or show the clean evidence file) |
| 2:40–3:00 | `evidence/REPORT.md` nine-stage table; closing line |

Record at 1080p, no copyrighted music, no third-party trademarks. Show real
timestamps; do not speed up the rollback beyond a 2× cut with a caption.
