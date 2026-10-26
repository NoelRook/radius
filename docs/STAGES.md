# The nine stages, and exactly what proves each one

The hackathon says "touching the stage counts", but a claim without an artifact
is not evidence. Every row below maps to a job, a file, or a URL that exists in
this repository's pipeline.

| # | Stage | Human action | What the automation does | Evidence |
| --- | --- | --- | --- | --- |
| 1 | **plan** | Opens one issue from the "Ship a change" template | Triage flow reads the contract, posts the plan, commits the smallest change and opens the MR | [Issue #3](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/work_items/3), Triage session 10056015 |
| 2 | **create** | Nothing | Triage pushes `radius/auto-3` and opens MR !9 | [MR !9](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/merge_requests/9) |
| 3 | **verify** | Nothing | `verify:test`, `verify:policy`, `verify:lint` | Pipeline [2989901218](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/pipelines/2989901218) |
| 4 | **package** | Nothing | Wheel + SBOM published as a generic package | `package:wheel` job artifact |
| 5 | **secure** | Nothing | Secret scan, dependency audit, GitLab SAST | `secure:*` jobs |
| 6 | **release** | Nothing | `release:create` tags and publishes release notes | Releases page |
| 7 | **configure** | Nothing | `configure:render` derives runtime config from `autonomy.yaml` | `deploy/runtime.env` artifact |
| 8 | **monitor** | Nothing | Canary + fault injection + policy decision + rollback | `evidence/canary.json`, 16/30 failures, rollback to `baseline-d5274e72` |
| 9 | **govern** | Nothing | `govern:report` publishes the nine-stage evidence table | `evidence/REPORT.md` |

## Where the "hands-off" claim is tested

The loop is not allowed to depend on a human clicking "approve" between stages.
The only human act is opening the issue. The Triage flow creates the branch and
the MR itself; the MR-created trigger starts the Release Captain; the Release
Captain merges, waits for the pipeline, reads the canary evidence, and posts the
rollback.

Verified end-to-end on 26 Oct 2026:

```
issue #3 (human)
  -> Triage session 10056015: plan + commit 38fec275 + MR !9
  -> Release session 10056111: policy ALLOW, merge 1506fbc8
  -> pipeline 2989901218: 16/30 failures (53.3%)
  -> policy DENY: error_budget (limit 2%)
  -> rollback to baseline-d5274e72, channel baseline
  -> "Decision: ROLLED BACK / Human actions required: 0"
```

## Why the flow creates the MR instead of assigning the Developer Flow

GitLab triggers require a human actor, and an agent cannot start another agent
by assigning it. The documented exception is a status-change completion, but the
organiser-managed group does not expose a custom status lifecycle to a project
Developer. Radius therefore collapses plan and create into one custom flow and
uses the merge-request-created event as the hand-off. That keeps the critical
path at exactly one human action.

## A red canary is not a broken demo

It is the product:

1. `monitor:canary` starts the baseline wheel on port 8001 and the candidate
   wheel on port 8000.
2. It injects a fault into the candidate and drives 30 requests.
3. `policy/check.py --action promote` returns exit 2 because the error rate is
   above `budgets.error_rate_max`.
4. The harness stops the candidate, restarts the baseline, and checks both the
   revision and the build channel reported by `/health`.
5. `evidence/canary.json` records the denial and the verified rollback.
6. The Release Captain comments the gate with the live revision and the exact
   policy reason.
