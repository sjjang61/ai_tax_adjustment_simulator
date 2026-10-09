from decimal import Decimal

import pytest

from app.tax.money import apply_rate, clamp, format_percent, truncate_to_10_won, truncate_won
from app.tax.rules.base import RateTier
from app.tax.tiers import describe_tiers, tiered_amount


def test_truncate_won_drops_fraction_toward_zero() -> None:
    assert truncate_won(Decimal("1234.99")) == 1234
    assert truncate_won(Decimal("-1234.99")) == -1234


def test_apply_rate_truncates() -> None:
    assert apply_rate(333, Decimal("0.15")) == 49  # 49.95 → 49


@pytest.mark.parametrize(
    ("amount", "expected"), [(0, 0), (19, 10), (-19, -10), (123_456, 123_450), (-636_309, -636_300)]
)
def test_truncate_to_10_won(amount: int, expected: int) -> None:
    assert truncate_to_10_won(amount) == expected


def test_clamp() -> None:
    assert clamp(-1, 0) == 0
    assert clamp(5, 0, 3) == 3
    assert clamp(2, 0, 3) == 2
    assert clamp(10, 0) == 10


def test_format_percent() -> None:
    assert format_percent(Decimal("0.15")) == "15%"
    assert format_percent(Decimal("0.70")) == "70%"
    assert format_percent(Decimal("0.008")) == "0.8%"


TIERS = (
    RateTier(upper=30_000_000, rate=Decimal("1.00")),
    RateTier(upper=50_000_000, rate=Decimal("0.70")),
    RateTier(upper=None, rate=Decimal("0.30")),
)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, 0),
        (29_999_999, 29_999_999),
        (30_000_000, 30_000_000),
        (30_000_001, 30_000_000),  # 1원 × 70% = 0.7 → 절사
        (50_000_000, 44_000_000),
        (60_000_000, 47_000_000),
    ],
)
def test_tiered_amount_boundaries(amount: int, expected: int) -> None:
    assert tiered_amount(amount, TIERS) == expected


def test_tiered_amount_with_start() -> None:
    tiers = (RateTier(upper=1_000, rate=Decimal("0.1")), RateTier(upper=None, rate=Decimal("0.5")))
    assert tiered_amount(100, tiers, start=100) == 0
    assert tiered_amount(2_000, tiers, start=100) == 90 + 500
    assert tiered_amount(2_000, tiers, start=1_500) == 250


def test_describe_tiers() -> None:
    assert describe_tiers(TIERS) == "30,000,000원 이하 100%, 50,000,000원 이하 70%, 초과 30%"
