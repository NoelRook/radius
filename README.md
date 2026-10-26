# Radius — autonomy with a blast-radius budget

GitLab Transcend Hackathon submission (Path A — Start Fresh, Hands-off).

Agents may plan, review, test, secure, merge, deploy and roll back — but only
inside a machine-readable autonomy contract that caps blast radius (error
budget, spend, freeze windows, data class). When a budget would be breached the
agent stops and escalates with evidence instead of acting.

> Status: bootstrapping. Onboarding issue:
> https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43225718/showcase/-/work_items/1

## Planned structure

```
app/                 small demo service (health, quote, chaos endpoints)
autonomy.yaml        machine-readable blast-radius contract
policy/              policy check used by CI and injected into flow prompts
.gitlab-ci.yml       verify → package → secure → release pipeline
docs/                stage-evidence map and demo script
```

## Submission checklist

- [x] Public GitLab project
- [x] MIT license
- [ ] CI/CD pipeline showing automation
- [ ] End-to-end hands-off loop (issue → production → verify/rollback)
- [ ] Demo video (< 3 minutes, public YouTube)
- [ ] Devpost submission

## License

MIT — see [LICENSE](LICENSE).
