"""docs/02_세무건보_규칙.md 8장의 대표 케이스 3종 + 세율표 검증."""

from backend import rules
from backend.health_insurance import calc_health_insurance, check_dependent
from backend.models import (FinancialInput, IncomeInput, PensionInput,
                            PropertyInput)
from backend.tax import (calc_financial_income,
                         is_subject_to_aggregate_financial_tax,
                         progressive_tax)


def test_progressive_tax_table():
    # 구간 경계 검증: 과세표준 1,400만 → 84만 / 5,000만 → 624만
    assert progressive_tax(14_000_000) == 14_000_000 * 0.06
    assert progressive_tax(50_000_000) == 50_000_000 * 0.15 - 1_260_000
    assert progressive_tax(0) == 0


def test_case1_safe_fire():
    """케이스 ①: 금융소득 1,800만, 연금 0, 재산과표 3억, 피부양자.
    → 종합과세 No, 피부양자 유지, 건보료 0."""
    fin = calc_financial_income(FinancialInput(interest=18_000_000))
    judge = is_subject_to_aggregate_financial_tax(fin["financial_income_total"])
    assert judge["subject"] is False
    assert judge["margin"] == 2_000_000

    hi = calc_health_insurance(
        "피부양자", fin["financial_income_total"], 0, IncomeInput(), 0,
        PropertyInput(real_estate_tax_base=300_000_000), earned_active=False,
    )
    assert hi["dependent_eligible"] is True
    assert hi["monthly_premium"] == 0
    assert hi["status_applied"] == "피부양자"


def test_case2_borderline():
    """케이스 ②: 금융소득 2,100만, 공적연금 1,200만, 지역가입.
    → 종합과세 Yes(100만 초과), 건보 부과소득 = 2,100만(전액) + 600만(연금 50%)."""
    fin = calc_financial_income(FinancialInput(interest=21_000_000))
    judge = is_subject_to_aggregate_financial_tax(fin["financial_income_total"])
    assert judge["subject"] is True
    assert judge["margin"] == -1_000_000

    hi = calc_health_insurance(
        "지역", 21_000_000, 12_000_000, IncomeInput(), 0,
        PropertyInput(), earned_active=False,
    )
    expected_income = 21_000_000 + 12_000_000 * rules.HI_PUBLIC_PENSION_RATIO  # 2,700만
    expected_monthly = (expected_income / 12 * rules.HI_RATE) * (1 + rules.LTC_RATE_ON_HI)
    assert hi["status_applied"] == "지역"
    assert hi["monthly_premium"] == round(expected_monthly)


def test_case3_dependent_loss():
    """케이스 ③: 금융소득 900만, 공적연금 1,300만, 피부양자.
    → 종합과세 No, 건보 부과 금융소득 0이지만 판정소득 2,200만 → 탈락, 지역 전환.
    '세금은 안 늘었는데 건보료가 새로 생기는' 핵심 시나리오."""
    fin_total = 9_000_000
    judge = is_subject_to_aggregate_financial_tax(fin_total)
    assert judge["subject"] is False

    dep = check_dependent(fin_total, 13_000_000, IncomeInput(), 0, PropertyInput())
    assert dep["eligible"] is False
    assert dep["judge_income"] == 22_000_000  # 연금 100% + 금융소득 전액

    hi = calc_health_insurance(
        "피부양자", fin_total, 13_000_000, IncomeInput(), 0,
        PropertyInput(), earned_active=False,
    )
    assert hi["status_applied"] == "지역"  # 탈락 → 지역 전환
    # 부과소득: 금융소득은 1,000만 이하라 0, 연금 50%만 = 650만
    expected_monthly = (6_500_000 / 12 * rules.HI_RATE) * (1 + rules.LTC_RATE_ON_HI)
    assert hi["monthly_premium"] == round(expected_monthly)
    assert "합산소득 2,000만 원 초과" in hi["dependent_fail_reasons"]
