"""Tests for projection math — Phase 6."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.models import Payslip, Profile, Target
from backend.projection import (
    DEPOSIT_FRACTION,
    HEADROOM_BAND,
    NIBUD_ANNUAL_FACTOR,
    compute_projection,
    deposit_target,
    headroom_range,
    monthly_savings_rate,
)

REF_DATE = datetime(2026, 4, 25, tzinfo=timezone.utc)


@pytest.fixture
def tim_transactions() -> list[dict]:
    path = Path(__file__).parent.parent / "backend" / "mocks" / "transactions.json"
    with path.open() as f:
        return json.load(f)["transactions"]


@pytest.fixture
def tim_buckets() -> list[dict]:
    path = Path(__file__).parent.parent / "backend" / "mocks" / "transactions.json"
    with path.open() as f:
        return json.load(f)["buckets"]


@pytest.fixture
def tim_profile() -> Profile:
    return Profile(
        user_id="u_demo",
        payslip=Payslip(
            gross_monthly_eur=4850.0,
            net_monthly_eur=3520.0,
            confidence="high",
        ),
        target=Target(funda_url="https://funda.nl/test", price_eur=425_000),
    )


# ── deposit_target ──────────────────────────────────────────────


def test_deposit_target_basic():
    assert deposit_target(425_000) == pytest.approx(59_500.0)


def test_deposit_target_zero():
    assert deposit_target(0) == 0.0


def test_deposit_target_matches_fraction():
    price = 600_000
    assert deposit_target(price) == pytest.approx(price * DEPOSIT_FRACTION)


# ── monthly_savings_rate ────────────────────────────────────────


def test_savings_rate_tim(tim_transactions):
    rate = monthly_savings_rate(tim_transactions, reference_date=REF_DATE)
    assert rate == pytest.approx(1450.0)


def test_savings_rate_empty():
    assert monthly_savings_rate([], reference_date=REF_DATE) == 0.0


def test_savings_rate_no_savings_category():
    txns = [
        {"date": "2026-04-01", "amount_eur": 4000.0, "category": "income"},
        {"date": "2026-04-05", "amount_eur": -1200.0, "category": "rent"},
    ]
    assert monthly_savings_rate(txns, reference_date=REF_DATE) == 0.0


def test_savings_rate_outside_window():
    txns = [
        {"date": "2025-01-01", "amount_eur": 1000.0, "category": "savings"},
    ]
    rate = monthly_savings_rate(txns, window_days=30, reference_date=REF_DATE)
    assert rate == 0.0


def test_savings_rate_single_month():
    txns = [
        {"date": "2026-04-01", "amount_eur": 500.0, "category": "savings"},
        {"date": "2026-04-15", "amount_eur": 300.0, "category": "savings"},
    ]
    rate = monthly_savings_rate(txns, reference_date=REF_DATE)
    assert rate == pytest.approx(800.0)


# ── headroom_range ──────────────────────────────────────────────


def test_headroom_range_tim():
    low, high = headroom_range(4850.0)
    gross_annual = 4850.0 * 12
    centre = gross_annual * NIBUD_ANNUAL_FACTOR
    assert low == int(centre * (1 - HEADROOM_BAND))
    assert high == int(centre * (1 + HEADROOM_BAND))


def test_headroom_range_zero():
    assert headroom_range(0) == (0, 0)


def test_headroom_range_ordering():
    low, high = headroom_range(5000.0)
    assert low < high


def test_headroom_range_realistic_band():
    low, high = headroom_range(4850.0)
    assert 200_000 < low < high < 500_000


# ── compute_projection ─────────────────────────────────────────


def test_projection_tim_full(tim_profile, tim_transactions, tim_buckets):
    proj = compute_projection(
        tim_profile, tim_transactions, tim_buckets, reference_date=REF_DATE
    )
    assert proj.savings_now_eur == 34_000.0
    assert proj.deposit_target_eur == 55_000.0
    assert proj.gap_eur == 21_000.0
    assert proj.monthly_savings_eur == pytest.approx(1450.0)
    assert proj.months_to_goal == 15  # ceil(21000 / 1450)
    assert isinstance(proj.headroom_range_eur, tuple)
    assert proj.headroom_range_eur[0] < proj.headroom_range_eur[1]
    assert proj.computed_at > 0


def test_projection_no_bucket(tim_profile):
    proj = compute_projection(
        tim_profile, [], [], reference_date=REF_DATE
    )
    assert proj.deposit_target_eur == pytest.approx(59_500.0)
    assert proj.savings_now_eur == 0.0
    assert proj.gap_eur == pytest.approx(59_500.0)


def test_projection_zero_savings_rate(tim_profile, tim_buckets):
    proj = compute_projection(
        tim_profile, [], tim_buckets, reference_date=REF_DATE
    )
    assert proj.months_to_goal == 0


def test_projection_already_at_goal():
    profile = Profile(
        user_id="u_demo",
        payslip=Payslip(gross_monthly_eur=5000.0, confidence="high"),
        target=Target(funda_url="https://funda.nl/x", price_eur=300_000),
    )
    buckets = [
        {"id": "b1", "name": "House", "balance_eur": 60_000.0, "goal_eur": 50_000.0},
    ]
    proj = compute_projection(profile, [], buckets, reference_date=REF_DATE)
    assert proj.gap_eur == 0.0
    assert proj.months_to_goal == 0


def test_projection_no_payslip():
    profile = Profile(
        user_id="u_demo",
        target=Target(funda_url="https://funda.nl/x", price_eur=300_000),
    )
    proj = compute_projection(profile, [], [], reference_date=REF_DATE)
    assert proj.headroom_range_eur == (0, 0)
