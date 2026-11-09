"""End-to-end: run tickets through the real pipeline with the local (Ollama) adapter.

Records every raw model reply so failures can be replayed offline as fixtures.
  python3 scripts/local_e2e.py qwen2.5:3b [tickets.json] > out.json
Synthetic data only. The model only ever sees masked text (pipeline guarantees it).
"""
import json, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from copilot.core import pipeline
from copilot.core.adapters import LocalAdapter
from copilot.core.audit import AuditLog


class Recording(LocalAdapter):
    def complete(self, prompt):
        t = time.time(); r = super().complete(prompt)
        self.calls.append({"prompt_len": len(prompt), "reply": r, "secs": round(time.time() - t, 2)})
        return r


def load(path):
    p = pathlib.Path(path)
    if p.suffix == ".jsonl":
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return [{"id": t["id"], "text": t["title"] + ". " + t["body"]} for t in json.loads(p.read_text())["tickets"]]


def main(model, path="data/support_tickets.jsonl"):
    rows = []
    for t in load(path):
        a = Recording(model=model, timeout=180); a.calls = []
        env = pipeline.run({"type": "support_ticket", "text": t["text"], "request_id": t["id"]}, a, AuditLog())
        rows.append({"id": t["id"], "expected_label": t.get("expected_label"), "status": env["status"],
                     "model_status": env["model"]["status"], "label": env["output"].get("label"),
                     "source": env["output"].get("source"), "handoff_reasons": env["handoff_reasons"],
                     "masked_text": env["masked_text"], "calls": a.calls})
    json.dump({"model": model, "rows": rows}, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
