# Radius demo script (target 2:50)

Record at 1440p or 1080p, browser zoom 110%, no copyrighted music. One continuous story:
a human creates an issue, then never touches the keyboard again.

## 0:00–0:20 — Hook
**Screen:** README top, then `autonomy.yaml`.

**Voice:** "Every engineering leader wants agents that ship. Almost none will let them.
Not because the models can't write code — because nobody can bound what happens after
the merge. Radius is the control plane that makes autonomy safe enough to say yes to."

## 0:20–0:45 — The only human action
**Screen:** New issue from `Ship` template. Title: "Add request ID to /quote response".
Create.

**Voice:** "One human action: an issue. Radius Triage reads the contract, states the
budget, the blast radius and the rollback path, then moves the work forward."

Show the `## Radius plan` note ending `Human actions required: 0`.

## 0:45–1:15 — Agent creates the change
**Screen:** Automate → Sessions, then the merge request and its pipeline.

**Voice:** "GitLab Duo's Developer Flow implements it, opens a merge request and marks
it ready. The release captain runs the deterministic policy — not a prompt — before it
is allowed to merge."

Show `python policy/check.py` output: `Decision: ALLOW`.

## 1:15–1:45 — The gate
**Screen:** Merge request note `## Radius release gate`, then pipeline graph at `monitor`.

**Voice:** "The pipeline canaries the new revision at 25 percent. Radius injects a
controlled fault — 60 percent of requests fail. The error budget is two percent."

Show job log lines: `error_rate=0.633`, `policy decision=deny`, `rollback_verified=true`.

## 1:45–2:15 — Proof, not a claim
**Screen:** `evidence/REPORT.md`, then `evidence/canary.json`, then job artifacts.

**Voice:** "Radius does not just stop. It restores the previous revision and proves it:
revision and build channel match the baseline. The evidence pack is a build artifact,
linked from the nine-stage report."

## 2:15–2:40 — Why this wins
**Screen:** `docs/EVIDENCE.md` gaps table, then `docs/STAGES.md` nine rows.

**Voice:** "DORA found ninety percent of teams use AI, but thirty percent trust it
little or not at all. GitHub's agent cannot merge. GitLab's triggers need a human.
Radius closes that gap with a machine-readable contract, deterministic policy and a
verified rollback — across all nine lifecycle stages."

## 2:40–2:50 — Close
**Screen:** README tagline.

**Voice:** "Autonomy is not a leap of faith. It's a budget. Radius."

## Recording checklist
- [ ] Two full rehearsals; second one recorded
- [ ] Terminal font ≥ 16pt, no tokens or email visible
- [ ] Close Slack, notifications, and unrelated tabs
- [ ] Show the real pipeline ID and a real artifact download
- [ ] Video length < 3:00, public on YouTube
- [ ] No third-party trademarks or music

## Fallback if the live flow chain is unavailable
Record the same story with a real commit pushed to `main`, then show the pipeline
canary and rollback. State clearly that the issue-to-MR step is demonstrated from a
recorded flow session. Never claim a live action that did not happen.
