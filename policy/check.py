"""Radius policy engine.

The single source of truth for "how far may the agent go?". It is deliberately
small, deterministic and dependency-light so that both CI and an agent can call
the same binary and get the same answer.

Exit codes:
    0  allowed
    2  denied (a policy decision, not an error)
    1  invalid invocation or contract
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONTRACT = Path(__file__).resolve().parents[1] / "autonomy.yaml"
PROTECTED_ACTIONS = {"merge", "deploy", "promote"}


@dataclass
class Decision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    escalate: bool = False

    def check(self, name: str, passed: bool, detail: str, escalate: bool = False) -> None:
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            self.reasons.append(f"{name}: {detail}")
            if escalate:
                self.escalate = True
        if not passed:
            self.allowed = False


def load_contract(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)
    if not isinstance(contract, dict):
        raise ValueError("contract must be a YAML mapping")
    return contract


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spec = contract.get("spec")
    if not isinstance(spec, dict):
        return ["spec is missing"]
    budgets = spec.get("budgets")
    if not isinstance(budgets, dict):
        errors.append("spec.budgets is missing")
    else:
        for key in ("error_rate_max", "spend_usd_per_day_max", "change_lines_max"):
            if key not in budgets:
                errors.append(f"spec.budgets.{key} is missing")
    actions = spec.get("actions")
    if not isinstance(actions, dict) or not actions:
        errors.append("spec.actions is missing")
    if not isinstance(spec.get("freeze_windows", []), list):
        errors.append("spec.freeze_windows must be a list")
    return errors


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def active_freeze(spec: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    for window in spec.get("freeze_windows", []) or []:
        start = parse_time(str(window["start"]))
        end = parse_time(str(window["end"]))
        if start <= now <= end:
            return window
    return None


def evaluate(
    contract: dict[str, Any],
    *,
    action: str,
    now: datetime,
    error_rate: float | None = None,
    latency_p95_ms: float | None = None,
    spend_usd: float | None = None,
    change_lines: int | None = None,
    data_class: str | None = None,
) -> Decision:
    decision = Decision(allowed=True)

    contract_errors = validate_contract(contract)
    decision.check(
        "contract_valid",
        not contract_errors,
        "contract is valid" if not contract_errors else "; ".join(contract_errors),
    )
    if contract_errors:
        decision.escalate = True
        return decision

    spec = contract["spec"]
    budgets = spec["budgets"]
    actions = spec["actions"]

    configured = actions.get(action)
    decision.check(
        "action_known",
        isinstance(configured, dict),
        f"action '{action}' is defined in the contract",
    )
    if not isinstance(configured, dict):
        decision.escalate = True
        return decision

    decision.check(
        "action_allowed",
        bool(configured.get("allowed", False)),
        f"action '{action}' is {'allowed' if configured.get('allowed') else 'disabled'}",
        escalate=not configured.get("allowed", False),
    )

    expected = spec.get("service", {}).get("data_class")
    allowed_classes = spec.get("service", {}).get("allowed_data_classes", [])
    if data_class is not None:
        decision.check(
            "data_class",
            data_class in allowed_classes,
            f"data class '{data_class}' allowed={data_class in allowed_classes}",
            escalate=True,
        )
    else:
        decision.check("data_class", True, f"using service default '{expected}'")

    freeze = active_freeze(spec, now)
    if freeze and action in PROTECTED_ACTIONS:
        decision.check(
            "freeze_window",
            False,
            f"'{freeze.get('name')}' is active until {freeze.get('end')}",
            escalate=True,
        )
    else:
        decision.check(
            "freeze_window",
            True,
            "no freeze window active" if not freeze else f"freeze '{freeze.get('name')}' does not block '{action}'",
        )

    if error_rate is not None:
        limit = float(budgets["error_rate_max"])
        decision.check(
            "error_budget",
            error_rate <= limit,
            f"error_rate={error_rate:.3f} limit={limit:.3f}",
            escalate=True,
        )

    if latency_p95_ms is not None:
        limit = float(budgets["latency_p95_ms_max"])
        decision.check(
            "latency_budget",
            latency_p95_ms <= limit,
            f"latency_p95_ms={latency_p95_ms:.1f} limit={limit:.1f}",
            escalate=True,
        )

    if spend_usd is not None:
        limit = float(budgets["spend_usd_per_day_max"])
        decision.check(
            "spend_budget",
            spend_usd <= limit,
            f"spend_usd={spend_usd:.2f} limit={limit:.2f}",
            escalate=True,
        )

    if change_lines is not None:
        limit = int(budgets["change_lines_max"])
        decision.check(
            "change_size",
            change_lines <= limit,
            f"change_lines={change_lines} limit={limit}",
            escalate=True,
        )

    return decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the Radius autonomy contract")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--action", required=True)
    parser.add_argument("--now", default=None, help="ISO-8601 timestamp (default: now)")
    parser.add_argument("--error-rate", type=float, default=None)
    parser.add_argument("--latency-p95-ms", type=float, default=None)
    parser.add_argument("--spend-usd", type=float, default=None)
    parser.add_argument("--change-lines", type=int, default=None)
    parser.add_argument("--data-class", default=None)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        contract = load_contract(args.contract)
        now = parse_time(args.now) if args.now else datetime.now(UTC)
        decision = evaluate(
            contract,
            action=args.action,
            now=now,
            error_rate=args.error_rate,
            latency_p95_ms=args.latency_p95_ms,
            spend_usd=args.spend_usd,
            change_lines=args.change_lines,
            data_class=args.data_class,
        )
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"decision": "error", "reason": str(exc)}))
        return 1

    result = {
        "decision": "allow" if decision.allowed else "deny",
        "action": args.action,
        "evaluated_at": now.isoformat(),
        "contract": {
            "name": contract.get("metadata", {}).get("name"),
            "version": contract.get("metadata", {}).get("version"),
        },
        "escalate": decision.escalate,
        "reasons": decision.reasons,
        "checks": decision.checks,
    }
    if args.format == "text":
        print(f"{result['decision'].upper()}: {args.action}")
        for reason in decision.reasons or ["all checks passed"]:
            print(f"  - {reason}")
    else:
        print(json.dumps(result, indent=2))
    return 0 if decision.allowed else 2


if __name__ == "__main__":
    sys.exit(main())
