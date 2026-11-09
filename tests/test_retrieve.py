"""Saturday retrieval: 11 synthetic docs, SITHS hits, abstain tickets miss."""
import json
from pathlib import Path

from copilot.core.grounding import check_citation
from copilot.core.masking import find_personnummer
from copilot.plugins.support_ticket.retrieve import load_docs, search

GAP = Path("data/gap_tickets_2026-11-05.jsonl")


def _gap(tid: str) -> str:
    for line in GAP.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        t = json.loads(line)
        if t["id"] == tid:
            return t["text"]
    raise AssertionError(tid)


def test_kb_has_eleven_docs_and_no_personnummer():
    docs = load_docs()
    ids = [d["id"] for d in docs]
    assert len(ids) == 11
    assert len(set(ids)) == 11
    for doc in docs:
        assert find_personnummer(f"{doc['title']}\n{doc['body']}") == []
        assert isinstance(doc["tags"], list)


def test_siths_login_hits_an_inloggning_doc():
    hits = search("Kan inte logga in med SITHS-kortet")
    assert len(hits) == 1
    tags = " ".join(hits[0]["tags"]).lower()
    assert "inloggning" in tags or "siths" in tags
    assert hits[0]["id"] in {d["id"] for d in load_docs()}


def test_abstain_tickets_do_not_retrieve():
    assert search(_gap("G-008")) == []
    assert search(_gap("G-007")) == []
    assert search(_gap("G-009")) == []


def test_citation_gate_accepts_only_a_retrieved_id():
    hits = search("Jag kan inte logga in till SITHS-systemet")
    ids = [d["id"] for d in load_docs()]
    assert check_citation(json.dumps({"citation": "KB-101"}), ids)["status"] == "handoff"
    assert check_citation(json.dumps({"citation": hits[0]["id"]}), ids)["status"] == "grounded"
