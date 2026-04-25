"""Funda property listing parser.

Three extraction tiers: JSON-LD (free) → LLM fallback → regex last resort.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from backend.anthropic_client import MODEL_VISION, client
from backend.config import settings
from backend.prompts import LLM_FUNDA

_FIXTURE_DIR = Path(__file__).parent / "mocks" / "funda_listings"
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


class FundaFetchError(Exception):
    pass


class FundaParseError(Exception):
    pass


async def fetch_funda(url: str) -> str:
    """Fetch Funda listing HTML.

    Returns raw HTML string. In fixture mode, reads from the local
    funda_listings directory instead of hitting the network.

    Live mode uses curl_cffi with Chrome TLS impersonation to bypass
    Cloudflare bot protection.
    """
    if settings.funda_mode == "fixture":
        # Derive fixture filename from URL path slug; fall back to default.
        path_slug = url.rstrip("/").split("/")[-1]
        candidate = _FIXTURE_DIR / f"{path_slug}.html"
        fixture = candidate if candidate.exists() else _FIXTURE_DIR / "default.html"
        return fixture.read_text(encoding="utf-8")

    async with AsyncSession(impersonate="chrome131") as session:
        response = await session.get(
            url,
            headers={
                "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            timeout=15,
        )

    if response.status_code != 200:
        raise FundaFetchError(f"Funda returned HTTP {response.status_code} for {url}")

    html = response.text

    if "Je bent bijna op de pagina" in html:
        raise FundaFetchError(f"Funda bot protection blocked request for {url}")

    return html


def parse_funda_jsonld(html: str) -> dict | None:
    """Extract property data from JSON-LD embedded in the page.

    Returns a dict with price_eur and optional fields, or None if no
    usable JSON-LD is found.
    """
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")

    candidates: list[dict] = []
    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        # JSON-LD may be a single object or a list
        if isinstance(data, list):
            candidates.extend(data)
        else:
            candidates.append(data)

    _PROPERTY_TYPES = {"Residence", "House", "Apartment", "RealEstateListing", "Huis", "Product"}

    for item in candidates:
        item_type = item.get("@type", "")
        # @type can be a string or a list (Funda uses e.g. ["Huis", "Product"])
        if isinstance(item_type, list):
            if not _PROPERTY_TYPES.intersection(item_type):
                continue
        elif item_type not in _PROPERTY_TYPES:
            continue
        offers = item.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        price = offers.get("price")
        if not price:
            spec = offers.get("priceSpecification", {})
            price = spec.get("price")

        if not price:
            continue

        address_obj = item.get("address", {})
        street = address_obj.get("streetAddress")
        locality = address_obj.get("addressLocality")
        address = None
        if street and locality:
            address = f"{street}, {locality}"
        elif street:
            address = street

        floor_size = item.get("floorSize", {})
        size_m2 = floor_size.get("value") if isinstance(floor_size, dict) else None

        return {
            "price_eur": int(price),
            "address": address,
            "type": item.get("propertyType") or item.get("additionalType"),
            "size_m2": int(size_m2) if size_m2 is not None else None,
            "year_built": item.get("yearBuilt"),
        }

    return None


async def parse_funda_llm(html: str) -> dict:
    """Extract property data via LLM on truncated body HTML.

    Raises FundaParseError if the model response cannot be parsed.
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text(separator=" ", strip=True)
    truncated = body[:8000]

    response = await client.messages.create(
        model=MODEL_VISION,
        max_tokens=512,
        messages=[
            {"role": "user", "content": f"{LLM_FUNDA}\n\n{truncated}"}
        ],
    )

    raw_text = response.content[0].text
    cleaned = _JSON_FENCE_RE.sub("", raw_text.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise FundaParseError(
            f"LLM response is not valid JSON: {exc}\nRaw: {raw_text}"
        ) from exc


def regex_price_fallback(html: str) -> int | None:
    """Extract the first plausible house price from raw HTML via regex.

    Handles Dutch formatting (450.000) and returns a plain int or None.
    """
    for match in re.finditer(r"€\s?([\d.]+)", html):
        raw = match.group(1).replace(".", "")
        try:
            value = int(raw)
        except ValueError:
            continue
        if value > 50000:
            return value
    return None


async def parse_funda(url: str) -> dict:
    """Parse a Funda listing URL and return structured property data.

    Tries three tiers in order:
    1. JSON-LD embedded in the page (free, fast).
    2. LLM extraction from truncated body text.
    3. Regex price fallback (price_eur only).
    """
    html = await fetch_funda(url)

    result = parse_funda_jsonld(html)
    if result and result.get("price_eur"):
        return result

    try:
        result = await parse_funda_llm(html)
        if result:
            return result
    except (FundaParseError, Exception):  # noqa: BLE001
        pass

    price = regex_price_fallback(html)
    return {
        "price_eur": price,
        "address": None,
        "type": None,
        "size_m2": None,
        "year_built": None,
    }
