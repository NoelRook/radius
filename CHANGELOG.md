# Changelog

## Unreleased

- Bounded-autonomy contract (`autonomy.yaml`) and deterministic policy engine.
- Demo service with health, workload, metrics and guarded fault injection.
- Canary harness that runs two revisions, breaches the error budget, gets a
  policy denial, and proves a rollback with a post-rollback health check.
- Nine-stage CI pipeline with package, release, configure, monitor and govern
  evidence.

## Fixes after pipeline #2988296618

- Build the stable canary revision from the previous commit's source archive, so
  rollback evidence no longer depends on the package registry.
- Split wheel publishing into a non-blocking `package:publish` job; a registry
  outage can no longer stop the release loop.
- Upgrade FastAPI to 0.162.0 (Starlette 1.10.0) to clear seven known
  vulnerabilities reported by `pip-audit`.
