"""Minimal stdlib JSON-schema subset validator (ported from arende-triage)."""
from __future__ import annotations
import math
import re

TYPES = {"object": (dict,), "array": (list,), "string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,), "null": (type(None),)}

def validate(instance, schema, path: str = "$") -> list[str]:
    """Returnera en lista med fel; tom lista betyder giltigt."""
    expected = schema.get("type")
    if expected and not _type_ok(instance, expected):
        return ["{}: förväntade {}, fick {}".format(path, expected, type(instance).__name__)]
    fel = []
    if "enum" in schema and instance not in schema["enum"]:
        fel.append("{}: {!r} finns inte i {}".format(path, instance, schema["enum"]))
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            fel.append("{}: för kort (minLength {})".format(path, schema["minLength"]))
        if "pattern" in schema and not re.match(schema["pattern"], instance):
            fel.append("{}: {!r} matchar inte {}".format(path, instance, schema["pattern"]))
    if _is_num(instance):
        if not math.isfinite(instance):
            fel.append("{}: icke-finita tal (NaN/Infinity)".format(path))
        else:
            for key, op in (("minimum", "<"), ("maximum", ">")):
                if key in schema and (instance < schema[key] if op == "<" else instance > schema[key]):
                    fel.append("{}: {} {} {}".format(path, instance, op, schema[key]))
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        fel += ["{}: saknar '{}'".format(path, k) for k in schema.get("required", []) if k not in instance]
        if schema.get("additionalProperties") is False:
            fel += ["{}: okänt fält '{}'".format(path, k) for k in instance if k not in props]
        fel += [e for k, sub in props.items() if k in instance
                for e in validate(instance[k], sub, "{}.{}".format(path, k))]
    if isinstance(instance, list) and schema.get("items"):
        fel += ["{}: för få element".format(path) for _ in range(schema.get("minItems", 0) - len(instance))]
        fel += [e for i, item in enumerate(instance)
                for e in validate(item, schema["items"], "{}[{}]".format(path, i))]
    return fel


def _type_ok(value, expected: str) -> bool:
    """bool är inte ett tal i JSON - det är en egen typ."""
    return expected in TYPES and isinstance(value, TYPES[expected]) and not (
        isinstance(value, bool) and expected in ("integer", "number"))


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


