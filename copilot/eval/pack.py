"""Schema, citation, handoff and repeat-stability pack.

The adapter is `none`, so a model is never called. Repeating the pack measures
whether the offline path flaps. It does not measure a live model.
"""
from __future__ import annotations

import json
from pathlib import Path

from copilot.chain import incident_from_envelope, validate_envelope
from copilot.core.adapters import NoneAdapter
from copilot.core.audit import AuditLog
from copilot.core.masking import sanitize
from copilot.core.pipeline import run
from copilot.plugins.support_ticket.drafter import grounded_reply
from copilot.plugins.support_ticket.retrieve import load_docs, search

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
TICKET_FILES = (DATA / "support_tickets.jsonl", DATA / "gap_tickets_2026-11-05.jsonl")


def load_tickets() -> list[dict]:
    tickets = []
    for path in TICKET_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tickets.append(json.loads(line))
    return tickets


def _signature(result: dict) -> tuple:
    out = result.get("output") or {}
    return (result["status"], tuple(result["handoff_reasons"]),
            tuple(out.get("citations") or []), out.get("label"),
            out.get("suggest_request_type"))


def _one(ticket: dict, docs: list[dict], by_id: dict[str, dict]) -> dict:
    audit = AuditLog()
    result = run({"type": "support_ticket", "id": ticket["id"], "text": ticket["text"]},
                 adapter=NoneAdapter(), audit=audit)
    decided = [e for e in audit.events if e["event"] == "decided"]
    cited = list((result.get("output") or {}).get("citations") or [])
    reply = (result.get("output") or {}).get("reply_draft") or ""
    label = (result.get("output") or {}).get("label")
    hit = search(result["masked_text"], docs)
    faithful = True
    if cited:
        doc = by_id.get(cited[0]) if len(cited) == 1 else None
        faithful = (doc is not None and reply == sanitize(grounded_reply(doc))
                    and (not hit or cited[0] == hit[0]["id"]))
    eligible = bool(hit) and label != "journalfel"
    recalled = eligible and cited == [hit[0]["id"]]
    incident_ok = True
    if (result.get("output") or {}).get("suggest_request_type") == "incident_report":
        chained = incident_from_envelope(result, adapter=NoneAdapter())
        incident_ok = chained["report_errors"] == [] and chained["status"] == "handoff"
    return {"id": ticket["id"], "result": result, "signature": _signature(result),
            "schema_ok": validate_envelope(result) == [],
            "audit_ok": len(decided) == 1 and decided[0]["status"] == result["status"]
                        and list(decided[0]["handoff_reasons"]) == list(result["handoff_reasons"]),
            "patient_data": "patient_data_detected" in result["handoff_reasons"],
            "needs_human": bool(ticket.get("needs_human")),
            "retrieved": bool(hit), "cited": bool(cited), "faithful": faithful,
            "eligible": eligible,
            "recalled": recalled, "incident_ok": incident_ok}


def _rate(hits: int, total: int) -> float | None:
    return None if total == 0 else round(hits / total, 4)


def evaluate(runs: int = 3) -> dict:
    docs = load_docs()
    by_id = {d["id"]: d for d in docs}
    tickets = load_tickets()
    passes = []
    for _ in range(runs):
        passes.append([_one(t, docs, by_id) for t in tickets])
    first = passes[0]
    flaky = [row["id"] for row, *rest in zip(*passes)
             if any(row["signature"] != other["signature"] for other in rest)]
    patient = [r for r in first if r["patient_data"]]
    human = [r for r in first if r["needs_human"]]
    cited = [r for r in first if r["cited"]]
    eligible = [r for r in first if r["eligible"]]
    incidents = [r for r in first if (r["result"].get("output") or {}).get("suggest_request_type")]
    handoffs = [r for r in first if r["result"]["status"] == "handoff"]
    return {
        "adapter": "none",
        "tickets": len(first),
        "runs": runs,
        "schema_pass": _rate(sum(r["schema_ok"] for r in first), len(first)),
        "audit_match": _rate(sum(r["audit_ok"] for r in first), len(first)),
        "handoff_rate": _rate(len(handoffs), len(first)),
        "awaiting_approval": len(first) - len(handoffs),
        "patient_data_cases": len(patient),
        "patient_data_handoff": _rate(sum(r["result"]["status"] == "handoff" for r in patient), len(patient)),
        "needs_human_cases": len(human),
        "needs_human_handoff": _rate(sum(r["result"]["status"] == "handoff" for r in human), len(human)),
        "retrieval_hits": sum(r["retrieved"] for r in first),
        "citation_cited": len(cited),
        "citation_faithfulness": _rate(sum(r["faithful"] for r in cited), len(cited)),
        "citation_eligible": len(eligible),
        "citation_recall": _rate(sum(r["recalled"] for r in eligible), len(eligible)),
        "incident_chains": len(incidents),
        "incident_schema_pass": _rate(sum(r["incident_ok"] for r in incidents), len(incidents)),
        "repeat_mismatches": flaky,
    }


def render_markdown(summary: dict) -> str:
    def pct(v):
        return "n/a" if v is None else f"{v:.0%}" if v in (0, 1) else f"{v:.1%}"
    lines = [
        "# Eval pack — offline, no model",
        "",
        f"Adapter `{summary['adapter']}` on {summary['tickets']} synthetic tickets, "
        f"{summary['runs']} identical repeats. A live model is not in these numbers.",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Schema-valid envelopes | {pct(summary['schema_pass'])} |",
        f"| Audit `decided` matches the envelope | {pct(summary['audit_match'])} |",
        f"| Handoff rate | {pct(summary['handoff_rate'])} ({summary['tickets'] - summary['awaiting_approval']} of {summary['tickets']}) |",
        f"| Awaiting a human approval | {summary['awaiting_approval']} |",
        f"| Patient-data cases that hand off | {pct(summary['patient_data_handoff'])} of {summary['patient_data_cases']} |",
        f"| `needs_human` cases that hand off | {pct(summary['needs_human_handoff'])} of {summary['needs_human_cases']} |",
        f"| Retrieval hits | {summary['retrieval_hits']} of {summary['tickets']} |",
        f"| Citation faithfulness | {pct(summary['citation_faithfulness'])} of {summary['citation_cited']} cited drafts |",
        f"| Citation recall | {pct(summary['citation_recall'])} of {summary['citation_eligible']} retrieved, non-journalfel tickets |",
        f"| Incident chain schema-pass | {pct(summary['incident_schema_pass'])} of {summary['incident_chains']} |",
        f"| Repeat mismatches | {len(summary['repeat_mismatches'])} |",
        "",
        "Faithfulness means the citation is the retrieved doc and the draft is that doc's title and body after the pipeline's mask pass, nothing else.",
        "Recall skips tickets the retriever misses, and skips `journalfel` because those drafts are withheld on purpose.",
        "Repeat mismatches are ids whose status, reasons, citations or label differed across the offline repeats.",
        "",
    ]
    if summary["repeat_mismatches"]:
        lines.append("Mismatched ids: " + ", ".join(summary["repeat_mismatches"]) + "\n")
    return "\n".join(lines)
