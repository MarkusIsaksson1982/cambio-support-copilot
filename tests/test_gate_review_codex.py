import pytest

from copilot.core.approval import decide
from copilot.core.audit import AuditLog
from copilot.core.grounding import check_citation
from copilot.core.span_gate import check_spans


@pytest.mark.parametrize("raw, span", [
    ("xTova", "Tova"),
    ("Tova2", "Tova"),
    ("Tova_name", "Tova"),
])
def test_span_fragment_inside_longer_token_is_rejected(raw, span):
    result = check_spans(raw, [span])
    assert result["rejected"] == [span]
    assert result["status"] == "handoff"


def test_span_boundary_is_case_sensitive_and_whitespace_is_not_normalized():
    result = check_spans("Tova Patient", ["tova", " Patient", "Patient"])
    assert result["accepted"] == ["Patient"]
    assert result["rejected"] == ["tova", " Patient"]


def test_unicode_lookalike_span_is_not_accepted():
    # Cyrillic о is visually similar to Latin o, but is not the raw substring.
    result = check_spans("Tova", ["Tоva"])
    assert result["status"] == "handoff"
    assert result["accepted"] == []


@pytest.mark.parametrize("raw", [
    '{"citation": ["KB-1"]}',
    '{"citation": {"id": "KB-1"}}',
])
def test_non_string_citation_hands_off(raw):
    assert check_citation(raw, ["KB-1"])["status"] == "handoff"


def test_empty_kb_cannot_ground_a_citation():
    assert check_citation('{"citation":"KB-1"}', [])["status"] == "handoff"


def test_approval_remasks_reply_draft_before_returning():
    result = {"request_id": "synthetic", "status": "awaiting_approval",
              "output": {"reply_draft": "Call patient 811218-9876"}}
    sent = decide(result, "reviewer", "approve", AuditLog())
    assert "811218-9876" not in sent["reply"]
    assert "[personnummer-maskat]" in sent["reply"]
