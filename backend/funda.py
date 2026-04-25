"""Funda URL fetching and property data extraction.

Parsing order:
1. JSON-LD (<script type="application/ld+json">) — fast, no tokens.
2. LLM fallback via Anthropic API with first ~8 k chars of visible text.
3. regex_price_fallback — last resort for price only.

Fixture mode (FUNDA_MODE=fixture): reads pre-cached HTML from
backend/mocks/funda_listings/ instead of hitting the network.
"""

import json
import logging
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from backend.config import settings
from backend.prompts import LLM_FUNDA

logger = logging.getLogger(__name__)

_MOCKS_DIR = Path(__file__).parent / "mocks" / "funda_listings"

# One fixture file serves as the default demo listing.
_DEFAULT_FIXTURE = "demo_425k.html"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fixture_path_for(url: str) -> Path:
    """Return a fixture file for the given URL.

    First checks whether any file in the mocks directory contains the URL's
    path slug as a substring.  Falls back to the default demo fixture.
    """
    from urllib.parse import urlparse
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    for candidate in _MOCKS_DIR.glob("*.html"):
        if slug and slug in candidate.stem:
            return candidate
    return _MOCKS_DIR / _DEFAULT_FIXTURE


async def fetch_funda(url: str) -> str:
    """Return the HTML of a Funda listing.

    In fixture mode reads from disk; otherwise performs a real HTTP request
    with browser-like headers over HTTP/2 with a 5 s timeout.
    """
    if settings.funda_mode == "fixture":
        fixture = _fixture_path_for(url)
        logger.debug("funda fixture mode: reading %s", fixture)
        return fixture.read_text(encoding="utf-8")

    async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=5.0) as client:
        response = await client.get(url, headers=_BROWSER_HEADERS)
        response.raise_for_status()
        return response.text


def _extract_jsonld(html: str) -> dict | None:
    """Return parsed JSON-LD data if it contains property fields, else None."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle both single objects and @graph arrays.
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            offers = obj.get("offers", {})
            if not offers:
                continue

            price = offers.get("price")
            address_obj = obj.get("address", {})
            street = address_obj.get("streetAddress")
            locality = address_obj.get("addressLocality")
            address = f"{street}, {locality}" if street and locality else street or locality

            floor = obj.get("floorSize", {})
            size = floor.get("value") if isinstance(floor, dict) else None
            year = obj.get("yearBuilt")

            if price is not None:
                return {
                    "price_eur": float(price),
                    "address": address,
                    "type": obj.get("@type"),
                    "size_m2": float(size) if size is not None else None,
                    "year_built": int(year) if year is not None else None,
                }
    return None


def _body_text(html: str, max_chars: int = 8000) -> str:
    """Return stripped visible body text, truncated to max_chars."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "head"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)[:max_chars]


def _llm_parse(html: str) -> dict | None:
    """Call the Anthropic API to extract property data from visible HTML text.

    Returns a validated dict on success, None on failure.
    """
    if not settings.anthropic_api_key:
        logger.warning("No anthropic_api_key configured; skipping LLM fallback")
        return None

    try:
        import anthropic  # local import keeps startup fast when not needed
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        text = _body_text(html)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": f"{LLM_FUNDA}\n\n{text}"}],
        )
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        # Validate shape: must be a dict with at least one recognisable field.
        if not isinstance(data, dict):
            return None
        return {
            "price_eur": float(data["price_eur"]) if data.get("price_eur") is not None else None,
            "address": data.get("address"),
            "type": data.get("type"),
            "size_m2": float(data["size_m2"]) if data.get("size_m2") is not None else None,
            "year_built": int(data["year_built"]) if data.get("year_built") is not None else None,
        }
    except Exception as exc:
        logger.warning("LLM funda fallback failed: %s", exc)
        return None


def regex_price_fallback(html: str) -> int | None:
    """Extract price from HTML using a regex pattern.

    Handles both the literal € symbol and the &euro; HTML entity.
    Strips Dutch thousand-separator dots (e.g. 425.000 → 425000).
    Returns an integer euro amount or None.
    """
    match = re.search(r"(?:€|&euro;)\s?([\d.]+)", html)
    if not match:
        return None
    raw = match.group(1).replace(".", "")
    try:
        return int(raw)
    except ValueError:
        return None


async def parse_funda(html: str) -> dict:
    """Extract property data from Funda HTML.

    Returns a dict with keys: price_eur, address, type, size_m2, year_built.
    price_eur is None if all extraction paths fail.
    """
    # Path 1: JSON-LD
    result = _extract_jsonld(html)
    if result is not None:
        logger.debug("funda: JSON-LD extraction succeeded (price=%.0f)", result.get("price_eur") or 0)
        return result

    # Path 2: LLM fallback
    logger.debug("funda: JSON-LD not found, trying LLM fallback")
    result = _llm_parse(html)
    if result is not None:
        logger.debug("funda: LLM extraction succeeded")
        return result

    # Path 3: regex price-only last resort
    logger.debug("funda: LLM fallback failed, using regex price fallback")
    price = regex_price_fallback(html)
    return {
        "price_eur": float(price) if price is not None else None,
        "address": None,
        "type": None,
        "size_m2": None,
        "year_built": None,
    }
