import json
from datetime import date

from copilot.core.adapters import FakeAdapter, NoneAdapter
from copilot.core.plugin import RuleResult
from copilot.core.masking import mask_text
from copilot.chain import validate_envelope
from copilot.core import plugin as registry
from copilot.core.audit import AuditLog

registry.load_builtin()


def make_pipeline_result(request, adapter=None, audit=None):
    from copilot.core.pipeline import run
    return run(request, adapter=adapter, audit=audit)


class TestPipeline:
    def test_rules_decided_no_model_call(self):
        ticket = {
            "id": "test-001",
            "text": "Jag kan inte logga in till SITHS-systemet",
        }
        result = make_pipeline_result(ticket, adapter=FakeAdapter(reply="{}"))
        # When rules decide, model_task returns None, so adapter.complete is never called
        # Check that model.status indicates skipped (no model call made)
        assert result["model"]["status"] in ("skipped",)

    def test_undecided_ticket_uses_model(self):
        ticket = {
            "id": "test-002",
            "text": "Har en fråga om tillgängliga tjänster",
        }
        result = make_pipeline_result(ticket, adapter=FakeAdapter())
        # Rules undecided -> model called -> model_output present
        assert result["model"]["status"] != "skipped"

    def test_invalid_model_json_status_handoff(self):
        ticket = {
            "id": "test-003",
            "text": "Har en fråga om tillgängliga tjänster",
        }
        result = make_pipeline_result(ticket, adapter=FakeAdapter(reply="invalid json"))
        assert result["status"] == "handoff"
        assert "model_output_invalid" in result["handoff_reasons"]

    def test_noneadapter_model_abstained(self):
        ticket = {
            "id": "test-004",
            "text": "Okänt ärende",
        }
        result = make_pipeline_result(ticket, adapter=NoneAdapter())
        assert result["model"]["status"] == "abstain"
        assert "model_abstained" in result["handoff_reasons"]

    def test_personnummer_patient_data_detected_handoff(self):
        ticket = {
            "id": "test-005",
            "text": "Anna Svensson, personnummer 811218-9876, kan inte logga in",
        }
        result = make_pipeline_result(ticket, adapter=NoneAdapter())
        assert "patient_data_detected" in result["handoff_reasons"]
        assert result["status"] == "handoff"

    def test_journalfel_suggest_request_type_incident_report(self):
        ticket = {
            "id": "test-006",
            "text": "Fel patient Johan Andersson fel i journal",
        }
        result = make_pipeline_result(ticket)
        assert result["output"].get("suggest_request_type") == "incident_report"

    def test_audit_never_contains_raw_persondata(self):
        ticket = {
            "id": "test-007",
            "text": "Anna Svensson, personnummer 811218-9876, ring 070-174 06 05, stöd@example.se",
        }
        audit = AuditLog()
        result = make_pipeline_result(ticket, adapter=NoneAdapter(), audit=audit)
        # Check audit events for raw personnummer, name, or phone
        for event in audit.for_request(result["request_id"]):
            event_str = json.dumps(event)
            assert "811218-9876" not in event_str
            assert "Anna Svensson" not in event_str
            assert "070-174 06 05" not in event_str
            assert "stöd@example.se" not in event_str

    def test_result_validates_against_envelope(self):
        ticket = {
            "id": "test-008",
            "text": "Jag kan inte logga in till SITHS-systemet",
        }
        result = make_pipeline_result(ticket, adapter=FakeAdapter())
        errors = validate_envelope(result)
        assert errors == [], f"Envelope validation errors: {errors}"