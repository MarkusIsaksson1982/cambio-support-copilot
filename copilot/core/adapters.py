"""Model adapters. The pipeline only ever sends MASKED text through these.

- none:     no model; every model step abstains (rules + human only).
- fake:     deterministic, offline, for tests and the offline demo mode.
- local:    Ollama-compatible HTTP endpoint (default http://localhost:11434).
- opencode: `opencode run` subprocess (free hosted models), stdin closed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from typing import Callable, Protocol


class ModelAdapter(Protocol):
    name: str

    def complete(self, prompt: str) -> str | None: ...


class NoneAdapter:
    name = "none"

    def complete(self, prompt: str) -> str | None:
        return None


class FakeAdapter:
    """Deterministic adapter: a function of the prompt, or a fixed reply."""
    name = "fake"

    def __init__(self, reply: str | Callable[[str], str | None] | None = None):
        self._reply = reply

    def complete(self, prompt: str) -> str | None:
        self.last_prompt = prompt
        if callable(self._reply):
            return self._reply(prompt)
        if self._reply is not None:
            return self._reply
        return json.dumps({"label": "ovrigt", "confidence": 0.4,
                           "rationale": "fake adapter: ingen modell"})


class LocalAdapter:
    name = "local"

    def __init__(self, model: str = "qwen2.5:3b", url: str | None = None, timeout: float = 60):
        self.model, self.timeout = model, timeout
        self.url = url or os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def complete(self, prompt: str) -> str | None:
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False,
                           "format": "json"}).encode()
        req = urllib.request.Request(self.url + "/api/generate", body,
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())["response"]
        except Exception:
            return None


class OpenCodeAdapter:
    name = "opencode"

    def __init__(self, model: str = "opencode/mimo-v2.6-flash-free", timeout: float = 120):
        self.model, self.timeout = model, timeout

    def complete(self, prompt: str) -> str | None:
        try:
            p = subprocess.run(["opencode", "run", "-m", self.model, prompt],
                               stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, timeout=self.timeout)
        except Exception:
            return None
        return p.stdout if p.returncode == 0 else None


def make(name: str, **kw) -> ModelAdapter:
    return {"none": NoneAdapter, "fake": FakeAdapter, "local": LocalAdapter,
            "opencode": OpenCodeAdapter}[name](**kw)


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json(raw: str | None) -> dict | None:
    """Tolerant JSON extraction (a small subset of llm-json-fixer's repairs):
    code fences, prose around the object, trailing commas. Returns None if unrepairable."""
    if not raw or not isinstance(raw, str):
        return None
    m = _FENCE.search(raw)
    text = m.group(1) if m else raw
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    text = re.sub(r",\s*([}\]])", r"\1", text[start:end + 1])
    try:
        val = json.loads(text)
    except json.JSONDecodeError:
        return None
    return val if isinstance(val, dict) else None
