"""Chain contract (path b) + adversarial tickets from docs/REVIEW-grok.md."""
from datetime import date

import pytest

from copilot.chain import incident_from_envelope, validate_envelope
from copilot.core.masking import mask_text
from copilot.core.pipeline import run
from copilot.plugins.support_ticket.rules import classify

TODAY = date(2026, 11, 4)


def test_envelope_to_incident_chain_keeps_patient_data_flag():
    env = run({"type": "support_ticket", "id": "T1",
               "text": "Fel patient fick anteckningen, pnr 19870312-4514"}, today=TODAY)
    assert validate_envelope(env) == []
    assert env["output"]["suggest_request_type"] == "incident_report"
    out = incident_from_envelope(env)
    assert out["report_errors"] == []
    assert out["report"]["source_request_id"] == "T1"
    assert out["status"] == "handoff"
    assert "upstream_patient_data" in out["handoff_reasons"]
    assert "4514" not in str(out)


def test_invalid_envelope_rejected():
    with pytest.raises(ValueError):
        incident_from_envelope({"request_id": "x"})


def test_personnummer_with_space_is_masked():
    masked, cats = mask_text("personnummer 19870312 4514", TODAY)
    assert "4514" not in masked and cats == ["personnummer"]


@pytest.mark.parametrize("text", ["Anteckningen hamnade på en annan patient.",
                                  "Patienten fick dubbel dos.", "Det blev feldos i morse."])
def test_patient_safety_variants(text):
    r = classify(text.lower())
    assert r.label == "journalfel" and "patient_safety" in r.forced_handoff


def test_window_mixup_is_not_journal_error():
    assert classify("jag förväxlade två fönster i klienten.").label != "journalfel"


def test_felkod_is_not_journal_error():
    assert classify("jag öppnade läkemedelslistan och fick felkod 42.").label != "journalfel"


def test_genitive_name_and_ssk_masked():
    masked, cats = mask_text("Anna Svenssons fråga, ssk Maja Holm", TODAY)
    assert "Svensson" not in masked and "Holm" not in masked
    assert "namn" in cats


def test_obfuscated_mail_and_journalnummer_masked():
    masked, cats = mask_text("Mejl maja.holm(at)example.se, journalnummer JV-2024-9912", TODAY)
    assert "maja.holm" not in masked and "9912" not in masked
    assert "epost" in cats and "identifierare" in cats


def test_parenthesized_and_0046_phone_masked():
    masked, cats = mask_text("Ring (070) 174 06 05 eller 0046-70-174 06 05.", TODAY)
    assert "174" not in masked and "070" not in masked
    assert cats == ["telefon"]
