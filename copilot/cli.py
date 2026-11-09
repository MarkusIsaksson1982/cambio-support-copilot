"""CLI: JSON in, JSON out - the chaining contract for separate projects.

  echo '{"type":"support_ticket","text":"..."}' | python -m copilot run --adapter fake
  python -m copilot run --adapter none < request.json > envelope.json
  python -m copilot validate-envelope < envelope.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from copilot.chain import validate_envelope
from copilot.core import adapters, pipeline
from copilot.core.audit import AuditLog


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="copilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--adapter", default="none", choices=["none", "fake", "local", "opencode"])
    r.add_argument("--audit", default=None, help="append audit JSONL here")
    sub.add_parser("validate-envelope")
    sub.add_parser("incident-from-envelope")
    e = sub.add_parser("eval")
    e.add_argument("--runs", type=int, default=3)
    e.add_argument("--out", default=None, help="write the markdown report here")
    a = ap.parse_args(argv)
    if a.cmd == "eval":
        from copilot.eval.pack import evaluate, render_markdown
        summary = evaluate(runs=a.runs)
        text = render_markdown(summary)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0 if not summary["repeat_mismatches"] else 1
    data = json.load(sys.stdin)
    if a.cmd == "run":
        out = pipeline.run(data, adapters.make(a.adapter), AuditLog(a.audit))
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    if a.cmd == "incident-from-envelope":
        from copilot.chain import incident_from_envelope
        print(json.dumps(incident_from_envelope(data), ensure_ascii=False, indent=2))
        return 0
    errs = validate_envelope(data)
    print(json.dumps({"valid": not errs, "errors": errs}, ensure_ascii=False))
    return 1 if errs else 0
