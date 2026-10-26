# Flow registration and trigger wiring

The two custom flows are defined in `.gitlab/duo/flows/`. Register them in the
GitLab UI: flow creation is a Maintainer/Owner action, not a repository push.

## Preflight

- [x] Protected `main` allows **Developers + Maintainers** to merge (service accounts).
- [x] **AI → Flows → New flow** is available on the showcase project.
- [x] Both custom flows are created.
- [x] **Developer Flow** is available as a foundational flow.
- [ ] Developer Flow is turned on for the project.
- [ ] The three triggers below are active.

No custom work item status is required. The hackathon group is managed by the
organizers, and a project Developer cannot create a status lifecycle. The chain
therefore uses the documented **Assign** event for Developer Flow.

## 1. Register Radius Triage & Plan

1. Open **AI → Flows → New flow**.
2. Name: `Radius Triage & Plan`.
3. Paste the entire contents of `.gitlab/duo/flows/radius_triage_plan.yaml`.
4. Create, then enable it for this project.

The flow is read-only except for one work-item note. It never merges, deploys,
edits the contract, or closes the work item.

## 2. Register Radius Release Captain

1. Open **AI → Flows → New flow**.
2. Name: `Radius Release Captain`.
3. Paste the entire contents of `.gitlab/duo/flows/radius_release_captain.yaml`.
4. Create, then enable it for this project.

The flow may merge only after `policy/check.py` exits 0. On a canary breach the
policy exits 2, the agent escalates, and the pipeline restores the previous
revision. It marks a draft MR ready before inspecting it.

## 3. Enable the Developer Flow

1. Open **AI → Flows**.
2. Find **Developer Flow** (foundational) and turn it on.
3. Copy its service account name; it is the `Duo Developer` identity used by the
   Assign trigger.

The Developer Flow supports **Mention** and **Assign** events. It does not start
from a Work item **Created** event.

## 4. Create the triggers

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
| 2 | `radius-develop-on-assign` | Assign | — | — | Developer Flow |
| 3 | `radius-ship-on-mr` | Merge request | Created | — | Radius Release Captain |

Trigger 1 has no completion action: completion settings are available only when
the condition is **Work item → Status changed** with a status. That is a platform
constraint, so the plan does not move the work item.

Trigger 2 is the documented Developer Flow start event. The issue is created with
the Developer Flow service account as assignee, so the assignment is part of the
single human action that creates the issue.

Trigger 3 runs as soon as the Developer Flow opens its draft MR. The Release
Captain marks the draft ready, then applies policy.

## 5. Capture service account names

After enabling each flow, open **AI → Triggers** and note the generated service
account, for example `ai-radius-triage-plan-<group>`. Record them in the
submission evidence. If a service account is not a project member, add it as
**Developer**.

## 6. Smoke test

Create an issue with:

```
Title: Add service name to health response

## Intent
Add a `service` field to the `/health` response with the value `radius-demo`.

## Acceptance criteria
- GET /health includes `"service": "radius-demo"`.
- No other response fields change.
- Existing tests pass.

## Risk
- Risk class: low
- Blast radius: canary at 25 percent
- Rollback: automatic, per autonomy.yaml
```

Assign the **Developer Flow service account** as assignee when creating the issue.

Expected sequence with no further human action:

1. Triage posts `## Radius plan`.
2. Developer Flow opens a draft MR.
3. The MR-created trigger starts Release Captain, which marks the MR ready,
   checks policy, merges, waits for the pipeline, reads the canary evidence, and
   posts `## Radius release gate`.
4. The canary injects a fault, the error budget is breached, and the pipeline
   restores the previous revision. The issue stays open with
   `Decision: ROLLED BACK`.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `prompts.0.placeholder: Extra inputs are not permitted` | Old YAML | Use commit `fd56add` or later; the linter rejects unknown prompt keys |
| `name/description/product_group` not permitted | Top-level metadata | Removed; the UI supplies the name |
| `tool not found` | Tool not in ambient registry | Run `python scripts/lint_flows.py --require-files`; it checks the allowlist |
| `environment must be ambient` | Wrong execution target | Keep `environment: ambient` |
| Trigger cannot select the flow | Flow not enabled | Enable it in the project, then reload AI → Triggers |
| Developer trigger rejects Work item Created | Documented limitation | Use the **Assign** event and assign the Developer service account |
| Service account cannot merge | Protected branch | Allow Developers to merge on `main` (already configured) |
