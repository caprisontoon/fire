"""FastAPI 앱: POST /api/simulate 단일 엔드포인트 + 프론트엔드 정적 파일 서빙.

실행: uvicorn backend.main:app --reload
API 문서: http://localhost:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .health_insurance import calc_health_insurance
from .models import (AggregateFinancialTaxResult, HealthInsuranceResult,
                     IncomeTaxResult, SimulationResult, UserInput)
from .simulation import run_scenarios
from .tax import (calc_financial_income, calc_income_tax, classify_pension,
                  is_subject_to_aggregate_financial_tax)

DISCLAIMERS = [
    "본 결과는 단순화된 모델에 따른 참고용 추정치이며, 실제 세액·보험료와 다를 수 있습니다.",
    "실제 세무 신고는 세무사 또는 국세청(홈택스), 건강보험료는 국민건강보험공단의 안내를 따르십시오.",
    "세법·건강보험 제도는 매년 바뀝니다. 본 시뮬레이터는 2025년 제도 기준입니다.",
]

app = FastAPI(title="은퇴·파이어족 세금/건보 시뮬레이터",
              description="금융소득종합과세·종합소득세·건강보험료·현금흐름 참고용 추정")


@app.post("/api/simulate", response_model=SimulationResult)
def simulate(user: UserInput) -> SimulationResult:
    basic = user.basic
    working = basic.current_age < basic.retire_age

    # 최상위 판정 카드: 현재 나이 기준 1년치 스냅샷 (시나리오 A)
    fin = calc_financial_income(user.financial)
    judge = is_subject_to_aggregate_financial_tax(fin["financial_income_total"])
    pen = classify_pension(user.pension, basic.current_age,
                           public_active=basic.current_age >= basic.public_pension_start_age,
                           private_active=not working)
    tax = calc_income_tax(user.income, user.property.rent_monthly, basic.married,
                          fin, pen, earned_active=working)
    hi = calc_health_insurance(basic.insurance_status, fin["financial_income_total"],
                               pen["public_annual"], user.income,
                               user.property.rent_monthly, user.property,
                               earned_active=working)

    return SimulationResult(
        aggregate_financial_tax=AggregateFinancialTaxResult(**judge),
        income_tax=IncomeTaxResult(**tax),
        health_insurance=HealthInsuranceResult(**hi),
        scenarios=run_scenarios(user),
        disclaimers=DISCLAIMERS,
    )


# 프론트엔드 정적 파일 서빙 (frontend/ 폴더가 있으면)
_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.is_dir():
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(_frontend / "index.html")

    app.mount("/static", StaticFiles(directory=_frontend), name="static")
