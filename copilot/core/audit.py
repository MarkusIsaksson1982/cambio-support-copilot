"""Append-only JSONL audit log. Everything written is masked again (defence in depth)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from copilot.core.masking import sanitize

AUDIT_VERSION = "1.0.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def text_hash(text: str) -> str:
    """Hash of the RAW input so a case can be matched later without storing it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class AuditLog:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.events: list[dict] = []

    def write(self, event: str, request_id: str, **data) -> dict:
        rec = sanitize({"audit_version": AUDIT_VERSION, "ts": now(), "event": event,
                        "request_id": request_id, **data})
        self.events.append(rec)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")
        return rec

    def for_request(self, request_id: str) -> list[dict]:
        return [e for e in self.events if e["request_id"] == request_id]
