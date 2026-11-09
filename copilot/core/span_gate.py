"""Exact-substring gate for PII spans proposed by a (local) model.

A model may only ADD masks. A proposed span is accepted only if it occurs verbatim in the
raw text; anything else (e.g. qwen2.5:3b inventing "22-4821") is rejected and forces handoff,
because a model that invents spans cannot be trusted to have found the real ones.
"""
from __future__ import annotations

R_SPAN = "model_span_not_in_text"


def _has_token_boundaries(raw_text: str, span: str) -> bool:
    """Require a proposed span to cover whole tokens, not fragments of words/IDs."""
    start = 0
    while True:
        start = raw_text.find(span, start)
        if start < 0:
            return False
        end = start + len(span)
        left_ok = start == 0 or not (raw_text[start - 1].isalnum() or raw_text[start - 1] == "_")
        right_ok = end == len(raw_text) or not (raw_text[end].isalnum() or raw_text[end] == "_")
        if left_ok and right_ok:
            return True
        start += 1


def check_spans(raw_text: str, entities) -> dict:
    raw_text = raw_text if isinstance(raw_text, str) else ""
    accepted, rejected = [], []
    for e in entities if isinstance(entities, list) else []:
        s = e.get("text") if isinstance(e, dict) else e
        if not isinstance(s, str) or not s.strip():
            rejected.append(s); continue
        (accepted if _has_token_boundaries(raw_text, s) else rejected).append(s)
    reasons = [R_SPAN] if rejected else []
    return {"accepted": accepted, "rejected": rejected, "handoff_reasons": reasons,
            "status": "handoff" if rejected else "ok"}


def apply_masks(raw_text: str, accepted, mask: str = "[PII]") -> str:
    for s in sorted(set(accepted), key=len, reverse=True):
        raw_text = raw_text.replace(s, mask)
    return raw_text
