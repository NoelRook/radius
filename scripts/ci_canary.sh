#!/usr/bin/env bash
# Run the canary loop in CI.
#
# The stable ("currently deployed") revision is reconstructed from the previous
# commit so the demo can prove a real rollback even when the package registry is
# empty or unavailable. Falls back to the registry lookup inside canary.py, and
# only seeds when no prior revision exists at all.
set -euo pipefail

SCENARIO="${1:-breach}"
REQUESTS="${2:-30}"
PYTHON="${PYTHON:-python}"
STABLE_ARGS=()

BASE_SHA="${CI_COMMIT_BEFORE_SHA:-}"
if [ -n "$BASE_SHA" ] && [ "$BASE_SHA" != "0000000000000000000000000000000000000000" ]; then
  rm -rf /tmp/radius-baseline /tmp/radius-baseline-dist /tmp/radius-baseline.tar.gz
  if "$PYTHON" - "$BASE_SHA" <<'PY'
import os
import sys
import urllib.request

sha = sys.argv[1]
url = (
    f"{os.environ['CI_API_V4_URL']}/projects/{os.environ['CI_PROJECT_ID']}"
    f"/repository/archive.tar.gz?sha={sha}"
)
request = urllib.request.Request(url, headers={"JOB-TOKEN": os.environ["CI_JOB_TOKEN"]})
with urllib.request.urlopen(request, timeout=120) as response:
    data = response.read()
with open("/tmp/radius-baseline.tar.gz", "wb") as handle:
    handle.write(data)
print(f"downloaded baseline archive for {sha[:8]} ({len(data)} bytes)")
PY
  then
    mkdir -p /tmp/radius-baseline
    if tar -xzf /tmp/radius-baseline.tar.gz -C /tmp/radius-baseline; then
      BASELINE_DIR="$(dirname "$(find /tmp/radius-baseline -maxdepth 2 -name pyproject.toml | head -1)")"
      if [ -n "$BASELINE_DIR" ] && [ -f "$BASELINE_DIR/pyproject.toml" ]; then
        if "$PYTHON" -m pip install --quiet build==1.2.2 \
          && (cd "$BASELINE_DIR" && "$PYTHON" -m build --wheel --outdir /tmp/radius-baseline-dist >/tmp/radius-baseline-build.log 2>&1); then
          WHEEL="$(ls /tmp/radius-baseline-dist/*.whl | head -1)"
          STABLE_ARGS=(--stable-wheel "$WHEEL" --stable-revision "baseline-${BASE_SHA:0:8}")
          echo "baseline artifact: $WHEEL (${BASE_SHA:0:8})"
        else
          echo "WARN: baseline build failed; falling back to the package registry"
          tail -20 /tmp/radius-baseline-build.log || true
        fi
      else
        echo "WARN: previous commit has no pyproject.toml; falling back to the package registry"
      fi
    else
      echo "WARN: could not extract baseline archive; falling back to the package registry"
    fi
  else
    echo "WARN: could not download baseline ${BASE_SHA}; falling back to the package registry"
  fi
fi

"$PYTHON" scripts/canary.py \
  --scenario "$SCENARIO" \
  --candidate-wheel "dist/radius_demo-0.1.0-py3-none-any.whl" \
  --requests "$REQUESTS" \
  "${STABLE_ARGS[@]}" \
  --allow-seed
