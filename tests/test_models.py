import pytest
from pydantic import ValidationError

from backend.models import Payslip, Profile, Projection, Target, Turn


def test_payslip_defaults():
    p = Payslip()
    assert p.confidence == "low"
    assert p.gross_monthly_eur is None


def test_payslip_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        Payslip(confidence="invalid")


def test_profile_defaults():
    p = Profile(user_id="u1")
    assert p.schema_version == 1
    assert p.onboarded_at is None
    assert p.payslip is None


def test_target_requires_url_and_price():
    t = Target(funda_url="https://funda.nl/abc", price_eur=450_000)
    assert t.price_eur == 450_000


def test_projection_fields():
    p = Projection(
        savings_now_eur=34000,
        deposit_target_eur=55000,
        gap_eur=21000,
        monthly_savings_eur=1500,
        months_to_goal=14,
        headroom_range_eur=(350_000, 420_000),
        computed_at=1000,
    )
    assert p.gap_eur == 21000
    assert p.headroom_range_eur == (350_000, 420_000)


def test_turn_kind_validation():
    with pytest.raises(ValidationError):
        Turn(turn_id="t1", session_id="s1", ts_ms=1000, kind="invalid_kind")
