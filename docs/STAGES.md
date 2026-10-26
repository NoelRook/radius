# The nine stages, and exactly what proves each one

The hackathon says "touching the stage counts", but a claim without an artifact
is not evidence. Every row below maps to a job, a file, or a URL that exists in
this repository's pipeline.

| # | Stage | Human action | What the automation does | Evidence |
| --- | --- | --- | --- | --- |
| 1 | **plan** | Opens one issue from the "Ship a change" template | Triage flow reads the issue, writes acceptance criteria, sets status `Ready for dev` | Issue + flow session |
| 2 | **create** | Nothing | Developer flow opens the MR; built-in code review runs when marked ready | MR timeline |
| 3 | **verify** | Nothing | `verify:test`, `verify:policy`, `verify:lint` | Job logs + JUnit artifact |
| 4 | **package** | Nothing | Wheel + SBOM published as a generic package | Package registry |
| 5 | **secure** | Nothing | Secret scan, dependency audit, GitLab SAST | Security jobs |
| 6 | **release** | Nothing | `release:create` tags and publishes release notes | Releases page |
| 7 | **configure** | Nothing | `configure:render` derives runtime config from `autonomy.yaml` | `deploy/runtime.env` artifact |
| 8 | **monitor** | Nothing | Canary + fault injection + policy decision + rollback | `evidence/canary.json` |
| 9 | **govern** | Nothing | `govern:report` publishes the nine-stage evidence table | `evidence/REPORT.md` |

## Where the "hands-off" claim is tested

The loop is not allowed to depend on a human clicking "approve" between stages.
The only human act is opening the issue. Everything after that is triggered by
the flow or by the pipeline.

The one platform constraint we design around: GitLab triggers require a human
actor, and a flow cannot start another flow except through the documented chain
trigger (set work item status on finish). That is why the issue status is the
hand-off between plan and ship, and why the ship flow is attached to pipeline
events rather than trying to call another flow.

## Failure path

A red canary is not a broken demo. It is the product:

1. Candidate revision receives faulted traffic.
2. Error rate exceeds the contract's `error_rate_max`.
3. `policy/check.py promote` returns deny with the breached budget.
4. The harness stops the candidate and restarts the stable revision.
5. `/health` is checked again; its revision must equal the stable revision.
6. `evidence/canary.json` records the denial and the verified rollback.

If step 5 fails, the job fails. There is no green result without a real rollback.
