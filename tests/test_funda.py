"""Tests for backend/funda.py and the /onboard/parse-funda endpoint."""

import asyncio
from pathlib import Path

import pytest

from backend.funda import _extract_jsonld, parse_funda, regex_price_fallback

# ---------------------------------------------------------------------------
# Minimal HTML snippets used across tests
# ---------------------------------------------------------------------------

_JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Residence",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Teststraat 1",
    "addressLocality": "Amsterdam"
  },
  "offers": {"@type": "Offer", "price": 350000, "priceCurrency": "EUR"},
  "floorSize": {"@type": "QuantitativeValue", "value": 65, "unitCode": "MTK"},
  "yearBuilt": 2001
}
</script>
</head><body><p>&euro; 350.000</p></body></html>
"""

_NO_JSONLD_HTML = """
<html><body>
<p>Vraagprijs &euro; 600.000 k.k.</p>
<p>Adres: Wilhelminapark 5, Utrecht</p>
</body></html>
"""

_NO_PRICE_HTML = "<html><body><p>Geen informatie beschikbaar.</p></body></html>"


# ---------------------------------------------------------------------------
# JSON-LD extraction
# ---------------------------------------------------------------------------


def test_jsonld_extracts_price():
    result = _extract_jsonld(_JSONLD_HTML)
    assert result is not None
    assert result["price_eur"] == 350_000.0


def test_jsonld_extracts_address():
    result = _extract_jsonld(_JSONLD_HTML)
    assert result["address"] == "Teststraat 1, Amsterdam"


def test_jsonld_extracts_size_and_year():
    result = _extract_jsonld(_JSONLD_HTML)
    assert result["size_m2"] == 65.0
    assert result["year_built"] == 2001


def test_jsonld_returns_none_when_absent():
    result = _extract_jsonld(_NO_JSONLD_HTML)
    assert result is None


# ---------------------------------------------------------------------------
# Regex price fallback
# ---------------------------------------------------------------------------


def test_regex_price_finds_dutch_format():
    # Dutch: 600.000 (dot as thousands separator)
    assert regex_price_fallback(_NO_JSONLD_HTML) == 600_000


def test_regex_price_returns_none_when_no_match():
    assert regex_price_fallback(_NO_PRICE_HTML) is None


def test_regex_price_handles_plain_format():
    html = "<p>€ 425000</p>"
    assert regex_price_fallback(html) == 425_000


# ---------------------------------------------------------------------------
# parse_funda (async) — tests the dispatch logic
# ---------------------------------------------------------------------------


def test_parse_funda_uses_jsonld_path():
    result = asyncio.run(parse_funda(_JSONLD_HTML))
    assert result["price_eur"] == 350_000.0
    assert result["address"] == "Teststraat 1, Amsterdam"


def test_parse_funda_falls_back_to_regex_when_no_jsonld_and_no_api_key(monkeypatch):
    """With no API key the LLM path is skipped; regex must still extract price."""
    monkeypatch.setattr("backend.funda.settings.anthropic_api_key", "")
    result = asyncio.run(parse_funda(_NO_JSONLD_HTML))
    assert result["price_eur"] == 600_000.0


def test_parse_funda_all_none_when_nothing_found(monkeypatch):
    monkeypatch.setattr("backend.funda.settings.anthropic_api_key", "")
    result = asyncio.run(parse_funda(_NO_PRICE_HTML))
    assert result["price_eur"] is None


# ---------------------------------------------------------------------------
# Demo fixture file integrity
# ---------------------------------------------------------------------------


def test_demo_fixture_file_exists():
    fixture = Path(__file__).parent.parent / "backend" / "mocks" / "funda_listings" / "demo_425k.html"
    assert fixture.exists(), "Demo fixture file missing"


def test_demo_fixture_jsonld_parseable():
    fixture = Path(__file__).parent.parent / "backend" / "mocks" / "funda_listings" / "demo_425k.html"
    html = fixture.read_text(encoding="utf-8")
    result = _extract_jsonld(html)
    assert result is not None
    assert result["price_eur"] == 425_000.0
    assert "Utrecht" in result["address"]


# ---------------------------------------------------------------------------
# Route: POST /onboard/parse-funda  (fixture mode, no network)
# ---------------------------------------------------------------------------


def test_parse_funda_endpoint_fixture_mode(client, monkeypatch):
    """End-to-end route test using fixture mode (no network or LLM calls)."""
    monkeypatch.setattr("backend.funda.settings.funda_mode", "fixture")
    resp = client.post(
        "/onboard/parse-funda",
        json={"funda_url": "https://www.funda.nl/koop/utrecht/huis-123-kanaalstraat/"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price_eur"] == 425_000.0
    assert body["address"] is not None
    assert body["fetched_at"] > 0


def test_parse_funda_endpoint_returns_null_price_gracefully(client, monkeypatch):
    """Route must return 200 even when price extraction fails."""
    monkeypatch.setattr("backend.funda.settings.funda_mode", "fixture")
    monkeypatch.setattr("backend.funda.settings.anthropic_api_key", "")

    # Patch fetch_funda to return HTML with no parseable price.
    async def _empty_html(_url: str) -> str:
        return "<html><body><p>Geen informatie.</p></body></html>"

    monkeypatch.setattr("backend.funda.fetch_funda", _empty_html)

    resp = client.post(
        "/onboard/parse-funda",
        json={"funda_url": "https://www.funda.nl/koop/utrecht/huis-999/"},
    )
    assert resp.status_code == 200
    assert resp.json()["price_eur"] is None
