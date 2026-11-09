"""Round-2 top-ranked edge cases (Lo · Cambio): replayed offline, no Ollama needed."""
import json
from pathlib import Path

import pytest

from copilot.core import pipeline
from copilot.core.adapters import FakeAdapter
from copilot.core.approval import decide
from copilot.core.audit import AuditLog
from copilot.core.span_gate import check_spans

CASES = json.loads((Path(__file__).parent / "fixtures" / "top_edge_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_top_edge_case(case):
    if case["kind"] == "pii_span":
        g = check_spans(case["text"], case["entities"])
        assert sorted(g["rejected"]) == sorted(case["expect_rejected"])
        assert g["status"] == case["expect_status"]
        assert all(s in case["text"] for s in g["accepted"])
        return
    env = pipeline.run({"type": "support_ticket", "text": case["text"]},
                       FakeAdapter(lambda _p: case["reply"]), AuditLog())
    assert env["status"] == case["expect_status"]
    for r in case["expect_reasons"]:
        assert r in env["handoff_reasons"]
    with pytest.raises(PermissionError):  # cannot be auto-approved as-is
        decide(env, "ssk-test", "approve", AuditLog())


def test_span_gate_rejects_non_strings_and_case_mismatch():
    g = check_spans("Patient Tova", [{"text": "tova"}, {"text": ""}, None, {"text": "Tova"}])
    assert g["accepted"] == ["Tova"] and g["status"] == "handoff"
