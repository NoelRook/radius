#!/bin/sh
# Run glab with the project-scoped merge credential injected by GitLab CI.
# The flow's built-in GITLAB_TOKEN is scoped to ai_workflows and cannot merge.
set -eu
if [ -z "${RADIUS_MERGE_TOKEN:-}" ]; then
  echo "RADIUS_MERGE_TOKEN_MISSING: add a masked project CI/CD variable named RADIUS_MERGE_TOKEN with api scope" >&2
  exit 78
fi
export GITLAB_HOST="${GITLAB_HOST:-gitlab.com}"
export GITLAB_TOKEN="$RADIUS_MERGE_TOKEN"
exec glab "$@"
