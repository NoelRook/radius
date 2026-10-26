# Flow registration and trigger wiring

The two custom flows are defined in `.gitlab/duo/flows/`. Register them in the
GitLab UI: flow creation is a Maintainer/Owner action, not a repository push.

## Preflight

- [x] Protected `main` allows **Developers + Maintainers** to push and merge.
- [x] **AI → Flows → New flow** is available on the showcase project.
- [x] Both custom flows are created and enabled.
- [x] Two triggers are active; the old Assign trigger is disabled.
- [x] Project CI/CD variables are **not** visible to ambient flows, so the
      Release Captain merges through the Git credential in its coding
      environment.

No custom work-item status is required. A project Developer cannot create a
status lifecycle in the organiser-managed group, so the chain uses the
merge-request event instead.

## 1. Register Radius Triage & Plan

1. Open **AI → Flows → New flow**.
2. Name: `Radius Triage & Plan`.
3. Paste the entire contents of `.gitlab/duo/flows/radius_triage_plan.yaml`.
4. Create, then enable it for this project.

The flow reads the work item and `autonomy.yaml`, decides `PROCEED` or
`ESCALATE`, commits the smallest change to `radius/auto-<iid>`, pushes the
branch, opens the MR, and posts one `## Radius plan` note. It never merges,
deploys, or closes the work item.

## 2. Register Radius Release Captain

1. Open **AI → Flows → New flow**.
2. Name: `Radius Release Captain`.
3. Paste the entire contents of `.gitlab/duo/flows/radius_release_captain.yaml`.
4. Create, then enable it for this project.

The flow may merge only after `policy/check.py` exits 0. It tries the API merge
first, then a Git merge and push, then `create_commit` as a last resort. On a
canary breach the policy exits 2, the pipeline restores the previous revision,
and the flow posts `## Radius release gate` with the evidence.

## 3. Create the triggers

Open **AI → Triggers → New flow trigger**. For every trigger:

1. Enter a description.
2. Under **Conditions**, select **Add condition → On an event**.
3. Choose the event and its **Run when** options, then **Add event**.
4. Select the flow's **Service account**.
5. Set **Configuration source** to **AI Catalog** and select the flow.
6. Select **Create flow trigger**.

| # | Description | Event | Run when | Type | Flow |
|---|-------------|-------|----------|------|------|
| 1 | `radius-plan-on-create` | Work item | Created | Issue | Radius Triage & Plan |
| 2 | `radius-ship-on-mr` | Merge request | Created | — | Radius Release Captain |

Disable any auto-created Developer or Assign triggers. With the Triage flow
creating the MR, there is no assignment step and no Developer Flow in the
critical path.

## 4. Capture service account names

After enabling each flow, open **AI → Triggers** and note the generated service
account:

- `ai-radius-triage-plan-gitlab-ai-hackathon`
- `ai-radius-release-captain-gitlab-ai-hackathon`

Both are project members with the Developer role. If one is missing, add it as
**Developer**; protected `main` already allows Developer pushes and merges.

## 5. Smoke test

Create an issue with:

```
Title: Expose service owner in health response

## Intent
Expose which team owns the service so on-call can route incidents.

## Acceptance criteria
- GET /health includes "owner": "platform-team".
- Existing health fields are unchanged.
- pytest passes.
```

Expected sequence with **no further human action**:

1. Triage posts `## Radius plan` and opens MR `radius/auto-<iid>`.
2. The MR-created trigger starts Release Captain.
3. Release Captain runs policy, merges through Git, waits for the pipeline,
   downloads `evidence/canary.json`, and posts `## Radius release gate`.
4. The canary injects a fault, the error budget is breached, and the pipeline
   restores the previous revision with `rollback_verified=true`.
5. The gate ends with `Human actions required: 0`.

Verified on 26 Oct 2026:

- Issue #3 → Triage session `10056015` → MR !9 (`38fec275`) → Release session
  `10056111` → merge `1506fbc8` → pipeline
  [2989901218](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/pipelines/2989901218)
  → canary 16/30 failures (53.3%) → policy deny → rollback to
  `baseline-d5274e72`.
- Gate note: `Decision: ROLLED BACK`, `Human actions required: 0`.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `prompts.0.placeholder: Extra inputs are not permitted` | Old YAML | Use the current `main`; the linter rejects unknown prompt keys |
| `name/description/product_group` not permitted | Top-level metadata | Removed; the UI supplies the name |
| `tool not found` | Tool not in ambient registry | Run `python scripts/lint_flows.py --require-files`; it checks the allowlist |
| `environment must be ambient` | Wrong execution target | Keep `environment: ambient` |
| Trigger cannot select the flow | Flow not enabled | Enable it in the project, then reload AI → Triggers |
| `RADIUS_MERGE_TOKEN_MISSING` | Ambient flows do not receive project CI/CD variables | The Release Captain falls back to Git push and `create_commit` |
| Merge API returns `403 insufficient_scope` | Flow token is scoped to `ai_workflows` | Git push works because the service account is a Developer on a branch that allows Developer pushes |
| `git push` rejected on main | Protected branch | Allow Developers to push/merge on `main`, or keep the API merge path with a token |
| Issue closes even after rollback | MR description contains `Closes #<iid>` | Use `Part of #<iid>` so the release outcome, not the merge, decides the issue state |
