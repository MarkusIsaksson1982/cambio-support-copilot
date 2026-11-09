"""Generate language-neutral fixtures from the live Python reference pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.core.adapters import FakeAdapter, NoneAdapter
from copilot.core.audit import AuditLog
from copilot.core.masking import mask_text
from copilot.core.pipeline import run
from copilot.chain import incident_from_envelope

OUT = Path(__file__).resolve().parent / "fixtures"


def dump(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = [json.loads(line) for line in (ROOT / "data/support_tickets.jsonl").read_text(encoding="utf-8").splitlines()]
    selected = [source[0], source[4], source[16]]
    dump("request.json", {"type": "support_ticket", "id": selected[0]["id"], "text": selected[0]["text"]})
    # Keep a concrete span fixture with the same offsets/replacement convention as masking.py.
    raw = "personnummer 19121212-1212"
    masked, categories = mask_text(raw)
    start = raw.index("19121212-1212")
    dump("masked_span.json", {"category": categories[0], "start": start, "stop": len(raw), "replacement": masked[start:]})

    generated = []
    audits = []
    for i, ticket in enumerate(selected):
        log = AuditLog()
        adapter = FakeAdapter() if i == 1 else NoneAdapter()
        env = run({"type": "support_ticket", "id": ticket["id"], "text": ticket["text"]}, adapter, log)
        generated.append(env)
        audits.extend(log.events)
    envelope = generated[-1]
    incident = incident_from_envelope(envelope, NoneAdapter(), AuditLog())
    dump("handoff_envelope.json", generated[0])
    dump("audit_events.json", audits)
    dump("incident_result.json", incident)
    dump("incident_report.json", incident["report"])


if __name__ == "__main__":
    main()
