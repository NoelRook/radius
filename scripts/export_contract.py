#!/usr/bin/env python3
"""Export autonomy.yaml to autonomy.json for runtimes without PyYAML.

The Duo ambient flow runtime is Python 3.9 and does not ship PyYAML. The
policy engine prefers the YAML contract and falls back to this generated JSON
when the import is unavailable. CI runs --check so the two never drift.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "autonomy.yaml"
JSON_PATH = ROOT / "autonomy.json"


def render() -> str:
    with YAML_PATH.open("r", encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)
    if not isinstance(contract, dict):
        raise ValueError("autonomy.yaml must contain a mapping")
    return json.dumps(contract, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if autonomy.json is stale")
    args = parser.parse_args()
    rendered = render()
    current = JSON_PATH.read_text(encoding="utf-8") if JSON_PATH.exists() else ""
    if args.check:
        if current != rendered:
            print("autonomy.json is stale; run scripts/export_contract.py", file=sys.stderr)
            return 1
        print("autonomy.json matches autonomy.yaml")
        return 0
    JSON_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {JSON_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
