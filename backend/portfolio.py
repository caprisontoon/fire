"""포트폴리오 설계 모드: 상품 구성 → 배당·이자 산출 → 종합과세/세금/건보료 역산.

사용자가 '무엇에 얼마를 어떤 수익률로' 담을지 입력하면, 상품 유형에 따라
세금 분류가 자동으로 결정된다. 기존 계산 엔진(tax.py, health_insurance.py)을
그대로 재사용한다. 설명서는 docs/07_포트폴리오_설계.md 참고.
"""

from typing import Literal

from pydantic import BaseModel, Field

from . import rules
from .health_insurance import calc_health_insurance
from .models import FinancialInput, IncomeInput, PensionInput, PropertyInput
from .tax import (calc_financial_income, calc_income_tax, classify_pension,
                  is_subject_to_aggregate_financial_tax)

# ── 상품 유형 등록표 ──────────────────────────────────────
# field: 산출 소득이 합산될 FinancialInput 필드 (None이면 분리과세·비과세 → 금융소득 제외)
# note: 화면 안내용 한 줄 설명
PRODUCT_TYPES: dict[str, dict] = {
    "domestic_stock": {
        "label": "국내 주식 (배당주)", "field": "dividend_domestic",
        "note": "배당금이 금융소득에 합산됩니다. 매매차익은 비과세입니다.",
    },
    "domestic_equity_etf": {
        "label": "국내 주식형 ETF", "field": "etf_domestic_equity_dist",
        "note": "분배금만 금융소득. 매매차익은 비과세라 종합과세·건보 위험이 가장 낮습니다.",
    },
    "domestic_other_etf": {
        "label": "기타 국내 ETF (해외지수·채권·리츠 등)",
        "field": "etf_domestic_other_dist_and_gain",
        "note": "분배금과 과세 대상 매매차익이 모두 금융소득에 합산됩니다.",
    },
    "foreign_stock": {
        "label": "해외 주식", "field": "dividend_foreign",
        "note": "배당금만 금융소득. 양도차익은 별도(양도세 22%)라 종합과세·건보에 거의 영향이 없습니다.",
    },
    "foreign_etf": {
        "label": "해외 상장 ETF", "field": "etf_foreign_dist",
        "note": "분배금만 금융소득. 양도차익은 별도(양도세 22%)입니다.",
    },
    "bond": {
        "label": "채권", "field": "interest",
        "note": "이자가 금융소득에 합산됩니다.",
    },
    "deposit": {
        "label": "예금·적금", "field": "interest",
        "note": "이자가 금융소득에 합산됩니다.",
    },
    "reits": {
        "label": "리츠 (REITs)", "field": "dividend_domestic",
        "note": "배당금이 금융소득에 합산됩니다.",
    },
    "separate_or_taxfree": {
        "label": "분리과세·비과세 (ISA·연금저축·IRP 등)", "field": None,
        "note": "이 수익은 금융소득·건보료 계산에서 제외되고 현금흐름에만 더해집니다.",
    },
}

PRODUCT_CODES = tuple(PRODUCT_TYPES.keys())


# ── 입력 모델 ─────────────────────────────────────────────

class PortfolioHolding(BaseModel):
    product_type: Literal[PRODUCT_CODES]  # type: ignore[valid-type]
    label: str = Field(default="", description="메모 (예: TIGER 미국S&P500)")
    amount: int = Field(ge=0, description="목표 나이 시점의 평가금액")
    annual_yield_pct: float = Field(
        ge=0, le=100, description="연 분배/배당/이자 수익률 (%)"
    )


class Portfolio(BaseModel):
    label: str = Field(description="포트폴리오 이름 (예: 배당주 중심)")
    holdings: list[PortfolioHolding] = Field(default_factory=list)


class PortfolioBasic(BaseModel):
    current_age: int = Field(ge=19, le=89)
    target_age: int = Field(ge=40, le=90, description="이 포트폴리오로 사는 시작 나이")
    married: bool = False
    insurance_status: Literal["직장", "지역", "피부양자"] = "지역"
    public_pension_start_age: int = Field(default=65, ge=50, le=80)
    annual_living_expense: int = Field(default=0, ge=0)


class PortfolioSimInput(BaseModel):
    basic: PortfolioBasic
    pension: PensionInput = PensionInput()
    property: PropertyInput = PropertyInput()
    portfolios: list[Portfolio] = Field(min_length=1, max_length=3)


# ── 핵심 계산 ─────────────────────────────────────────────

def portfolio_to_financial(holdings: list[PortfolioHolding]) -> dict:
    """보유 상품을 금융소득(FinancialInput) + 비과세 현금흐름 + 평가총액으로 환산."""
    fields = {
        "interest": 0, "dividend_domestic": 0, "dividend_foreign": 0,
        "etf_domestic_equity_dist": 0, "etf_domestic_other_dist_and_gain": 0,
        "etf_foreign_dist": 0, "capital_gain_foreign": 0,
    }
    tax_free_income = 0
    total_value = 0
    breakdown: dict[str, int] = {}

    for h in holdings:
        income = round(h.amount * h.annual_yield_pct / 100)
        total_value += h.amount
        meta = PRODUCT_TYPES[h.product_type]
        if meta["field"] is None:
            tax_free_income += income
        else:
            fields[meta["field"]] += income
        breakdown[meta["label"]] = breakdown.get(meta["label"], 0) + income

    return {
        "financial": FinancialInput(**fields),
        "tax_free_income": tax_free_income,
        "total_value": total_value,
        "breakdown": breakdown,
    }


def simulate_one_portfolio(basic: PortfolioBasic, pension: PensionInput,
                           prop: PropertyInput, portfolio: Portfolio) -> dict:
    mapped = portfolio_to_financial(portfolio.holdings)
    fin = mapped["financial"]
    fin_summary = calc_financial_income(fin)
    fin_total = fin_summary["financial_income_total"]
    judge = is_subject_to_aggregate_financial_tax(fin_total)

    prop_for_sim = PropertyInput(
        real_estate_tax_base=prop.real_estate_tax_base,
        rent_monthly=prop.rent_monthly,
        financial_assets=mapped["total_value"],
    )
    no_earned = IncomeInput()  # 포트폴리오 모드는 근로·사업소득 없음 (노후 자산 중심)
    rent_annual = prop.rent_monthly * 12

    rows = []
    assets = float(mapped["total_value"])
    living = basic.annual_living_expense
    depletion_age = None
    target_snapshot = None

    for age in range(basic.target_age, rules.SIM_END_AGE + 1):
        public_active = age >= basic.public_pension_start_age
        pen = classify_pension(pension, age, public_active, private_active=True)
        tax = calc_income_tax(no_earned, prop.rent_monthly, basic.married,
                              fin_summary, pen, earned_active=False)
        hi = calc_health_insurance(basic.insurance_status, fin_total,
                                   pen["public_annual"], no_earned,
                                   prop.rent_monthly, prop_for_sim,
                                   earned_active=False)
        income_total = (
            fin_total + fin_summary["foreign_capital_gain"]
            + mapped["tax_free_income"] + rent_annual
            + pen["public_annual"] + pen["private_annual"]
            + pen["tax_free_cashflow"]
        )
        net = income_total - tax["total_tax"] - hi["annual_premium"]
        assets = assets + (net - living)  # 잉여는 적립, 부족은 원금 인출 (성장 미가정)
        if living > 0 and assets < 0 and depletion_age is None:
            depletion_age = age
        if target_snapshot is None:
            target_snapshot = {"age": age, "income_tax": tax, "health_insurance": hi,
                               "income_total": round(income_total), "net": round(net)}
        rows.append({"age": age, "status": hi["status_applied"],
                     "income": round(income_total), "tax": tax["total_tax"],
                     "insurance": hi["annual_premium"], "net": round(net),
                     "remaining_assets": round(assets)})

    return {
        "label": portfolio.label,
        "total_value": mapped["total_value"],
        "financial_income_total": fin_total,
        "income_breakdown": mapped["breakdown"],
        "tax_free_income": mapped["tax_free_income"],
        "aggregate_subject": judge["subject"],
        "aggregate_margin": judge["margin"],
        "target_snapshot": target_snapshot,
        "cashflow_by_age": rows,
        "asset_depletion_age": depletion_age,
    }


DISCLAIMERS = [
    "본 결과는 단순화된 모델에 따른 참고용 추정치이며, 실제 세액·보험료와 다를 수 있습니다.",
    "수익률은 입력하신 가정치이며, 시장 상황에 따라 실제 배당·분배금은 달라집니다.",
    "해외 주식/ETF의 양도차익(매도 차익)은 이 모드에서 0으로 가정합니다(분배금·배당만 반영). "
    "양도차익은 종합과세·건보료에 거의 영향이 없으나, 양도세는 별도로 발생합니다.",
    "물가상승은 반영하지 않으며, 모든 금액은 현재 가치 기준입니다.",
]


def simulate_portfolios(data: PortfolioSimInput) -> dict:
    results = []
    for p in data.portfolios:
        results.append(
            simulate_one_portfolio(data.basic, data.pension, data.property, p)
        )
    return {"portfolios": results, "target_age": data.basic.target_age,
            "disclaimers": DISCLAIMERS}
