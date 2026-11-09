"""Demo page locks the four frozen tickets to adapter none."""
import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from copilot.api import ADAPTER, app  # noqa: E402
from copilot.core.adapters import FakeAdapter  # noqa: E402
from copilot.core.pipeline import run  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = json.loads((ROOT / "ui" / "examples.json").read_text(encoding="utf-8"))
EVAL = json.loads((ROOT / "ui" / "eval.json").read_text(encoding="utf-8"))
REPORT = (ROOT / "docs" / "EVAL-2026-11-08.md").read_text(encoding="utf-8")
client = TestClient(app)

FIGURES = (
    "39 of 44",
    "13 of 44",
    "100% of 8",
    "100% of 12",
    "A live model is not in these numbers.",
)


def _example(example_id):
    return next(item for item in EXAMPLES if item["id"] == example_id)


def test_page_uses_adapter_none_and_shows_the_offline_figures():
    assert ADAPTER.name == "none"
    page = client.get("/")
    assert page.status_code == 200
    html = page.text
    for needle in ("Godkänn", "Inspelat", "awaiting_approval", "patient_data_detected",
                   "ticket-001", "G-001", "G-008"):
        assert needle in html
    for figure in FIGURES:
        assert figure in html
        assert figure in REPORT
    served = client.get("/ui/examples.json")
    assert served.status_code == 200
    assert [item["id"] for item in served.json()] == [item["id"] for item in EXAMPLES]
    snapshot = client.get("/ui/eval.json").json()
    assert snapshot["adapter"] == "none" and snapshot["live_model"] is False
    assert snapshot == EVAL
    blob = json.dumps(snapshot)
    assert "39 of 44" in blob and "13 of 44" in blob


def test_live_envelopes_match_the_frozen_examples():
    for example in EXAMPLES:
        response = client.post("/requests", json={"type": "support_ticket", "text": example["text"]})
        assert response.status_code == 200
        body = response.json()
        frozen = example["frozen"]
        output = body["output"]
        assert body["status"] == frozen["status"]
        assert body["handoff_reasons"] == frozen["handoff_reasons"]
        assert body["masked_text"] == frozen["masked_text"]
        assert output["label"] == frozen["label"]
        assert output["reply_draft"] == frozen["reply_draft"]
        assert output["citations"] == frozen["citations"]
        assert output.get("suggest_request_type") == frozen["suggest_request_type"]
    hero = client.post("/requests", json={"text": _example("G-001")["text"]})
    assert "19121212-1212" not in hero.text
    assert "Astrid Holmgren" not in hero.json()["masked_text"]
    assert "[personnummer-maskat]" in hero.json()["masked_text"]
    assert "[namn-maskat]" in hero.json()["masked_text"]


def test_fake_adapter_would_drop_abstain_on_the_hero_ticket():
    result = run({"type": "support_ticket", "text": _example("G-001")["text"]}, FakeAdapter())
    assert "model_abstained" not in result["handoff_reasons"]
    assert "model_proposal_needs_review" in result["handoff_reasons"]
    assert result["status"] == "handoff"


def test_approve_siths_reject_bad_citation_and_block_patient_data():
    happy = client.post("/requests", json={"text": _example("ticket-001")["text"]}).json()
    assert happy["status"] == "awaiting_approval"
    approved = client.post(f"/requests/{happy['request_id']}/decision",
                           json={"reviewer": "granskare-1", "decision": "approve"})
    assert approved.status_code == 200
    assert approved.json()["final_state"] == "sent"

    mismatched = client.post("/requests", json={"text": _example("ticket-008")["text"]}).json()
    assert mismatched["output"]["citations"] == ["opencode-glm-5.3-flash-free:KB-002"]
    rejected = client.post(f"/requests/{mismatched['request_id']}/decision",
                           json={"reviewer": "granskare-1", "decision": "reject"})
    assert rejected.status_code == 200
    assert rejected.json()["final_state"] == "rejected"

    hero = client.post("/requests", json={"text": _example("G-001")["text"]}).json()
    denied = client.post(f"/requests/{hero['request_id']}/decision",
                         json={"reviewer": "granskare-1", "decision": "approve"})
    assert denied.status_code == 409
    missing_edit = client.post(f"/requests/{happy['request_id']}/decision",
                               json={"reviewer": "granskare-1", "decision": "edit"})
    assert missing_edit.status_code == 409
    missing_reviewer = client.post(f"/requests/{happy['request_id']}/decision",
                                   json={"reviewer": "  ", "decision": "reject"})
    assert missing_reviewer.status_code == 409
