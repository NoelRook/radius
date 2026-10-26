"""Radius demo service.

A deliberately small service used to prove the autonomy loop: it exposes a
health endpoint, a unit of work, counters, and a guarded chaos endpoint so the
canary job can inject a real failure and watch the policy engine stop a bad
release.

The service is not the product. The product is the contract that decides how
far an agent may go.
"""

from __future__ import annotations

import os
import random
import time
from collections import deque
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_REVISION = os.getenv("APP_REVISION", "dev")
APP_CHANNEL = os.getenv("APP_CHANNEL", "candidate")
AUTONOMY_CONTRACT = os.getenv("AUTONOMY_CONTRACT", "autonomy.yaml")
CHAOS_KEY = os.getenv("CHAOS_KEY", "demo-chaos-key")
STARTED_AT = time.time()

QUOTES = [
    ("Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
    ("A distributed system is one in which the failure of a computer you did not even know existed can render your own computer unusable.", "Leslie Lamport"),
    ("Hope is not a strategy.", "Unknown SRE"),
    ("The most dangerous phrase in the language is: we've always done it this way.", "Grace Hopper"),
]

app = FastAPI(title="Radius demo service", version=APP_VERSION)

_state = {
    "requests": 0,
    "errors": 0,
    "chaos_mode": "off",
    "chaos_rate": 0.0,
    "chaos_latency_ms": 0,
    "latencies_ms": deque(maxlen=2000),
}


class ChaosRequest(BaseModel):
    mode: Literal["off", "error", "latency"] = "off"
    rate: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int = Field(default=0, ge=0, le=5000)


@app.middleware("http")
async def count_requests(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    _state["requests"] += 1
    _state["latencies_ms"].append(elapsed_ms)
    if response.status_code >= 500:
        _state["errors"] += 1
    response.headers["X-Radius-Revision"] = APP_REVISION
    return response


def _chaos_triggered() -> bool:
    if _state["chaos_mode"] == "off":
        return False
    if _state["chaos_rate"] >= 1.0:
        return True
    return random.random() < _state["chaos_rate"]


def _maybe_fail() -> None:
    """Apply the injected fault, if any. Called only by workload endpoints."""
    if _state["chaos_mode"] == "latency" and _chaos_triggered():
        time.sleep(_state["chaos_latency_ms"] / 1000)
    if _state["chaos_mode"] == "error" and _chaos_triggered():
        raise HTTPException(status_code=503, detail="injected fault: upstream unavailable")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "radius-demo",
        "version": APP_VERSION,
        "revision": APP_REVISION,
        "channel": APP_CHANNEL,
        "owner": "platform-team",
        "contract": AUTONOMY_CONTRACT,
        "uptime_s": round(time.time() - STARTED_AT, 3),
        "chaos_mode": _state["chaos_mode"],
    }


@app.get("/quote")
def quote():
    _maybe_fail()
    text, author = random.choice(QUOTES)
    return {"quote": text, "author": author, "revision": APP_REVISION}


@app.get("/work")
def work(units: int = 1):
    """The workload the canary drives. Fails only when chaos is injected."""
    _maybe_fail()
    total = sum(i * i for i in range(max(1, min(units, 1000))))
    return {"units": units, "checksum": total, "revision": APP_REVISION}


@app.get("/metrics")
def metrics():
    latencies = sorted(_state["latencies_ms"])
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0.0
    requests = _state["requests"]
    return {
        "service": "radius-demo",
        "revision": APP_REVISION,
        "requests": requests,
        "errors": _state["errors"],
        "error_rate": round(_state["errors"] / requests, 4) if requests else 0.0,
        "latency_p95_ms": round(p95, 2),
        "chaos_mode": _state["chaos_mode"],
        "chaos_rate": _state["chaos_rate"],
    }


@app.post("/admin/chaos")
def set_chaos(payload: ChaosRequest, x_chaos_key: str = Header(default="")):
    if x_chaos_key != CHAOS_KEY:
        raise HTTPException(status_code=403, detail="invalid chaos key")
    _state["chaos_mode"] = payload.mode
    _state["chaos_rate"] = payload.rate
    _state["chaos_latency_ms"] = payload.latency_ms
    return {"chaos_mode": payload.mode, "chaos_rate": payload.rate}


@app.post("/admin/reset")
def reset(x_chaos_key: str = Header(default="")):
    if x_chaos_key != CHAOS_KEY:
        raise HTTPException(status_code=403, detail="invalid chaos key")
    _state["requests"] = 0
    _state["errors"] = 0
    _state["latencies_ms"].clear()
    return {"reset": True}
