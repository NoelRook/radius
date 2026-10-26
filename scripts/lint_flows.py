#!/usr/bin/env python3
"""Lint the Radius Duo flow sources before they are registered in the UI.

Custom flows are versioned in this repository as the source of truth, then
pasted into GitLab's flow builder. This linter catches the schema mistakes
that would otherwise only surface at registration time:

* wrong version/environment
* restricted top-level or prompt fields
* dangling prompt ids, routers or entry point
* tool names that are not in the Agent Platform registry
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

FLOW_DIR = Path(".gitlab/duo/flows")
REQUIRED_FILES = ("radius_triage_plan.yaml", "radius_release_captain.yaml")
ALLOWED_TYPES = {"AgentComponent", "DeterministicStepComponent", "OneOffComponent"}

# Tools confirmed against the Agent Platform tool registry. Keep this list
# tight: an unknown name means the flow would fail at runtime.
KNOWN_TOOLS = {
    "blob_search",
    "create_branch",
    "create_commit",
    "create_file_with_contents",
    "create_issue_note",
    "create_merge_request",
    "create_work_item_note",
    "edit_file",
    "find_files",
    "get_issue",
    "get_logs_from_job",
    "get_pipeline_failing_jobs",
    "get_repository_file",
    "get_work_item",
    "get_work_item_notes",
    "get_work_item_statuses",
    "list_dir",
    "list_repository_tree",
    "read_file",
    "run_command",
    "update_issue",
    "update_merge_request",
    "update_work_item",
}

RESTRICTED_TOP_LEVEL = {"name", "description", "product_group"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def lint_flow(path: Path) -> list[str]:
    errors: list[str] = []
    data: Any = yaml.safe_load(path.read_text())

    if not isinstance(data, dict):
        return [f"{path}: not a YAML mapping"]

    for key in RESTRICTED_TOP_LEVEL:
        if key in data:
            fail(errors, f"{path}: restricted top-level field '{key}'")

    if data.get("version") != "v1":
        fail(errors, f"{path}: version must be 'v1', got {data.get('version')!r}")
    if data.get("environment") != "ambient":
        fail(errors, f"{path}: environment must be 'ambient', got {data.get('environment')!r}")
    coding = data.get("coding_environment")
    if coding is not None and coding not in {"full", "none"}:
        fail(errors, f"{path}: coding_environment must be 'full' or 'none', got {coding!r}")

    components = data.get("components")
    if not isinstance(components, list) or not components:
        return errors + [f"{path}: components must be a non-empty list"]

    prompt_ids = set()
    for prompt in data.get("prompts") or []:
        if not isinstance(prompt, dict) or "prompt_id" not in prompt:
            fail(errors, f"{path}: every local prompt needs a prompt_id")
            continue
        prompt_ids.add(prompt["prompt_id"])
        if "model" in prompt:
            fail(errors, f"{path}: prompt '{prompt['prompt_id']}' sets restricted field 'model'")
        params = prompt.get("params") or {}
        if "stop" in params:
            fail(errors, f"{path}: prompt '{prompt['prompt_id']}' sets restricted param 'stop'")
        template = prompt.get("prompt_template") or {}
        if not template.get("system") or not template.get("user"):
            fail(errors, f"{path}: prompt '{prompt['prompt_id']}' needs system and user text")

    component_names = set()
    for component in components:
        if not isinstance(component, dict):
            fail(errors, f"{path}: component entries must be mappings")
            continue
        name = component.get("name")
        if not name:
            fail(errors, f"{path}: component without a name")
            continue
        if ":" in name or "." in name:
            fail(errors, f"{path}: component name '{name}' may not contain ':' or '.'")
        component_names.add(name)

        ctype = component.get("type")
        if ctype not in ALLOWED_TYPES:
            fail(errors, f"{path}: component '{name}' has unknown type {ctype!r}")

        if ctype == "AgentComponent":
            prompt_id = component.get("prompt_id")
            if prompt_id not in prompt_ids:
                fail(errors, f"{path}: component '{name}' references unknown prompt_id {prompt_id!r}")
            tools = component.get("toolset") or []
            if not isinstance(tools, list):
                fail(errors, f"{path}: component '{name}' toolset must be a list")
                tools = []
            for tool in tools:
                if tool not in KNOWN_TOOLS:
                    fail(errors, f"{path}: component '{name}' uses unknown tool {tool!r}")

        for event in component.get("ui_log_events") or []:
            if not isinstance(event, str):
                fail(errors, f"{path}: component '{name}' has a non-string ui_log_event")

    entry = (data.get("flow") or {}).get("entry_point")
    if entry not in component_names:
        fail(errors, f"{path}: flow.entry_point {entry!r} is not a component")

    routers = data.get("routers")
    if not isinstance(routers, list) or not routers:
        fail(errors, f"{path}: routers must be a non-empty list")
    else:
        for router in routers:
            if not isinstance(router, dict):
                fail(errors, f"{path}: router entries must be mappings")
                continue
            src, dst = router.get("from"), router.get("to")
            if src not in component_names:
                fail(errors, f"{path}: router from unknown component {src!r}")
            if dst != "end" and dst not in component_names:
                fail(errors, f"{path}: router to unknown component {dst!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-files", action="store_true")
    args = parser.parse_args()

    if not FLOW_DIR.is_dir():
        print(f"ERROR: {FLOW_DIR} does not exist", file=sys.stderr)
        return 1

    if args.require_files:
        for name in REQUIRED_FILES:
            if not (FLOW_DIR / name).is_file():
                print(f"ERROR: missing flow source {FLOW_DIR / name}", file=sys.stderr)
                return 1

    flows = sorted(FLOW_DIR.glob("*.yaml"))
    if not flows:
        print(f"ERROR: no flow sources in {FLOW_DIR}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for path in flows:
        errors.extend(lint_flow(path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    for path in flows:
        data = yaml.safe_load(path.read_text())
        entry = data["flow"]["entry_point"]
        tools = sum(len(c.get("toolset") or []) for c in data["components"])
        print(f"OK {path.name}: entry={entry} components={len(data['components'])} tools={tools}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
