"""Fail-closed citation gate: a draft is grounded only if it cites an exact id in the KB."""
import json


def check_citation(raw_reply: str, kb_ids) -> dict:
    try:
        o = json.loads(raw_reply)
    except (ValueError, TypeError):
        return {"status": "handoff", "reason": "unparseable"}
    c = o.get("citation") if isinstance(o, dict) else None
    if not isinstance(c, str) or not c:
        return {"status": "handoff", "reason": "abstained"}
    try:
        ids = set(kb_ids) if kb_ids is not None else set()
    except (TypeError, ValueError):
        ids = set()
    if not ids or c not in ids:
        return {"status": "handoff", "reason": "citation_not_in_kb"}
    return {"status": "grounded", "citation": c}
