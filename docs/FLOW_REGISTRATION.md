# Flow registration and trigger wiring

The two custom flows are defined in `.gitlab/duo/flows/`. They are registered in the
GitLab UI because custom flow creation is a Maintainer/Owner action, not a repository
push.

## Preflight (verified in this project)

- [x] Protected `main` allows **Developers + Maintainers** to merge (service accounts).
- [x] Project has **Automate → Flows → New flow** (Owner access confirmed).
- [ ] Work item status **`Ready for dev`** exists.
- [ ] Both flows are enabled for the project.
- [ ] The three triggers below are active.

## 1. Register Radius Triage & Plan

1. Open **Automate → Flows → New flow**.
2. Name: `Radius Triage & Plan`.
3. Paste the entire contents of `.gitlab/duo/flows/radius_triage_plan.yaml`.
4. Create, then enable it for this project.

The flow is read-only except for one work-item note. Its completion action, configured
on the trigger, moves the work item forward. It must not call `update_work_item`.

## 2. Register Radius Release Captain

1. Open **Automate → Flows → New flow**.
2. Name: `Radius Release Captain`.
3. Paste the entire contents of `.gitlab/duo/flows/radius_release_captain.yaml`.
4. Create, then enable it for this project.

The flow may merge only after `policy/check.py` exits 0. On a canary breach the policy
exits 2, the agent escalates, and the pipeline restores the previous revision.

## 3. Enable the Developer Flow

Enable GitLab's **Developer Flow** for the project. It implements the issue, opens a
merge request and marks it ready.

## 4. Create the chain triggers

| # | Event | Action | Completion action |
|---|-------|--------|-------------------|
| 1 | Work item **Created** (Issue) | Radius Triage & Plan | Set work item status **Ready for dev** |
| 2 | Work item **Status changed** = **Ready for dev** | Developer Flow | Mark merge requests as ready |
| 3 | Merge request **Marked ready** | Radius Release Captain | None |

GitLab does not allow bots to activate triggers. The documented exception is the
completion action on a trigger: the status change from trigger 1 is what starts
trigger 2. This is the only reason the loop can run Hands-off.

## 5. Capture service account names

After enabling each flow, open **Automate → Triggers** and note the generated service
account, for example `ai-radius-triage-plan-noelrook-group`. Record them in the
submission evidence. If a service account is not a project member, add it as
**Developer**.

## 6. Smoke test

Create an issue from the `Ship` template with:

```
Title: Add request ID to /quote response
Intent: Return an X-Request-ID header and include it in the JSON body.
Acceptance: existing tests pass; a new test asserts the header is present.
Risk class: low. No migrations, auth, payments or secrets.
Rollback: redeploy the previous revision; canary rollback is automatic.
```

Expected sequence with no further human action:

1. Triage posts `## Radius plan` and the work item moves to `Ready for dev`.
2. Developer Flow opens an MR and marks it ready.
3. Release Captain checks policy, merges, waits for the pipeline, reads the canary
   evidence, and posts `## Radius release gate`.
4. The canary injects a fault, the error budget is breached, and the pipeline restores
   the previous revision. The issue stays open with `Decision: ROLLED BACK`.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `prompts.0.placeholder: Extra inputs are not permitted` | Old YAML | Use commit `fd56add` or later; the linter rejects unknown prompt keys |
| `name/description/product_group` not permitted | Top-level metadata | Removed; the UI supplies the name |
| `tool not found` | Tool not in ambient registry | Run `python scripts/lint_flows.py --require-files`; it checks the allowlist |
| `environment must be ambient` | Wrong execution target | Keep `environment: ambient` |
| Trigger cannot select the flow | Flow not enabled | Enable it in the project, then reload Automate → Triggers |
| Status `Ready for dev` missing | Custom status not created | Settings → Work items → Statuses → add it |
| Service account cannot merge | Protected branch | Allow Developers to merge on `main` (already configured) |
