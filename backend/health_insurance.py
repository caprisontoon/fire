"""모듈 5: 건강보험료·피부양자 판정.

계산식은 docs/02_세무건보_규칙.md 6장과 1:1 대응한다.
핵심 비대칭: 부과 기준에는 공적연금 50%·금융소득(1,000만 초과 시 전액),
피부양자 판정에는 공적연금 100%·금융소득 전액이 들어간다.
"""

from . import rules
from .models import IncomeInput, PropertyInput


def _premium_income(financial_income_total: int, public_annual: int,
                    income: IncomeInput, rental_annual: int,
                    earned_active: bool) -> int:
    """건보 부과 기준 소득 (연). 근로소득은 제외(직장 기본보험료에서 별도 부과)."""
    fin = financial_income_total if financial_income_total > rules.HI_FIN_INCOME_MIN else 0
    return round(
        fin
        + public_annual * rules.HI_PUBLIC_PENSION_RATIO
        + income.business + income.other + rental_annual
    )


def check_dependent(financial_income_total: int, public_annual: int,
                    income: IncomeInput, rental_annual: int,
                    prop: PropertyInput) -> dict:
    """피부양자 유지 가능 여부. 판정 소득은 연금 100%·금융소득 전액 합산."""
    judge_income = (
        financial_income_total + public_annual
        + income.business + income.other + rental_annual
    )
    reasons = []
    if judge_income > rules.DEP_INCOME_LIMIT:
        reasons.append("합산소득 2,000만 원 초과")
    if income.business + rental_annual > 0:
        reasons.append("사업·임대소득 존재 (탈락 위험)")
    if prop.real_estate_tax_base > rules.DEP_PROPERTY_LIMIT_2:
        reasons.append("재산 과표 9억 원 초과")
    elif (prop.real_estate_tax_base > rules.DEP_PROPERTY_LIMIT_1
          and judge_income > rules.DEP_INCOME_LIMIT_MID_PROPERTY):
        reasons.append("재산 과표 5.4억 원 초과 + 합산소득 1,000만 원 초과")
    return {"eligible": len(reasons) == 0, "fail_reasons": reasons,
            "judge_income": judge_income}


def _regional_monthly(premium_income_annual: int, prop: PropertyInput) -> float:
    income_part = premium_income_annual / 12 * rules.HI_RATE
    property_part = (
        max(0, prop.real_estate_tax_base - rules.HI_PROPERTY_DEDUCTION)
        * rules.HI_PROPERTY_RATE_SIMPLE / 12
    )  # 실제 점수표 대신 단순 부과율 (단순화 S7)
    return max(income_part + property_part, rules.HI_REGIONAL_MIN_MONTHLY) \
        * (1 + rules.LTC_RATE_ON_HI)


def calc_health_insurance(status: str, financial_income_total: int,
                          public_annual: int, income: IncomeInput,
                          rent_monthly: int, prop: PropertyInput,
                          earned_active: bool = True) -> dict:
    rental = rent_monthly * 12
    base_income = _premium_income(
        financial_income_total, public_annual, income, rental, earned_active
    )
    dep = check_dependent(financial_income_total, public_annual, income, rental, prop)

    if status == "직장" and earned_active:
        base = income.earned / 12 * rules.HI_EMPLOYEE_RATE
        extra = max(0, base_income - rules.HI_EMPLOYEE_EXTRA_THRESHOLD) / 12 * rules.HI_RATE
        monthly = (base + extra) * (1 + rules.LTC_RATE_ON_HI)
        applied = "직장"
    elif status == "피부양자" and dep["eligible"]:
        monthly = 0
        applied = "피부양자"
    else:
        # 지역가입자, 또는 피부양자 탈락 → 지역 전환, 또는 은퇴한 직장가입자
        monthly = _regional_monthly(base_income, prop)
        applied = "지역"

    return {
        "status_applied": applied,
        "monthly_premium": round(monthly),
        "annual_premium": round(monthly * 12),
        "dependent_eligible": dep["eligible"],
        "dependent_fail_reasons": dep["fail_reasons"],
    }
