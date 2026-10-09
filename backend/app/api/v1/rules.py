from fastapi import APIRouter, Request

from app.core.config import Settings
from app.core.errors import ERROR_RESPONSES
from app.schemas.simulation import RulesYears
from app.tax.rules import SUPPORTED_TAX_YEARS, TaxRules, get_rules

router = APIRouter(prefix="/rules", tags=["rules"], responses=ERROR_RESPONSES)


@router.get("", response_model=RulesYears, summary="지원 귀속연도 목록")
def list_rule_years(request: Request) -> RulesYears:
    settings: Settings = request.app.state.settings
    default = settings.default_tax_year
    if default not in SUPPORTED_TAX_YEARS:
        default = SUPPORTED_TAX_YEARS[-1]
    return RulesYears(supported_years=list(SUPPORTED_TAX_YEARS), default_tax_year=default)


@router.get("/{tax_year}", response_model=TaxRules, summary="귀속연도별 한도·공제율 메타데이터")
def read_rules(tax_year: int) -> TaxRules:
    return get_rules(tax_year)
