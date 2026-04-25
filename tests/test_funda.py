"""Tests for backend/funda.py — JSON-LD parser, regex fallback, fetch, and orchestrator."""

from pathlib import Path

import pytest

from backend.funda import (
    fetch_funda,
    parse_funda,
    parse_funda_jsonld,
    regex_price_fallback,
)

FIXTURE_HTML = (
    Path(__file__).parent.parent
    / "backend"
    / "mocks"
    / "funda_listings"
    / "default.html"
).read_text(encoding="utf-8")

STEVINSTRAAT_HTML = (
    Path(__file__).parent / "html_fixture" / "stevinstraat.html"
).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# parse_funda_jsonld
# ---------------------------------------------------------------------------


def test_jsonld_extracts_price():
    result = parse_funda_jsonld(FIXTURE_HTML)
    assert result is not None
    assert result["price_eur"] == 425000


def test_jsonld_extracts_address():
    result = parse_funda_jsonld(FIXTURE_HTML)
    assert result is not None
    assert result["address"] == "Oudegracht 123, Utrecht"


def test_jsonld_extracts_size():
    result = parse_funda_jsonld(FIXTURE_HTML)
    assert result is not None
    assert result["size_m2"] == 85


def test_jsonld_extracts_year_built():
    result = parse_funda_jsonld(FIXTURE_HTML)
    assert result is not None
    assert result["year_built"] == 1920


def test_jsonld_returns_none_for_html_without_jsonld():
    plain_html = "<html><body><p>Geen JSON-LD hier.</p></body></html>"
    assert parse_funda_jsonld(plain_html) is None


def test_jsonld_returns_none_for_jsonld_without_price():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Residence", "name": "Test", "offers": {}}
    </script>
    </head></html>
    """
    assert parse_funda_jsonld(html) is None


def test_jsonld_ignores_unrelated_schema_types():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Organization", "name": "funda", "offers": {"price": 999000}}
    </script>
    </head></html>
    """
    assert parse_funda_jsonld(html) is None


# ---------------------------------------------------------------------------
# regex_price_fallback
# ---------------------------------------------------------------------------


def test_regex_extracts_price_from_fixture():
    # Fixture contains "€ 425.000 k.k." — should return 425000
    result = regex_price_fallback(FIXTURE_HTML)
    assert result == 425000


def test_regex_extracts_dutch_formatted_price():
    html = "<p>Vraagprijs: € 325.000 k.k.</p>"
    assert regex_price_fallback(html) == 325000


def test_regex_returns_none_for_html_with_no_euro_amounts():
    html = "<p>No prices here.</p>"
    assert regex_price_fallback(html) is None


def test_regex_skips_amounts_below_50000():
    # VvE contribution of €150 should be skipped; no house price present
    html = "<p>VvE bijdrage € 150 per maand.</p>"
    assert regex_price_fallback(html) is None


def test_regex_skips_small_and_returns_large():
    # Small amount first, then real price — should return the real price
    html = "<p>VvE € 150 per maand. Vraagprijs € 450.000 k.k.</p>"
    assert regex_price_fallback(html) == 450000


# ---------------------------------------------------------------------------
# fetch_funda (fixture mode — default in settings)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_funda_fixture_returns_html():
    html = await fetch_funda("https://www.funda.nl/koop/utrecht/appartement-12345678-oudegracht-123/")
    assert "<html" in html
    assert "Oudegracht" in html


@pytest.mark.asyncio
async def test_fetch_funda_unknown_slug_falls_back_to_default():
    # A slug with no matching file falls back to default.html
    html = await fetch_funda("https://www.funda.nl/koop/amsterdam/nonexistent-slug/")
    assert "Oudegracht" in html


# ---------------------------------------------------------------------------
# parse_funda (end-to-end, fixture mode — JSON-LD succeeds, no LLM call)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_funda_returns_dict_with_price():
    result = await parse_funda("https://www.funda.nl/koop/utrecht/appartement-12345678-oudegracht-123/")
    assert isinstance(result, dict)
    assert result["price_eur"] == 425000


@pytest.mark.asyncio
async def test_parse_funda_returns_full_fields():
    result = await parse_funda("https://www.funda.nl/koop/utrecht/appartement-12345678-oudegracht-123/")
    assert result["address"] == "Oudegracht 123, Utrecht"
    assert result["size_m2"] == 85
    assert result["year_built"] == 1920


# ---------------------------------------------------------------------------
# Real Funda listing HTML (Stevinstraat 51, Eindhoven — saved from browser)
# ---------------------------------------------------------------------------


def test_jsonld_real_listing_extracts_price():
    result = parse_funda_jsonld(STEVINSTRAAT_HTML)
    assert result is not None
    assert result["price_eur"] == 475000


def test_jsonld_real_listing_extracts_address():
    result = parse_funda_jsonld(STEVINSTRAAT_HTML)
    assert result is not None
    assert result["address"] == "Stevinstraat 51, Eindhoven"


def test_regex_real_listing_extracts_price():
    assert regex_price_fallback(STEVINSTRAAT_HTML) == 475000


# ---------------------------------------------------------------------------
# Live Playwright fetch (requires Chrome + network — skip in CI)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_parse_funda_live_fetch(monkeypatch):
    """End-to-end: Playwright fetches a real Funda page and parses it."""
    monkeypatch.setattr("backend.funda.settings.funda_mode", "live")
    result = await parse_funda(
        "https://www.funda.nl/detail/koop/eindhoven/huis-stevinstraat-51/43322936/",
    )
    assert result["price_eur"] == 475000
    assert result["address"] == "Stevinstraat 51, Eindhoven"
