"""입력/출력 데이터 모델. docs/03_데이터모델_API스펙.md 2~3장과 1:1 대응."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── 입력 ──────────────────────────────────────────────────

class BasicInfo(BaseModel):
    current_age: int = Field(ge=19, le=89, description="현재 나이")
    retire_age: int = Field(ge=19, le=90, description="은퇴(예정) 나이")
    married: bool = Field(default=False, description="혼인 여부")
    insurance_status: Literal["직장", "지역", "피부양자"] = Field(
        description="현재 건강보험 자격"
    )
    public_pension_start_age: int = Field(
        default=65, ge=50, le=80, description="공적연금 수령 개시 나이"
    )
    annual_living_expense: int = Field(
        default=0, ge=0, description="연간 생활비 (자산 소진 계산용, 0이면 생략)"
    )


class IncomeInput(BaseModel):
    earned: int = Field(default=0, ge=0, description="근로소득 총급여 (연)")
    business: int = Field(default=0, ge=0, description="사업소득 (연)")
    other: int = Field(default=0, ge=0, description="기타소득 (연)")


class FinancialInput(BaseModel):
    interest: int = Field(default=0, ge=0, description="이자소득")
    dividend_domestic: int = Field(default=0, ge=0, description="국내 주식 배당")
    dividend_foreign: int = Field(default=0, ge=0, description="해외 주식 배당")
    etf_domestic_equity_dist: int = Field(
        default=0, ge=0, description="국내 주식형 ETF 분배금"
    )
    etf_domestic_other_dist_and_gain: int = Field(
        default=0, ge=0, description="기타 국내 ETF 분배금+과세 매매차익"
    )
    etf_foreign_dist: int = Field(default=0, ge=0, description="해외 상장 ETF 분배금")
    capital_gain_foreign: int = Field(
        default=0, ge=0, description="해외 주식/ETF 양도차익 (금융소득 아님)"
    )


class PensionInput(BaseModel):
    public_annual: int = Field(default=0, ge=0, description="공적연금 (연)")
    private_annual: int = Field(default=0, ge=0, description="사적연금 (연)")
    tax_free_annual: int = Field(default=0, ge=0, description="비과세 연금 (연)")
    housing_monthly: int = Field(default=0, ge=0, description="주택연금 (월)")


class PropertyInput(BaseModel):
    real_estate_tax_base: int = Field(
        default=0, ge=0, description="부동산 재산세 과세표준"
    )
    rent_monthly: int = Field(default=0, ge=0, description="임대 월세 수입 (월)")
    financial_assets: int = Field(
        default=0, ge=0, description="금융자산 총액 (시뮬레이션 초기값)"
    )


class UserInput(BaseModel):
    basic: BasicInfo
    income: IncomeInput = IncomeInput()
    financial: FinancialInput = FinancialInput()
    pension: PensionInput = PensionInput()
    property: PropertyInput = PropertyInput()


# ── 출력 ──────────────────────────────────────────────────

class AggregateFinancialTaxResult(BaseModel):
    subject: bool
    total: int
    threshold: int
    margin: int


class IncomeTaxResult(BaseModel):
    aggregate_income_tax: int
    private_pension_tax: int
    foreign_capital_gain_tax: int
    financial_withholding_tax: int
    total_tax: int
    tax_base: int


class HealthInsuranceResult(BaseModel):
    status_applied: str
    monthly_premium: int
    annual_premium: int
    dependent_eligible: bool
    dependent_fail_reasons: list[str]


class CashflowRow(BaseModel):
    age: int
    status: str
    income: int
    tax: int
    insurance: int
    net: int
    remaining_assets: int


class ScenarioResult(BaseModel):
    label: str
    financial_income_total: int
    aggregate_subject: bool
    cashflow_by_age: list[CashflowRow]
    asset_depletion_age: Optional[int]
    retire_year_snapshot: Optional[dict]


class SimulationResult(BaseModel):
    aggregate_financial_tax: AggregateFinancialTaxResult
    income_tax: IncomeTaxResult
    health_insurance: HealthInsuranceResult
    scenarios: dict[str, ScenarioResult]
    disclaimers: list[str]
