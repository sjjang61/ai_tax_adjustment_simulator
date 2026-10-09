"""금액 계산 유틸리티.

모든 금액은 원 단위 ``int``로 다루고, 비율 곱셈은 ``Decimal``로 수행한 뒤 명시적 규칙으로 정수화한다.
``float``와 내장 ``round()``는 사용하지 않는다.
"""

from decimal import ROUND_DOWN, Decimal


def truncate_won(value: Decimal) -> int:
    """원 미만 절사(0 방향).

    근거: 국고금 관리법 제47조(국고금의 끝수 계산) 및 소득세 계산 실무상 각 공제·세액 산출 시
    원 미만 금액은 버린다.
    """
    return int(value.to_integral_value(rounding=ROUND_DOWN))


def apply_rate(amount: int, rate: Decimal) -> int:
    """금액 × 비율을 계산하고 원 미만을 절사한다."""
    return truncate_won(Decimal(amount) * rate)


def truncate_to_10_won(amount: int) -> int:
    """10원 미만 절사(0 방향, 환급액(음수)도 절대값 기준으로 버림).

    근거: 국고금 관리법 제47조 제1항 — 국고금의 수입 또는 지출 시 10원 미만의 끝수는 계산하지 않는다.
    차감징수(환급)세액 산정에 적용한다.
    """
    sign = -1 if amount < 0 else 1
    return sign * (abs(amount) // 10 * 10)


def clamp(value: int, lower: int, upper: int | None = None) -> int:
    """value를 [lower, upper] 범위로 제한한다. upper가 None이면 상한 없음."""
    if value < lower:
        return lower
    if upper is not None and value > upper:
        return upper
    return value


def format_percent(rate: Decimal) -> str:
    """Decimal("0.15") → "15%" (설명 문구 표시용)."""
    return f"{(rate * 100).normalize():f}%"
