import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from policy.check import active_freeze, evaluate, load_contract, validate_contract  # noqa: E402

CONTRACT = load_contract(ROOT / "autonomy.yaml")
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
FREEZE_NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def test_contract_is_valid():
    assert validate_contract(CONTRACT) == []


def test_deploy_allowed_when_budgets_hold():
    decision = evaluate(CONTRACT, action="deploy", now=NOW, error_rate=0.0, change_lines=20)
    assert decision.allowed
    assert decision.reasons == []


def test_promote_denied_on_error_budget_breach():
    decision = evaluate(CONTRACT, action="promote", now=NOW, error_rate=0.6)
    assert not decision.allowed
    assert decision.escalate
    assert any("error_budget" in reason for reason in decision.reasons)


def test_freeze_window_blocks_merge_but_not_rollback():
    blocked = evaluate(CONTRACT, action="merge", now=FREEZE_NOW)
    assert not blocked.allowed
    assert any("freeze_window" in reason for reason in blocked.reasons)

    rollback = evaluate(CONTRACT, action="rollback", now=FREEZE_NOW)
    assert rollback.allowed


def test_spend_and_change_size_are_enforced():
    assert not evaluate(CONTRACT, action="deploy", now=NOW, spend_usd=9.0).allowed
    assert not evaluate(CONTRACT, action="merge", now=NOW, change_lines=900).allowed


def test_unknown_action_is_denied():
    decision = evaluate(CONTRACT, action="delete_database", now=NOW)
    assert not decision.allowed
    assert decision.escalate


def test_disallowed_data_class_is_denied():
    decision = evaluate(CONTRACT, action="deploy", now=NOW, data_class="restricted")
    assert not decision.allowed
    assert any("data_class" in reason for reason in decision.reasons)


def test_active_freeze_detects_window():
    window = active_freeze(CONTRACT["spec"], FREEZE_NOW)
    assert window is not None and window["name"] == "month-end-close"


def test_cli_exit_codes(tmp_path):
    from policy.check import main

    assert main(["--action", "deploy", "--now", NOW.isoformat()]) == 0
    assert main(["--action", "promote", "--now", NOW.isoformat(), "--error-rate", "0.9"]) == 2
    assert main(["--action", "deploy", "--contract", str(tmp_path / "missing.yaml")]) == 1


def test_contract_falls_back_to_json_without_pyyaml(monkeypatch):
    import policy.check as check_module

    monkeypatch.setattr(check_module, "yaml", None)
    contract = check_module.load_contract(ROOT / "autonomy.yaml")
    assert contract["kind"] == "AutonomyContract"
    assert contract["spec"]["budgets"]["error_rate_max"] > 0
