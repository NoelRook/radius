# Radius demo script (target 2:50)

Record at 1080p, browser zoom 110%, no copyrighted music. Tell one continuous
story from the **verified run on 26 Oct 2026**. You do not need to wait for a new
pipeline: every screen below is a real artifact of issue #3.

## Exact URLs

- Repo: `https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase`
- Contract: `/-/blob/main/autonomy.yaml`
- Issue #3: `/-/work_items/3`
- Triage session: `/-/automate/agent-sessions/10056015`
- Merge request !9: `/-/merge_requests/9`
- Release session: `/-/automate/agent-sessions/10056111`
- Pipeline: `/-/pipelines/2989901218`
- Canary job: `/-/jobs/17470242282`
- Canary log: job page → **Log**
- Evidence artifact: job page → **Browse** → `evidence/REPORT.md`, `evidence/canary.json`
- Gap table: `/-/blob/main/docs/EVIDENCE.md`
- Stage table: `/-/blob/main/docs/STAGES.md`

## 0:00–0:18 — Hook

**Screen:** README top, then `autonomy.yaml` scrolled to `budgets`.

**Voice:** "Every engineering leader wants agents that ship. Almost none will let
them. Not because the models can't write code — because nobody can bound what
happens after the merge. Radius is the control plane that makes autonomy safe
enough to say yes to."

## 0:18–0:45 — The only human action

**Screen:** Issue #3, then scroll to the `## Radius plan` note. Highlight
`Human actions required: 0`, the 2% error budget and the freeze window.

**Voice:** "One human action: an issue. Triage reads the contract, quotes the
error budget, the latency limit and the rollback path, then writes the smallest
change and opens the merge request itself. There is no assignment, no status
change, no second click."

## 0:45–1:10 — Create, without a human

**Screen:** Triage session 10056015, then MR !9. Show branch `radius/auto-3`,
commit `38fec275`, and the diff.

**Voice:** "The flow commits to a branch and opens the merge request. The only
human event in this entire run was creating the issue. Everything after this is
an event the platform generated."

## 1:10–1:35 — The gate

**Screen:** Release Captain session 10056111, then the `## Radius release gate`
note on MR !9. Highlight `Policy — ALLOW` and the Git merge.

**Voice:** "The merge-request event starts the release captain. It runs the
deterministic policy — not a prompt — before it is allowed to merge. Policy says
allow, so it lands the change through the service account's Git credential."

## 1:35–2:05 — The gate closes

**Screen:** Pipeline 2989901218 graph, then canary job 17470242282 log lines:
`requests=30`, `failures=16`, `error_rate=0.533`, `policy decision=deny`,
`rollback_verified=true`.

**Voice:** "The pipeline canaries the new revision against the previous one.
Radius injects a controlled fault; sixteen of thirty requests fail. The contract
allows two percent. The policy denies promotion, stops the candidate, restarts
the baseline and checks that the live revision and build channel both match."

## 2:05–2:30 — Proof, not a claim

**Screen:** `evidence/REPORT.md`, then `evidence/canary.json` scrolled to
`"rollback_verified": true`, `"live_revision": "baseline-d5274e72"`,
`"live_channel": "baseline"`.

**Voice:** "This is the artifact a reviewer can audit: the policy checks, the
wheel hashes, the error rate, and the revision that is actually serving after the
rollback. The release gate ends with 'rolled back' and 'human actions required:
zero'."

## 2:30–2:50 — Why this wins

**Screen:** `docs/EVIDENCE.md` gaps table, then `docs/STAGES.md` nine rows, then
README tagline.

**Voice:** "DORA found ninety percent of teams use AI, but thirty percent trust it
little or not at all. GitHub's agent cannot merge. GitLab's triggers need a human.
Radius closes that gap with a machine-readable contract, deterministic policy and
a verified rollback, across all nine lifecycle stages. Autonomy is not a leap of
faith. It's a budget."

## Recording checklist

- [ ] Two full rehearsals; record the second
- [ ] Terminal and browser font at least 16pt; no tokens, emails or notifications
- [ ] Show the real issue, MR, session, pipeline and job IDs
- [ ] Show the artifact, not a slide about the artifact
- [ ] Video length under 3:00; public on YouTube
- [ ] No third-party trademarks or copyrighted music
- [ ] Description: repo URL, Path A Hands-off, one sentence on the run

## Fallback

If the UI is slow, record the same sequence from the job log and artifact pages,
then cut to the issue and release-gate notes. State clearly that the run is issue
#3 from 26 Oct 2026. Never claim a live action that did not happen.
