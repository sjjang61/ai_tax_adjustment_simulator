"""구간별 차등 공제율 계산 유틸리티."""

from collections.abc import Sequence
from decimal import Decimal

from app.tax.money import format_percent, truncate_won
from app.tax.rules.base import RateTier


def tiered_amount(amount: int, tiers: Sequence[RateTier], start: int = 0) -> int:
    """``start`` 초과 ``amount`` 이하 금액에 구간별 비율을 누적 적용하고 원 미만을 절사한다.

    tiers의 ``upper``는 누적 금액 기준 경계값이며, 구간 경계값 정확히 같은 금액은 아래 구간에 속한다.
    절사는 구간 합산 후 1회만 적용한다(구간마다 절사하면 합계가 줄어드는 왜곡 방지).
    """
    total = Decimal(0)
    lower = start
    for tier in tiers:
        upper = amount if tier.upper is None else min(tier.upper, amount)
        if upper > lower:
            total += Decimal(upper - lower) * tier.rate
        if tier.upper is not None:
            lower = max(lower, tier.upper)
        if lower >= amount:
            break
    return truncate_won(total)


def describe_tiers(tiers: Sequence[RateTier]) -> str:
    """구간 공제율 설명 문구: "3,000만원 이하 100%, 5,000만원 이하 70%, 초과 30%"."""
    parts = []
    for tier in tiers:
        rate = format_percent(tier.rate)
        parts.append(f"{tier.upper:,}원 이하 {rate}" if tier.upper is not None else f"초과 {rate}")
    return ", ".join(parts)
