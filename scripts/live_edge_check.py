"""Live check of the top edge cases against local Ollama models (synthetic data only).
  python3 scripts/live_edge_check.py qwen2.5:7b-instruct-q4 qwen2.5:3b
For each model: PII spans -> span gate; classification -> pipeline. Prints whether the gate held.
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from copilot.core import pipeline
from copilot.core.adapters import LocalAdapter, parse_json
from copilot.core.audit import AuditLog
from copilot.core.span_gate import check_spans

PII = ('Hitta ALLA personuppgifter i texten (fiktiva): personnamn, personnummer/samordningsnummer, '
       'telefon, e-post, patient-/ärende-id. Yrkesroller utan namn är INTE personuppgifter. Svara ENDAST JSON:\n'
       '{{"entities": [{{"text": exakt delsträng, "type": "namn|personnummer|telefon|epost|id"}}]}}\n\nText:\n"""{t}"""')
CASES = json.loads((pathlib.Path(__file__).resolve().parents[1] / "tests/fixtures/top_edge_cases.json").read_text())

for model in sys.argv[1:]:
    a = LocalAdapter(model=model, timeout=240)
    for c in CASES:
        if c["kind"] == "pii_span":
            raw = a.complete(PII.format(t=c["text"])); j = parse_json(raw) or {}
            g = check_spans(c["text"], j.get("entities", []))
            held = all(s in c["text"] for s in g["accepted"]) and (g["status"] == "handoff") == bool(g["rejected"])
            print(json.dumps({"model": model, "case": c["id"], "accepted": g["accepted"], "rejected": g["rejected"],
                              "status": g["status"], "gate_held": held}, ensure_ascii=False))
        else:
            env = pipeline.run({"type": "support_ticket", "text": c["text"]}, a, AuditLog())
            print(json.dumps({"model": model, "case": c["id"], "label": env["output"].get("label"),
                              "model_status": env["model"]["status"], "status": env["status"],
                              "reasons": env["handoff_reasons"], "gate_held": env["status"] != "awaiting_approval"}, ensure_ascii=False))
