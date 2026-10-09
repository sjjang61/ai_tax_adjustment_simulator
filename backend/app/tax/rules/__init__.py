"""귀속연도별 규칙 레지스트리."""

from app.tax.rules import y2025, y2026
from app.tax.rules.base import TaxRules

_REGISTRY: dict[int, TaxRules] = {
    y2025.RULES.tax_year: y2025.RULES,
    y2026.RULES.tax_year: y2026.RULES,
}

SUPPORTED_TAX_YEARS: tuple[int, ...] = tuple(sorted(_REGISTRY))


class UnsupportedTaxYearError(LookupError):
    def __init__(self, tax_year: int) -> None:
        super().__init__(f"지원하지 않는 귀속연도입니다: {tax_year}")
        self.tax_year = tax_year


def get_rules(tax_year: int) -> TaxRules:
    try:
        return _REGISTRY[tax_year]
    except KeyError:
        raise UnsupportedTaxYearError(tax_year) from None


__all__ = ["SUPPORTED_TAX_YEARS", "TaxRules", "UnsupportedTaxYearError", "get_rules"]
