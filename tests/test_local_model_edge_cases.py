"""Replay of REAL local-model (Ollama, qwen2.5 / llama3.2) replies captured by
scripts/local_e2e.py, plus PII cases where a local model found what the regex masker missed.

Small local models fail in natural ways (missing keys, misspelled keys, an over-confident
"ovrigt", timeouts). Each recorded reply is replayed offline through the real pipeline
with FakeAdapter, so the fail-closed behaviour is tested without Ollama installed.
"""
import json
from pathlib import Path

import pytest

from copilot.core import pipeline
from copilot.core.adapters import FakeAdapter
from copilot.core.audit import AuditLog
from copilot.core.masking import mask_text

FIX = Path(__file__).parent / "fixtures"
REPLAYS = json.loads((FIX / "local_model_replies.json").read_text(encoding="utf-8"))
PII = json.loads((FIX / "local_model_pii_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", REPLAYS, ids=[f'{c["model"]}:{c["id"]}' for c in REPLAYS])
def test_recorded_local_reply_replays(case):
    env = pipeline.run({"type": "support_ticket", "text": case["text"]},
                       FakeAdapter(lambda _p: case["reply"]), AuditLog())
    assert env["model"]["status"] == case["expected_model_status"]
    if case["expected_model_status"] != "ok":
        assert env["status"] == "handoff"  # never auto-approvable on a bad model step
        assert env["output"]["source"] == "abstain"
    else:
        assert "model_proposal_needs_review" in env["handoff_reasons"]


@pytest.mark.parametrize("case", PII, ids=[c["id"] for c in PII])
def test_pii_found_by_local_model(case):
    masked, _ = mask_text(case["text"])
    for s in case["must_be_masked"]:
        assert s not in masked
    leftover = [s for s in case.get("accepted_gaps", []) if s in masked]
    if leftover:
        pytest.xfail(case.get("known_gap") or f"accepted gaps still visible: {leftover}")
