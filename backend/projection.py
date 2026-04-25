"""Projection math for bunq Nest — pure functions, no I/O."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from backend.models import Profile, Projection

# Nibud 2026 lending norms (approximate annual-income multiplier).
# Real norms vary by interest rate, household type, etc.
NIBUD_ANNUAL_FACTOR = 5.0

# Dutch home-buying cost fractions
EIGEN_INLEG_FRACTION = 0.10   # 10 % own contribution (recommended)
KOSTEN_KOPER_FRACTION = 0.04  # ~4 % buyer's costs (notary, transfer tax, etc.)
DEPOSIT_FRACTION = EIGEN_INLEG_FRACTION + KOSTEN_KOPER_FRACTION  # 14 %

# Headroom band: ± this fraction around the Nibud centre estimate
HEADROOM_BAND = 0.08


def deposit_target(price_eur: float) -> float:
    """Own funds needed: 10 % eigen inleg + 4 % kosten koper."""
    return price_eur * DEPOSIT_FRACTION


def monthly_savings_rate(
    transactions: list[dict],
    window_days: int = 180,
    reference_date: datetime | None = None,
) -> float:
    """Average monthly savings from *savings-category* transactions.

    Looks at actual transfers to savings buckets (category == "savings")
    within the window. Clips to 5th–95th percentile of monthly totals
    to trim outlier months.
    """
    now = reference_date or datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=window_days)

    recent = [
        t
        for t in transactions
        if (
            datetime.fromisoformat(t["date"]).replace(tzinfo=timezone.utc) >= cutoff
            and t.get("category") == "savings"
        )
    ]

    if not recent:
        return 0.0

    monthly: dict[str, float] = defaultdict(float)
    for t in recent:
        month_key = t["date"][:7]  # "2026-01"
        monthly[month_key] += abs(t["amount_eur"])

    values = sorted(monthly.values())
    n = len(values)

    if n < 3:
        return sum(values) / n

    lo = max(0, int(n * 0.05))
    hi = min(n, int(math.ceil(n * 0.95)))
    clipped = values[lo:hi] if lo < hi else values

    return sum(clipped) / len(clipped)


def headroom_range(gross_monthly_eur: float) -> tuple[int, int]:
    """Nibud-based borrowing-capacity range (low, high).

    Always a *range*, never a single figure — per Wft requirements.
    Attach "per Nibud norms" when displaying.
    """
    gross_annual = gross_monthly_eur * 12
    centre = gross_annual * NIBUD_ANNUAL_FACTOR
    low = int(centre * (1 - HEADROOM_BAND))
    high = int(centre * (1 + HEADROOM_BAND))
    return (low, high)


def compute_projection(
    profile: Profile,
    transactions: list[dict],
    buckets: list[dict],
    reference_date: datetime | None = None,
) -> Projection:
    """Assemble a full Projection from profile + bunq snapshot."""
    price_eur = profile.target.price_eur if profile.target else 0.0
    gross_monthly = (
        profile.payslip.gross_monthly_eur
        if profile.payslip and profile.payslip.gross_monthly_eur
        else 0.0
    )

    house_bucket = next(
        (b for b in buckets if b.get("name", "").lower() == "house"), None
    )
    savings_now = house_bucket["balance_eur"] if house_bucket else 0.0

    target_eur = (
        house_bucket["goal_eur"]
        if house_bucket and house_bucket.get("goal_eur")
        else deposit_target(price_eur)
    )

    gap = max(0.0, target_eur - savings_now)
    rate = monthly_savings_rate(transactions, reference_date=reference_date)
    months = math.ceil(gap / rate) if rate > 0 else 0
    hr = headroom_range(gross_monthly) if gross_monthly else (0, 0)

    now = reference_date or datetime.now(tz=timezone.utc)

    return Projection(
        savings_now_eur=savings_now,
        deposit_target_eur=target_eur,
        gap_eur=gap,
        monthly_savings_eur=round(rate, 2),
        months_to_goal=months,
        headroom_range_eur=hr,
        computed_at=int(now.timestamp() * 1000),
    )
