"""Render the runtime configuration for the canary from the autonomy contract.

Configuration is derived from policy, not typed by hand, so the deploy cannot
silently exceed the blast radius the contract allows.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "deploy"


def main() -> int:
    contract = yaml.safe_load((ROOT / "autonomy.yaml").read_text(encoding="utf-8"))
    spec = contract["spec"]
    budgets = spec["budgets"]
    metadata = contract["metadata"]
    OUT_DIR.mkdir(exist_ok=True)
    rendered = {
        "SERVICE_NAME": spec["service"]["name"],
        "ENVIRONMENT": spec["service"]["environment"],
        "DATA_CLASS": spec["service"]["data_class"],
        "AUTONOMY_CONTRACT": f"{metadata['name']}@{metadata['version']}",
        "BLAST_RADIUS": budgets["blast_radius"],
        "CANARY_TRAFFIC_PERCENT": str(budgets["canary_traffic_percent"]),
        "ERROR_RATE_MAX": str(budgets["error_rate_max"]),
        "SPEND_USD_PER_DAY_MAX": str(budgets["spend_usd_per_day_max"]),
        "CHANGE_LINES_MAX": str(budgets["change_lines_max"]),
        "FREEZE_WINDOWS": ",".join(window["name"] for window in spec.get("freeze_windows", [])),
        "RENDERED_AT": datetime.now(timezone.utc).isoformat(),
        "RENDERED_FROM": os.environ.get("CI_COMMIT_SHA", "local"),
    }
    lines = [f"{key}={value}" for key, value in rendered.items()]
    (OUT_DIR / "runtime.env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "runtime.json").write_text(json.dumps(rendered, indent=2), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
