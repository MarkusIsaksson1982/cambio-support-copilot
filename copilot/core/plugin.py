"""Request-type plugin contract.

Every request type (support_ticket, incident_report, ...) implements RequestPlugin.
The pipeline owns the safety spine (mask -> rules -> one model step -> validate ->
handoff -> audit); a plugin only supplies the domain parts. A plugin can never
skip masking or the audit, and it can only ADD handoff reasons, never remove the
pipeline's own (patient data, invalid output, low confidence).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class RuleResult:
    """Outcome of the deterministic, rule-first step."""
    label: str | None              # None = rules undecided -> model step may propose
    confidence: float = 0.0
    hits: list[dict] = field(default_factory=list)
    route: str | None = None       # queue / team
    forced_handoff: list[str] = field(default_factory=list)  # reasons that always need a human


@dataclass
class ModelTask:
    """The ONE narrow model step a plugin may ask for."""
    name: str
    prompt: str                    # built from MASKED text only
    output_schema: dict


@runtime_checkable
class RequestPlugin(Protocol):
    name: str                      # request type, e.g. "support_ticket"
    version: str
    output_schema: dict            # schema of the plugin's final `output`
    confidence_threshold: float

    def rules(self, masked_text: str) -> RuleResult: ...

    def model_task(self, masked_text: str, rule: RuleResult) -> ModelTask | None: ...

    def build_output(self, masked_text: str, rule: RuleResult,
                     model_output: dict | None) -> dict: ...

    def handoff_reasons(self, output: dict, rule: RuleResult) -> list[str]: ...


_REGISTRY: dict[str, Any] = {}


def register(plugin) -> Any:
    if not isinstance(plugin, RequestPlugin):
        raise TypeError(f"{plugin!r} does not implement RequestPlugin")
    if plugin.name in _REGISTRY:
        raise ValueError(f"plugin {plugin.name!r} already registered")
    _REGISTRY[plugin.name] = plugin
    return plugin


def get(name: str):
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown request type {name!r}; known: {sorted(_REGISTRY)}") from None


def registered() -> list[str]:
    return sorted(_REGISTRY)


def load_builtin() -> None:
    """Import built-in plugins (idempotent)."""
    from copilot.plugins import support_ticket, incident_report  # noqa: F401
