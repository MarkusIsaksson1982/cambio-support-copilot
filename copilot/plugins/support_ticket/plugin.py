"""support_ticket: Swedish support tickets from healthcare staff (synthetic)."""
from __future__ import annotations

from copilot.core.plugin import ModelTask, RuleResult
from copilot.plugins.support_ticket import rules
from copilot.plugins.support_ticket.drafter import RetrievalDrafter

CONF = {"type": "number", "minimum": 0.0, "maximum": 1.0}
TEXT = {"type": "string", "minLength": 1}

MODEL_SCHEMA = {"type": "object", "additionalProperties": False,
                "required": ["label", "confidence", "rationale"],
                "properties": {"label": {"type": "string", "enum": rules.LABELS},
                               "confidence": CONF, "rationale": TEXT}}

OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["label", "label_display", "confidence", "source", "route", "reply_draft",
                 "citations"],
    "properties": {"label": {"type": "string", "enum": rules.LABELS}, "label_display": TEXT,
                   "confidence": CONF,
                   "source": {"type": "string", "enum": ["rules", "model_proposal", "abstain"]},
                   "route": TEXT, "rationale": {"type": "string"},
                   "reply_draft": {"type": "string"},
                   "citations": {"type": "array", "items": TEXT},
                   "suggest_request_type": {"type": "string"}}}

PROMPT = """Du klassar svenska supportärenden från vårdpersonal. Texten är redan maskad.
Svara ENDAST med JSON: {{"label": en av {labels}, "confidence": 0-1, "rationale": kort motivering}}.
Är du osäker, välj "ovrigt" med låg confidence.

Ärende:
\"\"\"{text}\"\"\""""


class SupportTicketPlugin:
    name = "support_ticket"
    version = "0.1.0"
    output_schema = OUTPUT_SCHEMA
    confidence_threshold = 0.6

    def __init__(self, drafter=None):
        self.drafter = drafter or RetrievalDrafter()

    def rules(self, masked_text: str) -> RuleResult:
        return rules.classify(masked_text)

    def model_task(self, masked_text: str, rule: RuleResult) -> ModelTask | None:
        if rule.label is not None:
            return None  # rules decided: no model call at all
        return ModelTask("classify_ticket",
                         PROMPT.format(labels=rules.LABELS, text=masked_text), MODEL_SCHEMA)

    def build_output(self, masked_text, rule, model_output):
        if rule.label is not None:
            label, conf, source, why = rule.label, rule.confidence, "rules", "regelträffar"
        elif model_output:
            label, conf = model_output["label"], model_output["confidence"]
            source, why = "model_proposal", model_output["rationale"]
        else:
            label, conf, source, why = "ovrigt", 0.0, "abstain", "oklassat"
        draft = self.drafter.draft(masked_text, label) if label != "journalfel" else None
        out = {"label": label, "label_display": rules.DISPLAY[label], "confidence": conf,
               "source": source, "route": rules.ROUTES[label], "rationale": why,
               "reply_draft": draft["reply"] if draft else "",
               "citations": draft["citations"] if draft else []}
        if label == "journalfel":
            out["suggest_request_type"] = "incident_report"
        return out

    def handoff_reasons(self, output, rule):
        r = []
        if output["label"] == "journalfel":
            r.append("journal_error_needs_incident_report")
        if output["source"] == "model_proposal":
            r.append("model_proposal_needs_review")
        if not output["reply_draft"]:
            r.append("no_grounded_draft")
        return r
