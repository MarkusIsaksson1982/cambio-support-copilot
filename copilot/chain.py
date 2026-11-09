"""Chaining a SEPARATE project via the JSON contract (path b in docs/EXTENDING.md)."""
from __future__ import annotations

import json
from pathlib import Path

from copilot.core.schema import validate

_C = Path(__file__).resolve().parents[1] / "contracts"
ENVELOPE_SCHEMA = json.loads((_C / "handoff_envelope.v1.schema.json").read_text(encoding="utf-8"))
INCIDENT_SCHEMA = json.loads((_C / "incident_report.v1.schema.json").read_text(encoding="utf-8"))


def validate_envelope(env: dict) -> list[str]:
    return validate(env, ENVELOPE_SCHEMA)


def validate_incident(rep: dict) -> list[str]:
    return validate(rep, INCIDENT_SCHEMA)


def incident_from_envelope(envelope: dict, adapter=None, audit=None) -> dict:
    """Path (b) reference consumer: envelope in -> incident report out.

    Runs the incident_report plugin on the envelope's ALREADY-MASKED text, carries the
    upstream masked_categories (so patient-data handoff is not lost on re-submit) and
    stamps source_request_id. A separate project implements the same function.
    """
    errs = validate_envelope(envelope)
    if errs:
        raise ValueError("invalid envelope: " + "; ".join(errs))
    from copilot.core import pipeline
    res = pipeline.run({"type": "incident_report", "id": envelope["request_id"] + ":incident",
                        "text": envelope["masked_text"]}, adapter, audit)
    report = dict(res["output"])
    report["source_request_id"] = envelope["request_id"]
    report.setdefault("route", res["route"])
    return {"report": report, "report_errors": validate_incident(report),
            "status": res["status"],
            "handoff_reasons": list(dict.fromkeys(
                res["handoff_reasons"] + (["upstream_patient_data"] if set(
                    envelope["masked_categories"]) & {"personnummer", "identifierare"} else [])))}
