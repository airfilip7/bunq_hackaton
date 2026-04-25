"""Domain models for bunq Nest."""

from typing import Literal
from pydantic import BaseModel


class Payslip(BaseModel):
    gross_monthly_eur: float | None = None
    net_monthly_eur: float | None = None
    employer_name: str | None = None
    pay_period: str | None = None
    confidence: Literal["high", "medium", "low"] = "low"
    source_s3_key: str | None = None
    extracted_at: int | None = None


class Target(BaseModel):
    funda_url: str
    price_eur: float
    address: str | None = None
    type: str | None = None
    size_m2: float | None = None
    year_built: int | None = None
    fetched_at: int | None = None


class Projection(BaseModel):
    savings_now_eur: float
    deposit_target_eur: float
    gap_eur: float
    monthly_savings_eur: float
    months_to_goal: int
    headroom_range_eur: tuple[int, int]
    computed_at: int


class Profile(BaseModel):
    user_id: str
    email: str | None = None
    onboarded_at: int | None = None
    payslip: Payslip | None = None
    target: Target | None = None
    projection: Projection | None = None
    schema_version: int = 1


class Session(BaseModel):
    session_id: str
    user_id: str
    started_at: int
    last_active_at: int
    state: Literal["active", "closed"] = "active"


class Turn(BaseModel):
    turn_id: str
    session_id: str
    ts_ms: int
    kind: Literal["user_message", "assistant_message", "tool_result", "tool_approval"]
    content: str | None = None
    tool_uses: list[dict] | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    ok: bool | None = None
    result: dict | None = None
    decision: Literal["approve", "deny"] | None = None
    overrides: dict | None = None
    feedback: str | None = None
    hidden: bool = False


class PendingTool(BaseModel):
    tool_use_id: str
    session_id: str
    tool_name: str
    params: dict
    summary: str
    rationale: str
    risk_level: Literal["low", "medium", "high"]
    proposed_at: int


class BunqToken(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str | None = None
    expires_at: int
    scope: str = "read"
    rotated_at: int | None = None

    def __repr__(self) -> str:
        return (
            f"BunqToken(user_id={self.user_id!r}, "
            f"access_token='***REDACTED***', "
            f"expires_at={self.expires_at})"
        )
