"""Safety spine shared by every request type; failures always become handoffs."""
from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path

from copilot.core import plugin as registry
from copilot.core.adapters import ModelAdapter, NoneAdapter, parse_json
from copilot.core.audit import AuditLog, text_hash
from copilot.core.masking import find_unverified_personnummer_shapes, mask_text, sanitize
from copilot.core.schema import validate

CONTRACT_VERSION = "1.0.0"
AWAITING_APPROVAL = "awaiting_approval"
HANDOFF = "handoff"
R_PATIENT_DATA = "patient_data_detected"
R_INVALID = "model_output_invalid"
R_ABSTAIN = "model_abstained"
R_LOW_CONF = "low_confidence"
R_EMPTY = "empty_input"
R_PLUGIN = "plugin_error"
R_ADAPTER = "adapter_error"
R_PROMPT = "unsafe_prompt"
_ENVELOPE = json.loads((Path(__file__).resolve().parents[2] / "contracts" /
                        "handoff_envelope.v1.schema.json").read_text(encoding="utf-8"))


def _fallback_output():
    return {"error": "pipeline failed closed"}


def _envelope(rid, rtype, version, status, reasons, route, masked, categories,
              rule_info, model_info, output, today):
    reasons = [str(reason) for reason in reasons]
    result = sanitize({"contract_version": CONTRACT_VERSION, "request_id": rid,
        "request_type": rtype, "plugin_version": version, "status": status,
        "handoff_reasons": list(dict.fromkeys(reasons)), "route": route or "forsta_linjen",
        "masked_text": masked, "masked_categories": categories, "rule": rule_info,
        "model": model_info, "output": output}, today)
    if validate(result, _ENVELOPE):
        # Keep the contract valid even if an untrusted hook returned malformed values.
        result.update(request_id=str(rid) or "unknown", request_type=str(rtype) or "unknown",
                      plugin_version=str(version or "unknown"), status=HANDOFF,
                      handoff_reasons=[R_PLUGIN],
                      route="forsta_linjen", masked_text=str(masked or ""),
                      masked_categories=[str(x) for x in categories if isinstance(x, str)],
                      rule={}, model={"adapter": "unknown", "status": "error"},
                      output=_fallback_output())
        result = sanitize(result, today)
    if validate(result, _ENVELOPE):
        raise RuntimeError("pipeline-owned handoff envelope is invalid")
    return result


def run(request: dict, adapter: ModelAdapter | None = None, audit: AuditLog | None = None,
        today: date | None = None) -> dict:
    # Establish safe identifiers/text before invoking any extension point.
    request = request if isinstance(request, dict) else {}
    raw = request.get("text") if isinstance(request.get("text"), str) else ""
    rtype = request.get("type", "support_ticket")
    rtype = rtype if isinstance(rtype, str) and rtype else "support_ticket"
    rid = str(request.get("id") or uuid.uuid4())
    masked, categories = mask_text(raw, today)
    audit = audit if audit is not None else AuditLog()
    adapter = adapter if adapter is not None else NoneAdapter()
    reasons = []
    if not masked.strip(): reasons.append(R_EMPTY)
    if "personnummer" in categories or "identifierare" in categories:
        reasons.append(R_PATIENT_DATA)
    elif find_unverified_personnummer_shapes(raw, today):
        # Luhn-invalid shape in patient/journal context: do not mask (demo gap), still hand off.
        reasons.append(R_PATIENT_DATA)
    audit.write("received", rid, request_type=rtype, input_sha256_16=text_hash(raw),
                masked_categories=categories)
    plugin = None
    version = "unknown"
    route = "forsta_linjen"
    rule_info, output = {}, _fallback_output()
    model_info = {"adapter": "unknown", "status": "skipped"}
    try:
        registry.load_builtin()
        plugin = registry.get(rtype)
        version = plugin.version
        rule = plugin.rules(masked)
        rule_info = {"label": rule.label, "confidence": rule.confidence, "hits": rule.hits}
        route = rule.route
        reasons.extend(rule.forced_handoff)
        audit.write("rules", rid, label=rule.label, confidence=rule.confidence,
                    hits=rule.hits, route=rule.route, forced_handoff=rule.forced_handoff)
        task = plugin.model_task(masked, rule) if masked.strip() else None
        model_out = None
        model_info = {"adapter": str(getattr(adapter, "name", "unknown")), "status": "skipped"}
        if task is not None:
            safe_prompt, _ = mask_text(task.prompt, today)
            if safe_prompt != task.prompt:
                reasons.append(R_PROMPT)
                model_info["status"] = "unsafe_prompt"
                audit.write("model", rid, task=task.name, adapter=model_info["adapter"],
                            status="unsafe_prompt")
            else:
                try:
                    reply = adapter.complete(task.prompt)
                except Exception:
                    reply = None
                    model_info["status"] = "adapter_error"
                    reasons.append(R_ADAPTER)
                if model_info["status"] != "adapter_error":
                    parsed = parse_json(reply)
                    if reply is None:
                        model_info["status"] = "abstain"; reasons.append(R_ABSTAIN)
                    elif parsed is None or validate(parsed, task.output_schema):
                        model_info["status"] = "invalid_schema"; reasons.append(R_INVALID)
                    else:
                        model_info["status"] = "ok"
                        model_out = sanitize(parsed, today)
                audit.write("model", rid, task=task.name, adapter=model_info["adapter"],
                            status=model_info["status"])
        # All model-derived strings are masked again before plugin output construction.
        output = sanitize(plugin.build_output(masked, rule, model_out), today)
        errors = validate(output, plugin.output_schema)
        if errors:
            audit.write("output_invalid", rid, errors=errors)
            reasons.append(R_INVALID)
            output = _fallback_output()
        conf = output.get("confidence", rule.confidence) if isinstance(output, dict) else 0.0
        if isinstance(conf, (int, float)) and conf < plugin.confidence_threshold:
            reasons.append(R_LOW_CONF)
        if not errors:
            reasons.extend(plugin.handoff_reasons(output, rule))
        if not isinstance(output, dict):
            raise TypeError("plugin output must be an object")
        route = output.get("route") or route
    except Exception:
        reasons.append(R_PLUGIN)
        output = _fallback_output()
        model_info = {"adapter": str(getattr(adapter, "name", "unknown")), "status": "plugin_error"}
        audit.write("extension_error", rid, reason=R_PLUGIN)
    status = HANDOFF if reasons else AWAITING_APPROVAL
    result = _envelope(rid, rtype, version, status, reasons, route, masked, categories,
                       rule_info, model_info, output, today)
    audit.write("decided", rid, status=result["status"],
                handoff_reasons=result["handoff_reasons"], route=result["route"])
    return result
