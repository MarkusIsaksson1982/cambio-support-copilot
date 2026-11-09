"""Offline replay of qwen2.5:7b RAG failures captured as local-model fixtures."""
import json
from pathlib import Path

import pytest

from copilot.core.grounding import check_citation

FIX = Path(__file__).parent / "fixtures" / "rag_abstain_cases.json"
CASES = json.loads(FIX.read_text(encoding="utf-8"))
KB_IDS = ["codex:KB-001", "codex:KB-002", "codex:KB-003", "grok-build:KB-001", "grok-build:KB-002",
          "grok-build:KB-003", "opencode-deepseek-v4.1-flash-free:KB-001",
          "opencode-deepseek-v4.1-flash-free:KB-002", "opencode-deepseek-v4.1-flash-free:KB-003",
          "opencode-glm-5.3-flash-free:KB-001", "opencode-glm-5.3-flash-free:KB-002"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_failing_local_reply_never_grounded(case):
    assert check_citation(case["raw_reply"], KB_IDS)["status"] == "handoff"


def test_exact_kb_id_is_grounded():
    assert check_citation('{"citation": "codex:KB-001"}', KB_IDS)["status"] == "grounded"
