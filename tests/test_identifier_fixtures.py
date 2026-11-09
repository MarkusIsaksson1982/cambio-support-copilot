"""Ported from arende-triage: masking fixtures (synthetic, Luhn-valid where they should be)."""
import json
from datetime import date
from pathlib import Path

import pytest

from copilot.core.masking import find_organisationsnummer, mask_text

FIX = json.loads((Path(__file__).resolve().parents[1] / "data" / "identifier_fixtures.json").read_text())
TODAY = date(2026, 10, 29)


@pytest.mark.parametrize("f", FIX, ids=[f["id"] for f in FIX])
def test_fixture(f):
    masked, cats = mask_text(f["text"], TODAY)
    assert masked == f["maskad"]
    assert cats == f["kategorier"]


def test_orgnr_luhn():
    assert find_organisationsnummer("559901-1235 och 559901-1234") == ["559901-1235"]
