"""2026년 귀속 근로소득 연말정산 규칙.

``y2025.py``를 복사한 뒤 개정 사항만 수정했다.

⚠️ 미검증(verified=False): 작성 시점에 2026년 귀속 개정 세법의 국회 통과·시행 여부를 공식 자료로
확인하지 못했다. 결과에는 경고가 함께 표시된다.

2025년 귀속 대비 변경 내역
- 신용카드 등 소득공제 기본한도: 자녀 1명당 50만원(최대 100만원), 총급여 7천만원 초과자는 1명당
  25만원(최대 50만원) 상향. 출처: 기획재정부 2025년 세법개정안(정책브리핑 2025.10.30.)
  TODO(verify): 개정 법률 확정 여부 및 적용 시기(2026.1.1. 이후 사용분 여부) 확인 필요
- 국민참여형 국민성장펀드 소득공제 신설: 전용계좌로 3년 이상 투자 시 투자금액 3천만원 이하 40%,
  3천만~5천만원 20%, 5천만~7천만원 10% (최대 1,800만원), 소득공제 종합한도 2,500만원에 포함,
  적용기한 2030년. 출처: 조특법 개정안 국회 본회의 통과(2026.4.23., 한국세정신문·머니투데이 보도)
  TODO(verify): 근거 조문 번호, 구간 기준(연간 납입액 vs 누적), 시행령 확정 내용, 적용 개시 납입분
- 그 밖의 2026년 귀속 개정 사항: TODO(verify) 국세청 「2026년 귀속 연말정산 신고안내」로 확인 필요
"""

from decimal import Decimal

from app.tax.rules.base import (
    CardRules,
    ChildCreditRules,
    DonationCreditRules,
    EarnedIncomeCreditRules,
    EarnedIncomeDeductionRules,
    EducationCreditRules,
    GlobalIncomeRules,
    HousingRules,
    InsuranceCreditRules,
    LimitTier,
    MedicalCreditRules,
    MortgageType,
    NationalGrowthFundRules,
    PensionAccountRules,
    PersonalDeductionRules,
    ProgressiveBracket,
    RateTier,
    RentCreditRules,
    TaxRateBracket,
    TaxRules,
    VentureRules,
)

RULES = TaxRules(
    tax_year=2026,
    verified=False,
    notes=(
        "2026년 귀속 규칙은 공식 자료로 검증되지 않았습니다. TODO(verify)",
        "신용카드 등 사용액 증가분(전년 대비 5% 초과분) 추가 공제는 지원하지 않습니다. "
        "TODO(verify): 2025년 귀속 적용 여부·공제율(10%/20%)·비교 기간 공식 확인 필요",
        "고액 기부금 3천만원 초과분 40% 한시 공제율(2024년 기부분)은 2025년에 적용하지 않았습니다. "
        "TODO(verify): 2025년 기부분 연장 여부 확인 필요",
        "세액감면(중소기업 취업자 감면 등), 우리사주조합·장기집합투자증권저축·노란우산공제 소득공제는 "
        "지원하지 않습니다.",
    ),
    # 소득세법 제47조 제1항: 근로소득공제 (제2항: 공제액 한도 2,000만원)
    earned_income_deduction=EarnedIncomeDeductionRules(
        brackets=(
            ProgressiveBracket(lower=0, upper=5_000_000, base_amount=0, rate=Decimal("0.70")),
            ProgressiveBracket(
                lower=5_000_000, upper=15_000_000, base_amount=3_500_000, rate=Decimal("0.40")
            ),
            ProgressiveBracket(
                lower=15_000_000, upper=45_000_000, base_amount=7_500_000, rate=Decimal("0.15")
            ),
            ProgressiveBracket(
                lower=45_000_000, upper=100_000_000, base_amount=12_000_000, rate=Decimal("0.05")
            ),
            ProgressiveBracket(
                lower=100_000_000, upper=None, base_amount=14_750_000, rate=Decimal("0.02")
            ),
        ),
        max_deduction=20_000_000,
    ),
    # 소득세법 제50조(기본공제), 제51조(추가공제)
    personal=PersonalDeductionRules(
        basic_per_person=1_500_000,  # 제50조 제1항: 1명당 150만원
        elderly_additional=1_000_000,  # 제51조 제1항 제1호: 70세 이상 100만원
        elderly_min_age=70,
        disabled_additional=2_000_000,  # 제51조 제1항 제2호: 장애인 200만원
        female_additional=500_000,  # 제51조 제1항 제3호: 부녀자 50만원
        female_earned_income_limit=30_000_000,  # 제51조 제1항 제3호: 종합소득금액 3천만원 이하
        single_parent_additional=1_000_000,  # 제51조 제1항 제4호: 한부모 100만원
        dependent_income_limit=1_000_000,  # 제50조 제1항: 연간 소득금액 합계액 100만원 이하
        dependent_salary_only_limit=5_000_000,  # 같은 항: 근로소득만 있는 경우 총급여 500만원 이하
        ascendant_min_age=60,  # 제50조 제1항 제3호 가목: 직계존속 60세 이상
        descendant_max_age=20,  # 같은 호 나목: 직계비속·입양자 20세 이하
        sibling_max_age=20,  # 같은 호 라목: 형제자매 20세 이하 또는 60세 이상
        sibling_min_age=60,
    ),
    housing=HousingRules(
        # 조특법 제87조 제2항: 주택청약종합저축 납입액(연 300만원 한도)의 40%, 총급여 7천만원 이하
        subscription_rate=Decimal("0.40"),
        subscription_payment_limit=3_000_000,
        subscription_gross_salary_limit=70_000_000,
        # 소득세법 제52조 제4항: 주택임차차입금 원리금상환액 40%, 주택청약과 합산 연 400만원
        rent_loan_rate=Decimal("0.40"),
        rent_loan_and_subscription_limit=4_000_000,
        # 소득세법 제52조 제5항 (2024.1.1. 이후 상향): 위 공제와 합산한 한도
        mortgage_limits={
            MortgageType.FIXED_AND_NON_DEFERRED_15Y: 20_000_000,
            MortgageType.FIXED_OR_NON_DEFERRED_15Y: 18_000_000,
            MortgageType.OTHER_15Y: 8_000_000,
            MortgageType.FIXED_OR_NON_DEFERRED_10Y: 6_000_000,
        },
    ),
    # 조특법 제126조의2 (신용카드 등 사용금액에 대한 소득공제)
    card=CardRules(
        minimum_usage_rate=Decimal("0.25"),  # 제1항: 총급여의 25% 초과 사용분
        credit_rate=Decimal("0.15"),  # 제2항 제5호: 신용카드 15%
        debit_cash_rate=Decimal("0.30"),  # 제2항 제4호: 직불·선불카드, 현금영수증 30%
        culture_rate=Decimal("0.30"),  # 제2항 제3호: 도서·신문·공연·박물관·미술관·영화 30%
        sports_facility_rate=Decimal("0.30"),  # 2025.7.1. 이후 수영장·체력단련장 시설이용료 30%
        traditional_market_rate=Decimal("0.40"),  # 제2항 제1호: 전통시장 40%
        public_transport_rate=Decimal("0.40"),  # 제2항 제2호: 대중교통 40%
        culture_gross_salary_limit=70_000_000,  # 도서·공연 등 공제는 총급여 7천만원 이하만
        limit_salary_threshold=70_000_000,
        basic_limit_low_income=3_000_000,  # 제10항: 총급여 7천만원 이하 300만원
        basic_limit_high_income=2_500_000,  # 총급여 7천만원 초과 250만원
        additional_limit_low_income=3_000_000,  # 전통시장·대중교통·도서등 합산 300만원
        additional_limit_high_income=2_000_000,  # 전통시장·대중교통 합산 200만원
        # 자녀 수에 따른 기본한도 확대 (2025년 세법개정안). TODO(verify): 확정·적용 시기 확인
        child_basic_limit_per_child_low_income=500_000,
        child_basic_limit_per_child_high_income=250_000,
        child_basic_limit_max_low_income=1_000_000,
        child_basic_limit_max_high_income=500_000,
    ),
    # 조특법 제16조 제1항·제3항: 벤처기업 등 직접투자는 3천만원 이하 100%, 3천만~5천만원 70%,
    # 5천만원 초과 30%, 벤처투자조합 등 간접투자 10%. 한도: 종합소득금액의 50%
    venture=VentureRules(
        direct_tiers=(
            RateTier(upper=30_000_000, rate=Decimal("1.00")),
            RateTier(upper=50_000_000, rate=Decimal("0.70")),
            RateTier(upper=None, rate=Decimal("0.30")),
        ),
        fund_rate=Decimal("0.10"),
        income_limit_rate=Decimal("0.50"),
    ),
    # 국민참여형 국민성장펀드 소득공제 (2026년 신설, 조특법 개정 2026.4.23. 국회 통과)
    # 전용계좌로 3년 이상 투자, 투자금액 구간별 40% / 20% / 10%, 최대 1,800만원, 종합한도 포함
    # TODO(verify): 근거 조문 번호, 구간을 연간 납입액 기준으로 적용하는지 시행령으로 확인
    national_growth_fund=NationalGrowthFundRules(
        tiers=(
            RateTier(upper=30_000_000, rate=Decimal("0.40")),
            RateTier(upper=50_000_000, rate=Decimal("0.20")),
            RateTier(upper=70_000_000, rate=Decimal("0.10")),
            RateTier(upper=None, rate=Decimal("0")),  # 7천만원 초과분은 공제 없음
        ),
        max_deduction=18_000_000,
        min_holding_years=3,
        included_in_aggregate_limit=True,
    ),
    # 조특법 제132조의2: 특별소득공제 등 소득공제 종합한도 2,500만원
    aggregate_deduction_limit=25_000_000,
    # 소득세법 제55조 제1항 기본세율 (2023.1.1. 이후, 누진공제액 방식으로 환산)
    tax_rate_brackets=(
        TaxRateBracket(upper=14_000_000, rate=Decimal("0.06"), progressive_deduction=0),
        TaxRateBracket(upper=50_000_000, rate=Decimal("0.15"), progressive_deduction=1_260_000),
        TaxRateBracket(upper=88_000_000, rate=Decimal("0.24"), progressive_deduction=5_760_000),
        TaxRateBracket(upper=150_000_000, rate=Decimal("0.35"), progressive_deduction=15_440_000),
        TaxRateBracket(upper=300_000_000, rate=Decimal("0.38"), progressive_deduction=19_940_000),
        TaxRateBracket(upper=500_000_000, rate=Decimal("0.40"), progressive_deduction=25_940_000),
        TaxRateBracket(upper=1_000_000_000, rate=Decimal("0.42"), progressive_deduction=35_940_000),
        TaxRateBracket(upper=None, rate=Decimal("0.45"), progressive_deduction=65_940_000),
    ),
    # 소득세법 제59조: 근로소득세액공제
    earned_income_credit=EarnedIncomeCreditRules(
        tax_threshold=1_300_000,  # 산출세액 130만원 이하 55%, 초과분 30%
        low_rate=Decimal("0.55"),
        high_rate=Decimal("0.30"),
        limit_tiers=(
            # 제59조 제2항 제1호: 총급여 3,300만원 이하 74만원
            LimitTier(
                lower=0, upper=33_000_000, base=740_000, reduction_rate=Decimal("0"), floor=740_000
            ),
            # 제2호: 74만원 − (총급여 − 3,300만원) × 8/1,000, 최저 66만원
            LimitTier(
                lower=33_000_000,
                upper=70_000_000,
                base=740_000,
                reduction_rate=Decimal("0.008"),
                floor=660_000,
            ),
            # 제3호: 66만원 − (총급여 − 7,000만원) × 1/2, 최저 50만원
            LimitTier(
                lower=70_000_000,
                upper=120_000_000,
                base=660_000,
                reduction_rate=Decimal("0.5"),
                floor=500_000,
            ),
            # 제4호: 50만원 − (총급여 − 1억2천만원) × 1/2, 최저 20만원
            LimitTier(
                lower=120_000_000,
                upper=None,
                base=500_000,
                reduction_rate=Decimal("0.5"),
                floor=200_000,
            ),
        ),
    ),
    # 소득세법 제59조의2: 자녀세액공제 (2025.1.1. 이후 발생 소득분 상향)
    child_credit=ChildCreditRules(
        min_age=8,
        first_child=250_000,
        second_child=300_000,
        third_plus_child=400_000,
        # 제59조의2 제3항: 출산·입양 첫째 30만원, 둘째 50만원, 셋째 이상 70만원
        birth_first=300_000,
        birth_second=500_000,
        birth_third_plus=700_000,
    ),
    # 소득세법 제59조의3: 연금계좌세액공제 (2023.1.1. 이후 한도 상향)
    pension_account=PensionAccountRules(
        savings_limit=6_000_000,  # 연금저축 600만원
        combined_limit=9_000_000,  # 퇴직연금(IRP) 합산 900만원
        high_rate_gross_salary_limit=55_000_000,  # 총급여 5,500만원 이하 15%
        high_rate_income_limit=45_000_000,  # 종합소득금액 4,500만원 이하 15% (근로소득 외 소득이 있을 때)
        high_rate=Decimal("0.15"),
        low_rate=Decimal("0.12"),
    ),
    # 소득세법 제59조의4 제1항: 보험료 세액공제
    insurance_credit=InsuranceCreditRules(
        general_limit=1_000_000,
        general_rate=Decimal("0.12"),
        disabled_limit=1_000_000,
        disabled_rate=Decimal("0.15"),
    ),
    # 소득세법 제59조의4 제2항: 의료비 세액공제
    medical_credit=MedicalCreditRules(
        threshold_rate=Decimal("0.03"),  # 총급여 3% 초과분
        general_limit=7_000_000,  # 그 밖의 부양가족 연 700만원
        general_rate=Decimal("0.15"),
        specific_rate=Decimal("0.15"),  # 본인·65세 이상·장애인·6세 이하·산정특례자: 한도 없음
        premature_rate=Decimal("0.20"),  # 미숙아·선천성이상아
        infertility_rate=Decimal("0.30"),  # 난임시술비
        # 제59조의4 제2항 제1호: 65세 이상, (2024.1.1. 이후) 과세기간 개시일 현재 6세 이하
        specific_min_age=65,
        specific_max_age_at_start=6,
    ),
    # 소득세법 제59조의4 제3항: 교육비 세액공제
    education_credit=EducationCreditRules(
        rate=Decimal("0.15"),
        preschool_limit=3_000_000,  # 취학전 아동 1명당 300만원
        school_limit=3_000_000,  # 초·중·고 1명당 300만원
        university_limit=9_000_000,  # 대학생 1명당 900만원
    ),
    donation_credit=DonationCreditRules(
        # 조특법 제76조: 정치자금 10만원 이하 110분의 100, 10만원 초과분 15%(3천만원 초과분 25%)
        political_full_credit_limit=100_000,
        political_full_credit_ratio=Decimal(100) / Decimal(110),
        political_tiers=(
            RateTier(upper=30_000_000, rate=Decimal("0.15")),
            RateTier(upper=None, rate=Decimal("0.25")),
        ),
        # 조특법 제58조: 고향사랑기부금 10만원 이하 110분의 100, 초과분 15%
        # (특별재난지역 30%), 2025.1.1. 이후 기부분 연간 한도 2,000만원
        hometown_full_credit_limit=100_000,
        hometown_full_credit_ratio=Decimal(100) / Decimal(110),
        hometown_rate=Decimal("0.15"),
        hometown_disaster_rate=Decimal("0.30"),
        hometown_annual_limit=20_000_000,
        # 소득세법 제59조의4 제4항: 특례·일반기부금 1천만원 이하 15%, 초과분 30%
        general_tiers=(
            RateTier(upper=10_000_000, rate=Decimal("0.15")),
            RateTier(upper=None, rate=Decimal("0.30")),
        ),
        # 소득세법 제34조 제3항: 일반기부금 한도 = 소득금액의 30%
        # (종교단체 기부금이 있으면 10% + min(20%, 종교단체 외 기부금))
        general_limit_rate=Decimal("0.30"),
        religious_limit_rate=Decimal("0.10"),
        religious_extra_limit_rate=Decimal("0.20"),
    ),
    # 조특법 제95조의2: 월세 세액공제 (2024.1.1. 이후 지출분 한도 1,000만원, 총급여 8천만원 이하)
    rent_credit=RentCreditRules(
        gross_salary_limit=80_000_000,
        high_rate_gross_salary_limit=55_000_000,
        high_rate=Decimal("0.17"),
        low_rate=Decimal("0.15"),
        payment_limit=10_000_000,
    ),
    # 소득세법 제59조의4 제9항 제1호: 근로소득자 표준세액공제 13만원
    standard_credit=130_000,
    # 소득세법 제59조의4 제9항 제2호: 근로소득이 없는 거주자로서 종합소득이 있는 자 7만원
    standard_credit_non_earned=70_000,
    # 조특법 제92조: 결혼세액공제 50만원 (2024.1.1. ~ 2026.12.31. 혼인신고, 생애 1회)
    marriage_credit=500_000,
    # 지방세법 제103조의13: 근로소득 연말정산 시 특별징수 지방소득세 = 소득세 결정세액의 10%
    local_income_tax_rate=Decimal("0.10"),
    global_income=GlobalIncomeRules(
        # 소득세법 제129조 제1항 제3호: 인적용역 등 사업소득 원천징수 3%
        business_withholding_rate=Decimal("0.03"),
        # 소득세법 제129조 제1항 제6호: 기타소득 원천징수 20%
        other_withholding_rate=Decimal("0.20"),
        # 소득세법 시행령 제87조: 강연료·원고료 등 필요경비 의제 60%
        other_deemed_expense_rate=Decimal("0.60"),
        # 소득세법 제14조 제3항 제8호: 기타소득금액 300만원 이하 분리과세 선택 가능
        other_separate_threshold=3_000_000,
        # 소득세법 제129조 제1항 제6호: 분리과세 시 원천징수세율(20%)로 과세 종결
        other_separate_rate=Decimal("0.20"),
    ),
)
