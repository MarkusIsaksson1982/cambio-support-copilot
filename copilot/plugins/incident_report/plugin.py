"""incident_report (avvikelse). One extraction step, then a human. Never auto-sent.

Harm words are the ones named in docs/EXTENDING.md. `fall` is a whole word so
`tillfälle` does not count. Every case keeps `incident_always_human`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from copilot.core.plugin import ModelTask, RuleResult

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "incident_report.v1.schema.json"
INCIDENT_SCHEMA = json.loads(CONTRACT.read_text(encoding="utf-8"))

_BOOKKEEPING = {"schema_version", "status", "route", "source_request_id"}
EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["what", "when", "where", "harm", "immediate_action", "confidence"],
    "properties": {k: v for k, v in INCIDENT_SCHEMA["properties"].items() if k not in _BOOKKEEPING},
}
HARM_PATTERNS = (
    (re.compile(r"fel patient"), "fel patient"),
    (re.compile(r"fel ?dos"), "fel dos"),
    (re.compile(r"\bfall\b"), "fall"),
)
PROMPT = """Du fyller i en avvikelserapport från redan maskad text. Svara ENDAST med JSON:
{{"what": "vad hände", "when": "när, eller tom sträng", "where": "var, eller tom sträng",
  "harm": "ingen|risk|lindrig|allvarlig|okand", "immediate_action": "vad som redan gjorts, eller tom sträng",
  "confidence": 0.0}}
Hitta inte på uppgifter som inte står i texten. Är du osäker, sätt harm till "okand" och confidence under 0.6.

Text:
\"\"\"{text}\"\"\""""


class IncidentReportPlugin:
    name = "incident_report"
    version = "0.1.0"
    output_schema = INCIDENT_SCHEMA
    confidence_threshold = 0.6

    def rules(self, masked_text: str) -> RuleResult:
        t = masked_text.lower()
        hits = []
        for pattern, phrase in HARM_PATTERNS:
            m = pattern.search(t)
            if m:
                hits.append({"label": "avvikelse", "phrase": m.group(0), "weight": 4})
        label = "avvikelse" if hits else None
        return RuleResult(label, 0.9 if hits else 0.0, hits, "patientsakerhet",
                          ["incident_always_human"])

    def model_task(self, masked_text: str, rule: RuleResult) -> ModelTask | None:
        return ModelTask("extract_incident", PROMPT.format(text=masked_text), EXTRACT_SCHEMA)

    def build_output(self, masked_text, rule, model_output):
        out = {"schema_version": "1.0.0", "what": "", "when": "", "where": "",
               "harm": "okand", "immediate_action": "", "confidence": 0.0,
               "status": "draft", "route": rule.route or "patientsakerhet"}
        if model_output:
            for key in ("what", "when", "where", "harm", "immediate_action", "confidence"):
                if key in model_output:
                    out[key] = model_output[key]
        return out

    def handoff_reasons(self, output, rule):
        reasons = []
        if not str(output.get("what") or "").strip():
            reasons.append("incident_what_empty")
        if output.get("harm") in {"allvarlig", "okand"}:
            reasons.append("incident_harm_needs_review")
        return reasons
