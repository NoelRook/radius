# Runbook: register Radius on GitLab Duo Agent Platform

This is the only manual setup. Everything after it is the autonomous loop.
Estimated time: **20–30 minutes**, most of it waiting for the first pipeline.

Verified on the public showcase project on 26 October 2026. The screenshots and
IDs in this runbook come from that project, not from a mock.

## 0. Preflight

1. Open the project: **AI → Flows** (direct URL `/-/ai/flows`).
   - GitLab 19 uses **AI → Flows**. The older docs and some screenshots say
     **Automate → Flows**; `/-/automate/flows` returns 404.
   - If the page loads and **New flow** is enabled, continue. Custom flows
     normally require Maintainer/Owner; the hackathon project allowed the
     Developer role to create them.
2. Check **Settings → Repository → Protected branches** for `main`:
   - **Allowed to push:** Developers + Maintainers.
   - **Allowed to merge:** Developers + Maintainers.
   - The flow service account is a Developer. Without Developer push/merge the
     release captain cannot land the change.
3. Check that **Settings → CI/CD → Token Access** and the package registry are
   enabled (defaults on GitLab.com).
4. Check the GitLab Credits dashboard. Two flow sessions plus one pipeline use
   roughly **4–8 credits**. Do not loop test runs.
5. Do not create a custom work-item status. It is not needed. The hackathon
   group did not expose the status settings, and the final design does not use a
   status chain.

## 1. Register the two custom flows

For each file in `.gitlab/duo/flows/`:

1. **AI → Flows → New flow**.
2. Name: `Radius Triage & Plan` / `Radius Release Captain`.
3. Paste the entire YAML into the editor.
4. **Create flow**, then **Enable** it for this project.
5. Open the flow and copy the **service account** name
   (`ai-<flow-name>-<group>`); it appears in the trigger target picker.

The repository YAML is the source of truth. The UI does **not** track the repo:
after changing a flow YAML, paste it into the existing flow and save. CI lints
the repository copy with `scripts/lint_flows.py` on every pipeline.

## 2. Create the two triggers

Open **Automate → Triggers → New trigger**. The current UI has **Target**,
**Conditions → New event**, then **Event** and **Run when**.

| # | Trigger name | Target | Event | Run when |
| --- | --- | --- | --- | --- |
| 1 | `radius-plan-on-create` | Radius Triage & Plan | Work item | Created |
| 2 | `radius-ship-on-mr` | Radius Release Captain | Merge request | Created |

Do **not** create a Developer Flow trigger, an Assign trigger, or a Mention
trigger. Earlier auto-created triggers caused duplicate work and were disabled.

Why this shape: GitLab has no cron trigger, and a bot cannot start a trigger by
mentioning a service account. Radius uses only the two human-originated events
it needs: the human creates the work item, and the Triage flow creates the merge
request. The merge-request creation is a normal event, so the chain continues
without a completion action.

## 3. What Triage does

The Triage flow:

1. Reads the work item and `autonomy.yaml`.
2. Edits `app/main.py` with the smallest change (for the demo, adds an `owner`
   field to `/health`).
3. Commits to `radius/auto-<iid>` and pushes.
4. Opens a merge request whose description explains the change and the rollback
   path.
5. Posts one `## Radius plan` note quoting the budgets and ending
   `Human actions required: 0`.

It never merges, never deploys, and never closes the work item.

## 4. What Release Captain does

The Release Captain:

1. Reads the MR IID from the trigger goal (a number, not a URL).
2. Computes `LINES` from the MR diff.
3. Runs `python policy/check.py --action merge --change-lines ...`; exit `2`
   posts `Decision: ESCALATE` and stops.
4. Merges in this order:
   - API merge, if a token with `api` scope is available (it is not in ambient
     flows);
   - **Git merge + `git push origin main`** using the flow service account's Git
     credential;
   - `create_commit` to `main` as the last resort.
5. Polls the default-branch pipeline, downloads `evidence/canary.json` from the
   `monitor:canary` job, and posts `## Radius release gate`.
6. Reports `Decision: PROMOTED` only if the canary passed; otherwise
   `Decision: ROLLED BACK` with the live revision and channel.

Ambient flows do **not** receive project CI/CD variables. Do not design around a
`RADIUS_MERGE_TOKEN` CI variable; it will be missing. The Git credential is the
supported path for this project because `main` allows Developer push.

## 5. Verified run (26 Oct 2026)

- Issue **#3** `Expose service owner in health response` created by the user.
- Triage session **10056015** created branch `radius/auto-3`, commit `38fec275`,
  and MR **!9**.
- Release session **10056111** started on `MR !9 created`, policy **ALLOW**,
  merged as `1506fbc8`.
- Main pipeline **2989901218** succeeded in 255s across all nine stages.
- Canary job **17470242282**: **16/30 failures (53.3%)**, p95 0.71ms, policy
  **DENY** `error_budget` (limit 0.02), **rollback_verified=true** to
  `baseline-d5274e72`, live channel `baseline`, promoted false.
- Release gate: `Decision: ROLLED BACK`, `Human actions required: 0`.
- Issue #3 auto-closed because the MR description contained `Closes #3`. That is
  cosmetic; a production template should omit the closing keyword when the agent
  may roll back.

## 6. Verify it worked

In the pipeline:

- `verify:test` → 16 passed, coverage report.
- `verify:policy` → allow, deny (error budget), deny (freeze).
- `verify:policy39` → the policy engine still works on the flow runtime's Python.
- `secure:secrets`, `secure:deps`, `secure:sast` → visible security stage.
- `package:wheel` → wheel + SBOM artifacts; `package:publish` mirrors the wheel.
- `release:create` → a GitLab Release on `main`.
- `configure:render` → `deploy/runtime.json`.
- `monitor:canary` → `evidence/canary.json`, `canary.md`.
- `govern:report` → `evidence/REPORT.md` with all nine stages.

Useful public checks:

```bash
curl -s "https://gitlab.com/api/v4/projects/87459456/pipelines?ref=main&per_page=1"
curl -s "https://gitlab.com/api/v4/projects/87459456/packages?package_type=generic"
```

## 7. Failure playbook

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| No flow page | Looking under Automate | Use **AI → Flows** or `/-/ai/flows` |
| New flow disabled | Role below Maintainer and no hackathon exception | Ask organisers; do not fake the flow |
| Paste rejected: `placeholder` | Old YAML had an unsupported prompt field | Use the current YAML; the linter rejects it |
| Flow not selectable in trigger | Flow not enabled for the project | AI → Flows → Enable |
| Duplicate MRs | Auto-created Mention/Assign triggers are active | Disable them; keep only the two in this runbook |
| `ImportError: cannot import name UTC` | Flow runtime is Python 3.9 | Code uses `datetime.timezone.utc`; do not regress |
| `ModuleNotFoundError: yaml` | Flow runtime has no PyYAML | `policy/check.py` falls back to `autonomy.json`; keep parity test |
| Merge 403 `insufficient_scope` | Flow API token is scoped to `ai_workflows` | Use the Git merge path; do not add a human PAT |
| Release Captain says no IID | Prompt expected a URL | Prompt accepts a numeric IID from the trigger goal |
| `monitor:canary` exits 4 | No previous revision and no `--allow-seed` | Keep `--allow-seed`; the next commit provides a baseline |
| `monitor:canary` exits 3 | Rollback health check failed | Treat as real; inspect `evidence/canary.json` |
| Credits hit zero | Too many flow sessions | Stop; the demo needs two sessions, not a loop |
| Issue closes on rollback | MR description used `Closes #` | Use `Part of #` or no closing keyword |

## 8. Demo recording

Use [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md). Record 1080p, no copyrighted music,
no third-party trademarks. Show the real timestamps and real job IDs. Do not
speed up the rollback beyond a labelled 2× cut.
