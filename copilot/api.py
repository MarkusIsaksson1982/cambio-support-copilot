"""FastAPI app (optional dependency). uvicorn copilot.api:app --reload"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from copilot.core import adapters, approval, pipeline
from copilot.core import plugin as registry
from copilot.core.audit import AuditLog

app = FastAPI(title="Support copilot (demo, synthetic data)")
AUDIT = AuditLog()
RESULTS: dict[str, dict] = {}
# The demo page and the offline eval pack both use adapter none.
# FakeAdapter invents a low-confidence label when rules abstain, so G-001 and
# G-008 would lose model_abstained. The CLI still selects an adapter itself.
ADAPTER = adapters.make("none")
UI_DIR = Path(__file__).resolve().parents[1] / "ui"
_NO_STORE = {"Cache-Control": "no-store"}


class Req(BaseModel):
    type: str = "support_ticket"
    text: str
    id: str | None = None


class Decision(BaseModel):
    reviewer: str
    decision: str
    note: str = ""
    edited_reply: str | None = None


@app.get("/request-types")
def types():
    registry.load_builtin()
    return registry.registered()


@app.post("/requests")
def submit(req: Req):
    registry.load_builtin()
    if req.type not in registry.registered():
        raise HTTPException(400, f"unknown request type; known: {registry.registered()}")
    res = pipeline.run(req.model_dump(), ADAPTER, AUDIT)
    RESULTS[res["request_id"]] = res
    return res


@app.post("/requests/{rid}/decision")
def decide(rid: str, d: Decision):
    if rid not in RESULTS:
        raise HTTPException(404, "unknown request")
    try:
        return approval.decide(RESULTS[rid], d.reviewer, d.decision, AUDIT, d.note, d.edited_reply)
    except (ValueError, PermissionError) as e:
        raise HTTPException(409, str(e))


@app.get("/audit/{rid}")
def audit(rid: str):
    return AUDIT.for_request(rid)


@app.get("/")
def home():
    return FileResponse(UI_DIR / "index.html", headers=_NO_STORE)


@app.get("/ui/examples.json")
def ui_examples():
    return FileResponse(UI_DIR / "examples.json", media_type="application/json", headers=_NO_STORE)


@app.get("/ui/eval.json")
def ui_eval():
    return FileResponse(UI_DIR / "eval.json", media_type="application/json", headers=_NO_STORE)
