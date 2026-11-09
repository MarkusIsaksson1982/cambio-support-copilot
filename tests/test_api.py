import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from copilot.api import app  # noqa: E402

c = TestClient(app)


def test_submit_decide_audit():
    assert "support_ticket" in c.get("/request-types").json()
    r = c.post("/requests", json={"text": "Kan inte logga in med SITHS-kortet"}).json()
    assert r["status"] == "awaiting_approval"
    d = c.post(f"/requests/{r['request_id']}/decision",
               json={"reviewer": "granskare-1", "decision": "approve"}).json()
    assert d["final_state"] == "sent"
    events = [e["event"] for e in c.get(f"/audit/{r['request_id']}").json()]
    assert events[0] == "received" and events[-1] == "human_decision"


def test_handoff_cannot_be_approved():
    r = c.post("/requests", json={"text": "Fel patient, pnr 19870312-4514"}).json()
    assert r["status"] == "handoff"
    assert c.post(f"/requests/{r['request_id']}/decision",
                  json={"reviewer": "g", "decision": "approve"}).status_code == 409


def test_unknown_type_400():
    assert c.post("/requests", json={"type": "nope", "text": "x"}).status_code == 400
