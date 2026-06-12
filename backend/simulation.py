"""모듈 6: 연령별 현금흐름 시뮬레이션과 시나리오 A/B/C.

연도마다 모듈 1~5를 다시 실행한다 (은퇴 전후로 소득·건보 자격이 바뀌므로).
자산 변화식은 docs/03_데이터모델_API스펙.md 3장 참고:
  다음해 자산 = 자산×(1+수익률) − (금융소득+해외양도차익) + (순현금흐름 − 생활비)
금융소득은 자산 수익의 일부(현금 인출분)로 간주해 이중계산을 막는다.
"""

import copy

from . import rules
from .health_insurance import calc_health_insurance
from .models import ScenarioResult, UserInput
from .tax import (calc_financial_income, calc_income_tax, classify_pension,
                  is_subject_to_aggregate_financial_tax)


def _year_result(user: UserInput, age: int) -> dict:
    """한 연도의 소득·세금·건보료를 계산한다."""
    basic = user.basic
    working = age < basic.retire_age
    public_active = age >= basic.public_pension_start_age
    private_active = age >= basic.retire_age  # 사적·비과세·주택연금은 은퇴부터 (단순화)

    fin = calc_financial_income(user.financial)
    pen = classify_pension(user.pension, age, public_active, private_active)
    tax = calc_income_tax(user.income, user.property.rent_monthly, basic.married,
                          fin, pen, earned_active=working)

    # 은퇴 전: 입력한 자격 그대로 / 은퇴 후: 피부양자 가능하면 피부양자, 아니면 지역
    status = basic.insurance_status if working else "피부양자"
    hi = calc_health_insurance(status, fin["financial_income_total"],
                               pen["public_annual"], user.income,
                               user.property.rent_monthly, user.property,
                               earned_active=working)

    income_total = (
        (user.income.earned if working else 0)
        + user.income.business + user.income.other
        + user.property.rent_monthly * 12
        + fin["financial_income_total"] + fin["foreign_capital_gain"]
        + pen["public_annual"] + pen["private_annual"] + pen["tax_free_cashflow"]
    )
    net = income_total - tax["total_tax"] - hi["annual_premium"]

    return {"age": age, "status": hi["status_applied"], "income": round(income_total),
            "tax": tax["total_tax"], "insurance": hi["annual_premium"],
            "net": round(net), "fin": fin, "tax_detail": tax, "hi_detail": hi}


def simulate_cashflow_by_age(user: UserInput) -> dict:
    """현재 나이~90세 연 단위 시뮬레이션."""
    rows = []
    assets = float(user.property.financial_assets)
    living = user.basic.annual_living_expense
    depletion_age = None
    retire_snapshot = None

    for age in range(user.basic.current_age, rules.SIM_END_AGE + 1):
        r = _year_result(user, age)
        fin_cash = (r["fin"]["financial_income_total"]
                    + r["fin"]["foreign_capital_gain"])
        assets = assets * (1 + rules.ASSET_RETURN_RATE) - fin_cash \
            + (r["net"] - living)
        if living > 0 and assets < 0 and depletion_age is None:
            depletion_age = age
        if age == user.basic.retire_age:
            retire_snapshot = {"age": age, "tax": r["tax_detail"],
                               "health_insurance": r["hi_detail"]}
        rows.append({"age": age, "status": r["status"], "income": r["income"],
                     "tax": r["tax"], "insurance": r["insurance"],
                     "net": r["net"], "remaining_assets": round(assets)})

    return {"cashflow_by_age": rows, "asset_depletion_age": depletion_age,
            "retire_year_snapshot": retire_snapshot}


def _cap_financial_income(user: UserInput, cap: int) -> UserInput:
    """금융소득 6개 필드를 같은 비율로 축소해 합계를 한도에 맞춘다.

    해외 양도차익은 금융소득이 아니므로 조정하지 않는다.
    """
    capped = copy.deepcopy(user)
    fin = capped.financial
    total = calc_financial_income(fin)["financial_income_total"]
    if total <= cap or total == 0:
        return capped
    ratio = cap / total
    # 내림 처리: 반올림 합산으로 한도를 1~2원 넘는 일을 막는다
    fin.interest = int(fin.interest * ratio)
    fin.dividend_domestic = int(fin.dividend_domestic * ratio)
    fin.dividend_foreign = int(fin.dividend_foreign * ratio)
    fin.etf_domestic_equity_dist = int(fin.etf_domestic_equity_dist * ratio)
    fin.etf_domestic_other_dist_and_gain = int(
        fin.etf_domestic_other_dist_and_gain * ratio)
    fin.etf_foreign_dist = int(fin.etf_foreign_dist * ratio)
    return capped


def run_scenarios(user: UserInput) -> dict[str, ScenarioResult]:
    scenarios = {
        "A": ("현재 입력 그대로", user),
        "B": ("금융소득 연 2,000만 원 이하 관리",
              _cap_financial_income(user, rules.SCENARIO_B_CAP)),
        "C": ("금융소득 연 1,000만 원 이하 관리",
              _cap_financial_income(user, rules.SCENARIO_C_CAP)),
    }
    results = {}
    for key, (label, u) in scenarios.items():
        fin_total = calc_financial_income(u.financial)["financial_income_total"]
        sim = simulate_cashflow_by_age(u)
        results[key] = ScenarioResult(
            label=label,
            financial_income_total=fin_total,
            aggregate_subject=is_subject_to_aggregate_financial_tax(fin_total)["subject"],
            **sim,
        )
    return results
