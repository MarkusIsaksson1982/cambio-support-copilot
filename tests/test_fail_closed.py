from datetime import date

import pytest

from copilot.core.adapters import FakeAdapter
from copilot.core.audit import AuditLog
from copilot.core import plugin as registry
from copilot.core.pipeline import HANDOFF, run
from copilot.core.schema import validate
import json
from pathlib import Path


ENVELOPE = json.loads((Path(__file__).resolve().parents[1] / "contracts" /
                       "handoff_envelope.v1.schema.json").read_text())


class BrokenPlugin:
    name = "broken_test"
    version = "x"
    confidence_threshold = 0
    output_schema = {"type": "object"}

    def __init__(self, point): self.point = point
    def _fail(self, point):
        if self.point == point: raise RuntimeError("raw secret 811218-9876")
    def rules(self, text):
        self._fail("rules")
        from copilot.core.plugin import RuleResult
        return RuleResult(None)
    def model_task(self, text, rule):
        self._fail("model_task")
        from copilot.core.plugin import ModelTask
        prompt = "Text: " + ("811218-9876" if self.point == "prompt" else text)
        return ModelTask("task", prompt, {"type": "object"})
    def build_output(self, text, rule, output):
        self._fail("build_output")
        return {"reply": output.get("rationale", "") if output else ""}
    def handoff_reasons(self, output, rule):
        self._fail("handoff_reasons")
        return []


@pytest.mark.parametrize("point", ["rules", "model_task", "build_output", "handoff_reasons"])
def test_plugin_hook_exception_fails_closed_and_is_audited(monkeypatch, point):
    plugin = BrokenPlugin(point)
    monkeypatch.setattr(registry, "load_builtin", lambda: None)
    monkeypatch.setattr(registry, "get", lambda _: plugin)
    audit = AuditLog()
    result = run({"type": "broken_test", "text": "allmänt ärende"}, FakeAdapter(), audit,
                 today=date(2024, 1, 1))
    assert result["status"] == HANDOFF
    assert "plugin_error" in result["handoff_reasons"]
    assert validate(result, ENVELOPE) == []
    assert any(e["event"] == "decided" for e in audit.events)
    assert "811218-9876" not in repr(result)
    assert "raw secret" not in repr(audit.events)


def test_adapter_exception_fails_closed_and_is_audited(monkeypatch):
    plugin = BrokenPlugin("none")
    monkeypatch.setattr(registry, "load_builtin", lambda: None)
    monkeypatch.setattr(registry, "get", lambda _: plugin)

    class BadAdapter:
        name = "bad"
        def complete(self, prompt): raise RuntimeError("raw adapter response 811218-9876")

    audit = AuditLog()
    result = run({"type": "broken_test", "text": "ärendet"}, BadAdapter(), audit)
    assert result["status"] == HANDOFF
    assert "adapter_error" in result["handoff_reasons"]
    assert result["model"]["status"] == "adapter_error"
    assert validate(result, ENVELOPE) == []
    assert any(e["event"] == "decided" for e in audit.events)
    assert "811218-9876" not in repr(audit.events)


def test_unmasked_personnummer_in_prompt_aborts_before_adapter(monkeypatch):
    plugin = BrokenPlugin("prompt")
    monkeypatch.setattr(registry, "load_builtin", lambda: None)
    monkeypatch.setattr(registry, "get", lambda _: plugin)
    adapter = FakeAdapter()
    result = run({"type": "broken_test", "text": "ärendet"}, adapter)
    assert not hasattr(adapter, "last_prompt")
    assert result["status"] == HANDOFF
    assert "unsafe_prompt" in result["handoff_reasons"]
    assert validate(result, ENVELOPE) == []


def test_model_output_is_remasked_before_plugin_uses_it(monkeypatch):
    plugin = BrokenPlugin("none")
    captured = []
    original = plugin.build_output
    plugin.build_output = lambda text, rule, output: (captured.append(output) or original(text, rule, output))
    monkeypatch.setattr(registry, "load_builtin", lambda: None)
    monkeypatch.setattr(registry, "get", lambda _: plugin)
    run({"type": "broken_test", "text": "ärendet"},
        FakeAdapter('{"rationale":"personnummer 811218-9876"}'))
    assert captured[0]["rationale"] != "personnummer 811218-9876"
