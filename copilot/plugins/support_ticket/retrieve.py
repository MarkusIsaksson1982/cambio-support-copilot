"""Token-overlap retrieval over the synthetic KB. No model call.

A hit has to be about the ticket, not a single shared word. Short tickets
(the SITHS demo line) clear a high overlap ratio. Longer tickets dilute that
ratio, so four shared stems at a lower ratio still count. Two weak stems,
as in the G-008 abstain ticket, do not.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

KB_PATH = Path(__file__).resolve().parents[3] / "data" / "kb.json"

_STOP = {
    "och", "att", "det", "den", "en", "ett", "som", "är", "på", "av", "för",
    "till", "med", "om", "jag", "du", "vi", "ni", "de", "dem", "inte", "kan",
    "ska", "vill", "har", "hade", "vara", "var", "finns", "utan", "från",
    "efter", "innan", "under", "över", "vid", "när", "hur", "vad", "vem",
    "vilka", "vilket", "detta", "dessa", "man", "oss", "sin", "sitt", "sina",
    "eller", "men", "också", "bara", "hej", "tack",
}
_SUFFIXES = ("andet", "ende", "erna", "arna", "het", "ade", "are", "ern",
             "en", "et", "na", "ar", "er", "or")


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-zåäö0-9]+", (text or "").lower())
            if len(w) >= 4 and w not in _STOP}


def load_docs(path: Path | None = None) -> list[dict]:
    data = json.loads((path or KB_PATH).read_text(encoding="utf-8"))
    docs = data["docs"] if isinstance(data, dict) else data
    return list(docs)


def _indexed(doc: dict) -> str:
    tags = " ".join(doc.get("tags") or [])
    return f"{doc.get('title', '')}\n{doc.get('body', '')}\n{tags}"


def _clears(overlap: int, ratio: float) -> bool:
    return (overlap >= 2 and ratio >= 0.5) or (overlap >= 4 and ratio >= 0.30)


def search(text: str, docs: list[dict] | None = None) -> list[dict]:
    """Return the single best doc, or [] when nothing clears the minimum."""
    query = tokens(text)
    if not query:
        return []
    best = None
    best_key = None
    for doc in docs if docs is not None else load_docs():
        shared = query & tokens(_indexed(doc))
        overlap = len(shared)
        ratio = overlap / len(query)
        if not _clears(overlap, ratio):
            continue
        key = (ratio, overlap, doc["id"])
        if best_key is None or key > best_key:
            best_key = key
            best = doc
    return [best] if best is not None else []
