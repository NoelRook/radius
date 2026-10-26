"""Canary + rollback harness.

Starts the previous revision (stable) and the candidate side by side, drives
traffic, injects a deterministic fault, asks the policy engine whether promotion
is allowed, and either promotes or rolls back to the stable revision. Writes
machine-readable evidence that the pipeline publishes as an artifact.

This is intentionally real: two processes, two revisions, HTTP traffic, a fault,
and a verified post-rollback health check. No mocks in the demo path.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

REPO = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = REPO / "evidence" / "canary.json"
KEY = os.environ.get("CHAOS_KEY") or "canary-local-key"


def log(message: str) -> None:
    print(f"[canary] {message}", flush=True)


def now() -> str:
    return datetime.now(UTC).isoformat()


def install_wheel(wheel: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-deps", "--target", str(target), str(wheel)],
        check=True,
    )


def start_service(port: int, revision: str, app_dir: Path | None) -> subprocess.Popen:
    env = os.environ.copy()
    env["APP_REVISION"] = revision
    env["CHAOS_KEY"] = KEY
    env["PYTHONUNBUFFERED"] = "1"
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    cwd = app_dir or REPO
    if app_dir:
        env["PYTHONPATH"] = str(app_dir)
    return subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def stop(process: subprocess.Popen) -> str:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    output = ""
    if process.stdout:
        try:
            output = process.stdout.read() or ""
        except ValueError:
            output = ""
    return output.strip()


def wait_healthy(port: int, timeout: float = 40.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error = "no response"
    while time.time() < deadline:
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1.5)
            if response.ok:
                return response.json()
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.4)
    raise RuntimeError(f"service on port {port} did not become healthy: {last_error}")


def drive(port: int, count: int) -> tuple[int, int, list[str]]:
    failures = 0
    errors: list[str] = []
    for _ in range(count):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/work", timeout=3)
            if response.status_code >= 500:
                failures += 1
                errors.append(f"{response.status_code}: {response.text[:120]}")
        except requests.RequestException as exc:
            failures += 1
            errors.append(f"transport: {exc}")
    return count, failures, errors


def get_metrics(port: int) -> dict[str, Any]:
    try:
        return requests.get(f"http://127.0.0.1:{port}/metrics", timeout=3).json()
    except requests.RequestException:
        return {}


def set_chaos(port: int, mode: str, rate: float) -> None:
    response = requests.post(
        f"http://127.0.0.1:{port}/admin/chaos",
        json={"mode": mode, "rate": rate},
        headers={"X-Chaos-Key": KEY},
        timeout=3,
    )
    response.raise_for_status()


def evaluate_policy(error_rate: float, latency_p95_ms: float) -> tuple[int, dict[str, Any]]:
    command = [
        sys.executable,
        str(REPO / "policy" / "check.py"),
        "--action",
        "promote",
        "--error-rate",
        f"{error_rate:.4f}",
        "--latency-p95-ms",
        f"{latency_p95_ms:.1f}",
    ]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    try:
        decision = json.loads(result.stdout)
    except json.JSONDecodeError:
        decision = {"decision": "error", "stdout": result.stdout, "stderr": result.stderr}
    return result.returncode, decision


def fetch_stable_wheel(api_url: str, project_id: str, current_version: str, workdir: Path) -> tuple[Path | None, str | None]:
    packages_url = f"{api_url.rstrip('/')}/projects/{project_id}/packages"
    try:
        response = requests.get(
            packages_url,
            params={"package_type": "generic", "package_name": "radius", "per_page": 100},
            timeout=20,
        )
        if not response.ok:
            log(f"package list unavailable: {response.status_code}")
            return None, None
        packages = [p for p in response.json() if p.get("version") and p["version"] != current_version]
        packages.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        for package in packages:
            version = package["version"]
            wheel_url = (
                f"{api_url.rstrip('/')}/projects/{project_id}/packages/generic/radius/{version}/"
                f"radius-demo-{version}.whl"
            )
            wheel = requests.get(wheel_url, timeout=60)
            if wheel.ok and wheel.content:
                path = workdir / f"stable-{version}.whl"
                path.write_bytes(wheel.content)
                return path, version
    except requests.RequestException as exc:
        log(f"could not fetch stable package: {exc}")
    return None, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Radius canary and rollback loop")
    parser.add_argument("--scenario", choices=["breach", "clean"], default="breach")
    parser.add_argument("--candidate-wheel", type=Path, default=None)
    parser.add_argument("--stable-wheel", type=Path, default=None, help="Known-good wheel to roll back to")
    parser.add_argument("--stable-revision", default=None, help="Revision label for --stable-wheel")
    parser.add_argument(
        "--allow-seed",
        action="store_true",
        help="If no previous revision exists, record a seed run instead of faking a rollback",
    )
    parser.add_argument("--chaos-rate", type=float, default=None)
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--candidate-port", type=int, default=8000)
    parser.add_argument("--stable-port", type=int, default=8001)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--api-url", default=os.environ.get("CI_API_V4_URL", "https://gitlab.com/api/v4"))
    parser.add_argument("--project-id", default=os.environ.get("CI_PROJECT_ID", "87459456"))
    parser.add_argument("--candidate-revision", default=os.environ.get("CI_COMMIT_SHORT_SHA", "local-candidate"))
    args = parser.parse_args(argv)

    chaos_rate = args.chaos_rate if args.chaos_rate is not None else (0.6 if args.scenario == "breach" else 0.0)
    workdir = Path(tempfile.mkdtemp(prefix="radius-canary-"))
    candidate_process: subprocess.Popen | None = None
    stable_process: subprocess.Popen | None = None
    started_at = now()
    evidence: dict[str, Any] = {
        "service": "radius-demo",
        "scenario": args.scenario,
        "started_at": started_at,
        "pipeline": {
            "id": os.environ.get("CI_PIPELINE_ID"),
            "job_id": os.environ.get("CI_JOB_ID"),
            "job_url": os.environ.get("CI_JOB_URL"),
            "project_url": os.environ.get("CI_PROJECT_URL"),
            "commit": os.environ.get("CI_COMMIT_SHA"),
        },
        "candidate": {"revision": args.candidate_revision},
        "chaos": {"mode": "error" if chaos_rate > 0 else "off", "rate": chaos_rate},
    }

    try:
        if args.candidate_wheel:
            candidate_target = workdir / "candidate"
            install_wheel(args.candidate_wheel, candidate_target)
            app_dir: Path | None = candidate_target
            evidence["candidate"]["wheel"] = args.candidate_wheel.name
            evidence["candidate"]["sha256"] = __import__("hashlib").sha256(args.candidate_wheel.read_bytes()).hexdigest()
        else:
            app_dir = None
            evidence["candidate"]["wheel"] = "source-tree"

        stable_wheel = args.stable_wheel
        stable_version = args.stable_revision
        stable_source = "provided"
        if stable_wheel is None:
            stable_wheel, stable_version = fetch_stable_wheel(
                args.api_url, args.project_id, args.candidate_revision, workdir
            )
            stable_source = "package-registry"

        seeded = False
        stable_dir: Path | None = None
        stable_revision = "none"
        stable_health: dict[str, Any] = {}
        if stable_wheel:
            stable_target = workdir / "stable"
            install_wheel(stable_wheel, stable_target)
            stable_dir = stable_target
            stable_revision = stable_version or "unknown"
            evidence["stable"] = {
                "revision": stable_revision,
                "source": stable_source,
                "wheel": stable_wheel.name,
                "sha256": __import__("hashlib").sha256(stable_wheel.read_bytes()).hexdigest(),
            }
        elif args.allow_seed:
            seeded = True
            evidence["stable"] = {"revision": "none", "source": "seeded", "reason": "no previous revision yet"}
            log("no previous revision: recording a seed run (no rollback claim)")
        else:
            evidence["stable"] = {"revision": "none", "source": "missing"}
            evidence["error"] = "no previous revision available; refusing to fake a rollback (use --allow-seed or --stable-wheel)"
            evidence["finished_at"] = now()
            args.evidence.parent.mkdir(parents=True, exist_ok=True)
            args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            log(evidence["error"])
            return 4

        if not seeded:
            log(f"starting stable revision {stable_revision} on :{args.stable_port}")
            stable_process = start_service(args.stable_port, stable_revision, stable_dir)
            stable_health = wait_healthy(args.stable_port)

        log(f"starting candidate revision {args.candidate_revision} on :{args.candidate_port}")
        candidate_process = start_service(args.candidate_port, args.candidate_revision, app_dir)
        candidate_health = wait_healthy(args.candidate_port)

        log("baseline traffic (no chaos)")
        baseline_count, baseline_failures, _ = drive(args.candidate_port, 10)
        baseline_rate = baseline_failures / baseline_count if baseline_count else 0.0

        if chaos_rate > 0:
            log(f"injecting fault: error rate {chaos_rate}")
            set_chaos(args.candidate_port, "error", chaos_rate)

        log(f"canary traffic: {args.requests} requests")
        count, failures, errors = drive(args.candidate_port, args.requests)
        error_rate = failures / count if count else 1.0
        metrics = get_metrics(args.candidate_port)
        latency_p95 = float(metrics.get("latency_p95_ms", 0.0))

        exit_code, decision = evaluate_policy(error_rate, latency_p95)
        log(f"policy decision: {decision.get('decision')} (exit {exit_code})")
        for reason in decision.get("reasons", []):
            log(f"  - {reason}")

        evidence["candidate"].update(
            {
                "health": candidate_health,
                "baseline_error_rate": round(baseline_rate, 4),
                "canary_requests": count,
                "canary_failures": failures,
                "error_rate": round(error_rate, 4),
                "latency_p95_ms": latency_p95,
                "sample_errors": errors[:3],
            }
        )
        if stable_health:
            evidence["stable"]["health"] = stable_health
        evidence["policy"] = {
            "decision": decision.get("decision"),
            "exit_code": exit_code,
            "reasons": decision.get("reasons", []),
            "checks": decision.get("checks", []),
            "contract": decision.get("contract", {}),
        }

        expected_allow = args.scenario == "clean"
        actual_allow = decision.get("decision") == "allow"

        if seeded:
            evidence["outcome"] = {
                "seeded": True,
                "promoted": False,
                "rollback_verified": False,
                "live_revision": candidate_health.get("revision"),
                "live_health": candidate_health,
                "note": "First run seeds the package registry; the next pipeline has a real previous revision.",
            }
            return_code = 0
        elif actual_allow and not expected_allow:
            evidence["outcome"] = {"promoted": True, "rollback_verified": False, "unexpected": "policy allowed a faulted canary"}
            log("ERROR: policy allowed the faulted canary")
            return_code = 3
        elif not actual_allow and expected_allow:
            evidence["outcome"] = {"promoted": False, "rollback_verified": False, "unexpected": "policy denied a healthy canary"}
            log("ERROR: policy denied a healthy canary")
            return_code = 3
        elif actual_allow:
            log("promotion allowed; stopping the previous revision")
            stop(stable_process)
            stable_process = None
            live_health = wait_healthy(args.candidate_port)
            evidence["outcome"] = {
                "promoted": True,
                "rollback_verified": False,
                "live_revision": live_health.get("revision"),
                "live_health": live_health,
            }
            return_code = 0
        else:
            log("promotion denied; rolling back to the stable revision")
            candidate_log = stop(candidate_process)
            candidate_process = None
            stop(stable_process)
            stable_process = start_service(args.candidate_port, stable_revision, stable_dir)
            live_health = wait_healthy(args.candidate_port)
            stable_channel = evidence["stable"].get("health", {}).get("channel")
            rollback_verified = live_health.get("revision") == stable_revision and (
                stable_channel is None or live_health.get("channel") == stable_channel
            )
            evidence["outcome"] = {
                "promoted": False,
                "rollback_verified": rollback_verified,
                "live_revision": live_health.get("revision"),
                "live_channel": live_health.get("channel"),
                "live_health": live_health,
                "candidate_log_tail": candidate_log[-2000:],
            }
            return_code = 0 if rollback_verified else 3

        evidence["finished_at"] = now()
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        markdown = args.evidence.with_suffix(".md")
        markdown.write_text(render_markdown(evidence), encoding="utf-8")
        log(f"evidence written to {args.evidence}")
        print(json.dumps(evidence["outcome"], indent=2))
        return return_code
    except Exception as exc:  # noqa: BLE001 - evidence must capture any failure
        evidence["finished_at"] = now()
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        log(f"canary failed: {exc}")
        return 1
    finally:
        for process in (candidate_process, stable_process):
            if process is not None:
                stop(process)
        shutil.rmtree(workdir, ignore_errors=True)


def render_markdown(evidence: dict[str, Any]) -> str:
    candidate = evidence.get("candidate", {})
    stable = evidence.get("stable", {})
    policy = evidence.get("policy", {})
    outcome = evidence.get("outcome", {})
    lines = [
        "# Radius canary evidence",
        "",
        f"- Scenario: **{evidence.get('scenario')}**",
        f"- Candidate revision: `{candidate.get('revision')}`",
        f"- Stable revision: `{stable.get('revision')}` ({stable.get('source')})",
        f"- Canary error rate: **{candidate.get('error_rate')}**",
        f"- Policy decision: **{policy.get('decision')}**",
        f"- Rollback verified: **{outcome.get('rollback_verified')}**",
        f"- Promoted: **{outcome.get('promoted')}**",
        f"- Seeded (no previous revision): **{outcome.get('seeded', False)}**",
        "",
        "## Policy reasons",
        "",
    ]
    reasons = policy.get("reasons") or ["all checks passed"]
    lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(["", "## Checks", "", "| Check | Passed | Detail |", "| --- | --- | --- |"])
    for check in policy.get("checks", []):
        lines.append(f"| {check.get('name')} | {check.get('passed')} | {check.get('detail')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
