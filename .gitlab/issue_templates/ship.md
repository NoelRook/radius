## Intent

<!-- One paragraph. What should exist after this work item is done, and for whom? -->

## Acceptance criteria

- [ ] 
- [ ] 
- [ ] 

## Risk class

<!-- low = docs/UI copy · medium = application code behind a flag · high = data, auth, payments or production config -->

Risk: **low**

## Blast radius

<!-- What can this change reach? Keep it inside autonomy.yaml: canary only, no schema migrations, no new data classes. -->

- Environment: production
- Blast radius: canary (the contract declares a 25% ceiling; the harness runs a separate candidate process)
- Data classes touched: public, internal

## Rollback

<!-- The exact action that returns production to the previous revision. Radius executes this automatically when a budget is breached. -->

`policy/check.py --action rollback` restarts the previous built revision and verifies `/health` reports it.

## Autonomy

This work item is handled under [`autonomy.yaml`](../autonomy.yaml). The agent may plan, open an MR, run CI, merge, deploy a canary, verify SLOs and roll back. It may **not** promote when an error, latency, spend or freeze budget is breached; it escalates on the work item instead.

Do not use a `Closes #` keyword in the merge request description. The agent may roll the change back; the work item should stay open until promotion.

## Evidence

The pipeline attaches `evidence/canary.json`, `evidence/canary.md` and `evidence/REPORT.md`, including the policy decision and the revision that is live after the run.
