"""모듈 1~4: 금융소득 합산, 종합과세 판정, 연금 분류, 종합소득세 추정.

계산식은 docs/02_세무건보_규칙.md 2~5장과 1:1 대응한다.
"""

from . import rules
from .models import FinancialInput, IncomeInput, PensionInput


# ── 모듈 1: 금융소득 합산 ─────────────────────────────────

def calc_financial_income(fin: FinancialInput) -> dict:
    total = (
        fin.interest
        + fin.dividend_domestic
        + fin.dividend_foreign
        + fin.etf_domestic_equity_dist
        + fin.etf_domestic_other_dist_and_gain
        + fin.etf_foreign_dist
    )
    return {
        "financial_income_total": total,
        "foreign_capital_gain": fin.capital_gain_foreign,
    }


# ── 모듈 2: 금융소득종합과세 판정 ─────────────────────────

def is_subject_to_aggregate_financial_tax(financial_income_total: int) -> dict:
    return {
        "subject": financial_income_total > rules.FIN_TAX_THRESHOLD,
        "total": financial_income_total,
        "threshold": rules.FIN_TAX_THRESHOLD,
        "margin": rules.FIN_TAX_THRESHOLD - financial_income_total,
    }


# ── 모듈 3: 연금소득 분류 ─────────────────────────────────

def _private_pension_age_rate(age: int) -> float:
    if age >= 80:
        return rules.PRIVATE_PENSION_RATE_80UP
    if age >= 70:
        return rules.PRIVATE_PENSION_RATE_70S
    return rules.PRIVATE_PENSION_RATE_UNDER70


def classify_pension(pension: PensionInput, age: int,
                     public_active: bool = True,
                     private_active: bool = True) -> dict:
    """연금을 종합과세분 / 분리과세 세액 / 비과세 현금흐름으로 분류.

    public_active/private_active: 시뮬레이션에서 해당 연도에 수령 중인지 여부.
    """
    public_annual = pension.public_annual if public_active else 0
    private_annual = pension.private_annual if private_active else 0
    tax_free = (pension.tax_free_annual + pension.housing_monthly * 12) if private_active else 0

    # (a) 공적연금: 80%를 과세대상으로 보고 40%(상한 900만)를 공제 (단순화 S3)
    deduction = min(
        public_annual * rules.PENSION_INCOME_DEDUCTION_RATE,
        rules.PENSION_INCOME_DEDUCTION_MAX,
    )
    public_taxable = max(
        0, public_annual * rules.PUBLIC_PENSION_TAXABLE_RATIO - deduction
    )

    # (b) 사적연금: 1,500만 이하 저율 분리과세 / 초과 시 16.5% 분리과세 고정 (단순화 S4)
    if private_annual <= rules.PRIVATE_PENSION_SEP_LIMIT:
        private_tax = private_annual * _private_pension_age_rate(age)
    else:
        private_tax = private_annual * rules.PRIVATE_PENSION_EXCESS_SEP_RATE

    return {
        "public_annual": public_annual,
        "public_pension_taxable": round(public_taxable),
        "private_annual": private_annual,
        "private_pension_tax": round(private_tax),
        "private_to_aggregate": 0,
        "tax_free_cashflow": tax_free,
    }


# ── 모듈 4: 종합소득세 추정 ───────────────────────────────

def progressive_tax(tax_base: float) -> float:
    """누진세율표 적용 (지방소득세 제외 산출세액)."""
    if tax_base <= 0:
        return 0
    for upper, rate, deduction in rules.TAX_BRACKETS:
        if upper is None or tax_base <= upper:
            return tax_base * rate - deduction
    raise AssertionError("unreachable")


def calc_income_tax(income: IncomeInput, rent_monthly: int, married: bool,
                    financial_summary: dict, pension_summary: dict,
                    earned_active: bool = True) -> dict:
    fin_total = financial_summary["financial_income_total"]
    foreign_cg = financial_summary["foreign_capital_gain"]
    earned = income.earned if earned_active else 0
    rental = rent_monthly * 12

    # 1단계: 종합과세 대상 소득 합산
    earned_deduction = min(
        earned * rules.EARNED_INCOME_DEDUCTION_RATE,
        rules.EARNED_INCOME_DEDUCTION_MAX,
    )
    earned_amount = max(0, earned - earned_deduction)
    base_income = (
        earned_amount + income.business + income.other + rental
        + pension_summary["public_pension_taxable"]
        + pension_summary["private_to_aggregate"]
    )

    # 2단계: 금융소득 2,000만 기준 분리 (단순화 S1·S2)
    if fin_total <= rules.FIN_TAX_THRESHOLD:
        fin_to_aggregate = 0
        threshold_tax = 0
        withholding = fin_total * rules.FIN_WITHHOLDING_RATE * (1 + rules.LOCAL_TAX_RATE)
    else:
        fin_to_aggregate = fin_total - rules.FIN_TAX_THRESHOLD
        threshold_tax = rules.FIN_TAX_THRESHOLD * rules.FIN_WITHHOLDING_RATE
        withholding = 0  # 기준금액분 세액은 산출세액에 포함되므로 중복 계상하지 않음

    # 3단계: 과세표준과 산출세액 (지방세 10% 포함)
    basic_deduction = rules.BASIC_DEDUCTION_PER_PERSON * (2 if married else 1)
    tax_base = max(0, base_income + fin_to_aggregate - basic_deduction)
    aggregate_tax = (progressive_tax(tax_base) + threshold_tax) * (1 + rules.LOCAL_TAX_RATE)

    # 4단계: 해외 양도소득세 (별도 트랙)
    foreign_cg_tax = max(0, foreign_cg - rules.FOREIGN_CG_DEDUCTION) * rules.FOREIGN_CG_RATE

    # 5단계: 연간 총 세부담
    private_pension_tax = pension_summary["private_pension_tax"]
    total_tax = aggregate_tax + private_pension_tax + foreign_cg_tax + withholding

    return {
        "aggregate_income_tax": round(aggregate_tax),
        "private_pension_tax": round(private_pension_tax),
        "foreign_capital_gain_tax": round(foreign_cg_tax),
        "financial_withholding_tax": round(withholding),
        "total_tax": round(total_tax),
        "tax_base": round(tax_base),
    }
