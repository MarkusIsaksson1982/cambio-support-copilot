"""Incident plugin: harm words, one extraction, always a human handoff."""
import json
from datetime import date

from copilot.chain import incident_from_envelope, validate_incident
from copilot.core.adapters import FakeAdapter, NoneAdapter
from copilot.core.pipeline import run

TODAY = date(2026, 11, 4)
VALID = json.dumps({
    "what": "Anteckning hamnade på fel patient",
    "when": "i morse",
    "where": "Demoklinik Norr",
    "harm": "lindrig",
    "immediate_action": "Utdelning stoppad",
    "confidence": 0.9,
})


def _run(text, adapter):
    return run({"type": "incident_report", "id": "inc-1", "text": text},
               adapter=adapter, today=TODAY)


def test_harm_words_and_not_tillfalle():
    hit = _run("Fel patient fick fel dos efter ett fall", FakeAdapter(reply=VALID))
    assert [h["phrase"] for h in hit["rule"]["hits"]] == ["fel patient", "fel dos", "fall"]
    assert hit["route"] == "patientsakerhet"
    miss = _run("Vi saknar en funktion för två vårdtillfällen", FakeAdapter(reply=VALID))
    assert miss["rule"]["hits"] == []


def test_valid_extraction_is_a_draft_and_still_hands_off():
    result = _run("Fel patient fick anteckningen", FakeAdapter(reply=VALID))
    assert result["status"] == "handoff"
    assert "incident_always_human" in result["handoff_reasons"]
    assert "not_implemented" not in result["handoff_reasons"]
    assert "model_output_invalid" not in result["handoff_reasons"]
    assert "low_confidence" not in result["handoff_reasons"]
    assert result["model"]["status"] == "ok"
    assert result["output"]["status"] == "draft"
    assert result["output"]["what"] == "Anteckning hamnade på fel patient"
    assert result["output"]["harm"] == "lindrig"
    assert validate_incident(result["output"]) == []


def test_invalid_json_fails_closed_but_report_still_validates():
    result = _run("Fel patient fick anteckningen", FakeAdapter(reply="inte json"))
    assert result["status"] == "handoff"
    assert "model_output_invalid" in result["handoff_reasons"]
    assert "incident_always_human" in result["handoff_reasons"]
    assert validate_incident(result["output"]) == []
    assert result["output"]["status"] == "draft"
    assert result["output"]["harm"] == "okand"


def test_none_adapter_chain_keeps_patient_flag_and_valid_report():
    env = run({"type": "support_ticket", "id": "T1",
               "text": "Fel patient fick anteckningen, pnr 19870312-4514"}, today=TODAY)
    out = incident_from_envelope(env, adapter=NoneAdapter())
    assert out["status"] == "handoff"
    assert "upstream_patient_data" in out["handoff_reasons"]
    assert "incident_always_human" in out["handoff_reasons"]
    assert out["report_errors"] == []
    assert out["report"]["status"] == "draft"
    assert "4514" not in str(out)
