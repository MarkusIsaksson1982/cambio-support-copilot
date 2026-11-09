import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "ports/fixtures"
SCHEMAS = ROOT / "ports/schemas"


def _schema(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validate(instance, schema_name):
    schema = _schema(schema_name)
    try:
        import jsonschema
    except ImportError:
        from copilot.core.schema import validate
        if "$ref" in schema:
            schema = json.loads((SCHEMAS / schema["$ref"]).resolve().read_text(encoding="utf-8"))
        assert validate(instance, schema) == []
    else:
        resolver = jsonschema.RefResolver(base_uri=SCHEMAS.as_uri() + "/", referrer=schema)
        jsonschema.Draft202012Validator(schema, resolver=resolver).validate(instance)


def test_shared_fixtures_validate_against_ports_schemas():
    _validate(json.loads((FIXTURES / "request.json").read_text()), "request.v1.schema.json")
    _validate(json.loads((FIXTURES / "masked_span.json").read_text()), "masked_span.v1.schema.json")
    _validate(json.loads((FIXTURES / "handoff_envelope.json").read_text()), "handoff_envelope.v1.schema.json")
    events = json.loads((FIXTURES / "audit_events.json").read_text())
    for event in events:
        _validate(event, "audit_event.v1.schema.json")
    _validate(json.loads((FIXTURES / "incident_report.json").read_text()), "incident_report.v1.schema.json")
