"""기본세율 적용 (소득세법 제55조 제1항)."""

from dataclasses import dataclass
from decimal import Decimal

from app.tax.money import truncate_won
from app.tax.rules.base import TaxRateBracket, TaxRules


@dataclass(frozen=True)
class CalculatedTax:
    amount: int
    bracket: TaxRateBracket


def calculate_tax(tax_base: int, rules: TaxRules) -> CalculatedTax:
    """산출세액 = 과세표준 × 세율 − 누진공제액 (원 미만 절사)."""
    for bracket in rules.tax_rate_brackets:
        if bracket.upper is None or tax_base <= bracket.upper:
            amount = truncate_won(Decimal(tax_base) * bracket.rate) - bracket.progressive_deduction
            return CalculatedTax(amount=max(amount, 0), bracket=bracket)
    raise AssertionError("tax brackets must be open-ended")  # pragma: no cover
