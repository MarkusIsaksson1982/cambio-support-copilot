"""Reply drafting.

`RetrievalDrafter` is the demo path: one synthetic doc, or no draft.
`TemplateDrafter` remains for a fixed citation per label.
"""
from __future__ import annotations

from typing import Protocol

KB = {  # fake internal docs (synthetic)
    "inloggning": ("KB-101", "Logga ut, ta ut och sätt i SITHS-kortet igen och starta om klienten."),
    "behorighet": ("KB-204", "Behörighet beställs av din behörighetsansvarige via beställningsformuläret."),
    "bugg": ("KB-310", "Notera felkod och tidpunkt; ärendet går vidare till andra linjen."),
    "instruktion": ("KB-120", "Se snabbguiden i hjälpmenyn under 'Hjälp > Snabbguider'."),
}


class ReplyDrafter(Protocol):
    def draft(self, masked_text: str, label: str) -> dict | None:
        """Return {"reply": str, "citations": [doc_id]} or None when ungrounded."""


class TemplateDrafter:
    def draft(self, masked_text: str, label: str) -> dict | None:
        if label not in KB:
            return None  # ungrounded -> no draft, handoff
        doc, text = KB[label]
        return {"reply": f"Hej! Tack för ditt ärende. {text} [{doc}] Hälsningar, Support",
                "citations": [doc]}


def grounded_reply(doc: dict) -> str:
    """The only text a retrieved citation is allowed to contribute."""
    title = str(doc.get("title") or "").strip()
    body = str(doc.get("body") or "").strip()
    return f"{title}\n{body}".strip()


class RetrievalDrafter:
    """Cite one retrieved synthetic doc, or nothing. No model call."""

    def __init__(self, docs: list[dict] | None = None):
        self._docs = docs

    def draft(self, masked_text: str, label: str) -> dict | None:
        from copilot.plugins.support_ticket.retrieve import search
        hits = search(masked_text, self._docs)
        if not hits:
            return None
        text = grounded_reply(hits[0])
        if not text:
            return None
        return {"reply": text, "citations": [hits[0]["id"]]}
