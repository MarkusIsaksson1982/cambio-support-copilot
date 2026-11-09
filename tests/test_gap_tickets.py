"""Thu 5 Nov gap tickets (synthetic). Safety invariant: needs_human => handoff.
Label/route accuracy beyond that is covered by Friday rules work."""
import json
import pytest
from copilot.core.adapters import NoneAdapter
from copilot.core.pipeline import run

TICKETS = [json.loads(l) for l in open("data/gap_tickets_2026-11-05.jsonl", encoding="utf-8") if l.strip()]


@pytest.mark.parametrize("t", [t for t in TICKETS if t["needs_human"]], ids=lambda t: t["id"])
def test_needs_human_goes_to_handoff(t):
    r = run({"type": "support_ticket", "text": t["text"]}, adapter=NoneAdapter())
    assert r["status"] == "handoff", r.get("handoff_reasons")


def test_hero_ticket_masks_test_pnr():
    hero = next(t for t in TICKETS if t["id"] == "G-001")
    r = run({"type": "support_ticket", "text": hero["text"]}, adapter=NoneAdapter())
    assert "19121212-1212" not in r["masked_text"]
    assert "patient_data_detected" in r["handoff_reasons"]


def test_g003_luhn_invalid_shape_still_hands_off():
    """Interview story: masker misses Luhn-invalid samordning; gate still hands off."""
    t = next(x for x in TICKETS if x["id"] == "G-003")
    r = run({"type": "support_ticket", "text": t["text"]}, adapter=NoneAdapter())
    assert "19850372-6614" in r["masked_text"]  # not masked
    assert r["status"] == "handoff"
    assert "patient_data_detected" in r["handoff_reasons"]
