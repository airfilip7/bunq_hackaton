"""Onboarding routes mounted at /onboard."""

import time

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

import backend.funda as funda_module

router = APIRouter()


class ParseFundaRequest(BaseModel):
    funda_url: str


class ParseFundaResponse(BaseModel):
    funda_url: str
    price_eur: float | None
    address: str | None
    type: str | None
    size_m2: float | None
    year_built: int | None
    fetched_at: int


@router.post("/parse-funda", response_model=ParseFundaResponse)
async def parse_funda(request: ParseFundaRequest = Body(...)):
    """Fetch and parse a Funda listing URL.

    Returns structured property data. price_eur is null when all extraction
    paths fail (rare — manual entry is the fallback).
    """
    try:
        html = await funda_module.fetch_funda(request.funda_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch Funda URL: {exc}") from exc

    data = await funda_module.parse_funda(html)
    return ParseFundaResponse(
        funda_url=request.funda_url,
        fetched_at=int(time.time()),
        **data,
    )
