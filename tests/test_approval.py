import json
from copilot.core.approval import decide
from copilot.core.audit import AuditLog
from copilot.core.masking import mask_note
from copilot.core.adapters import NoneAdapter


class TestApproval:
    def test_approve_handoff_raises_permission_error(self):
        from copilot.core.pipeline import run
        result = run({
            "id": "test-001",
            "text": "Anna Svensson, personnummer 811218-9876, kan inte logga in",
        }, adapter=NoneAdapter())
        result["status"] = "handoff"
        try:
            decide(result, reviewer="test", decision="approve", audit=AuditLog())
            assert False, "Should have raised PermissionError"
        except PermissionError:
            pass

    def test_edit_needs_edited_reply(self):
        from copilot.core.pipeline import run
        result = run({
            "id": "test-002",
            "text": "Jag kan inte logga in till SITHS-systemet",
        })
        try:
            decide(result, reviewer="test", decision="edit", audit=AuditLog())
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "edited_reply" in str(e).lower() or "edited" in str(e).lower()

    def test_reviewer_required(self):
        from copilot.core.pipeline import run
        result = run({
            "id": "test-003",
            "text": "Okänt ärende",
        })
        try:
            decide(result, reviewer="", decision="take_over", audit=AuditLog())
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_decisions_audited_with_masked_note(self):
        from copilot.core.pipeline import run
        audit = AuditLog()
        result = run({
            "id": "test-004",
            "text": "Anna Svensson, personnummer 811218-9876",
        }, adapter=NoneAdapter())
        decide(result, reviewer="granskare-1", decision="take_over", audit=audit,
               note="Ring Anna Svensson om 811218-9876")
        # decide() returns one record. The log is the list to assert on.
        events = [event for event in audit.events if event["event"] == "human_decision"]
        assert len(events) == 1
        blob = json.dumps(events[0], ensure_ascii=False)
        assert "811218-9876" not in blob
        assert "Anna Svensson" not in blob
        assert events[0]["decision"] == "take_over"
        assert events[0]["final_state"] == "human_owned"