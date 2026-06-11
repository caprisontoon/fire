"""POST /api/simulate 통합 테스트: docs/03 2-6장의 예시 입력으로 전체 응답 구조 검증."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE = {
    "basic": {"current_age": 52, "retire_age": 55, "married": True,
              "insurance_status": "직장", "public_pension_start_age": 65,
              "annual_living_expense": 36_000_000},
    "income": {"earned": 60_000_000, "business": 0, "other": 0},
    "financial": {"interest": 3_000_000, "dividend_domestic": 5_000_000,
                  "dividend_foreign": 4_000_000, "etf_domestic_equity_dist": 1_000_000,
                  "etf_domestic_other_dist_and_gain": 6_000_000,
                  "etf_foreign_dist": 2_000_000, "capital_gain_foreign": 10_000_000},
    "pension": {"public_annual": 18_000_000, "private_annual": 12_000_000,
                "tax_free_annual": 0, "housing_monthly": 0},
    "property": {"real_estate_tax_base": 300_000_000, "rent_monthly": 500_000,
                 "financial_assets": 800_000_000},
}


def test_simulate_full_response():
    res = client.post("/api/simulate", json=SAMPLE)
    assert res.status_code == 200
    body = res.json()

    # 금융소득 2,100만 → 종합과세 대상
    assert body["aggregate_financial_tax"]["subject"] is True
    assert body["aggregate_financial_tax"]["total"] == 21_000_000

    # 시나리오 3종, 52세~90세 = 39행
    assert set(body["scenarios"].keys()) == {"A", "B", "C"}
    rows = body["scenarios"]["A"]["cashflow_by_age"]
    assert rows[0]["age"] == 52 and rows[-1]["age"] == 90
    assert len(rows) == 39

    # 시나리오 B/C는 금융소득이 한도 이하로 조정되어 종합과세 비대상
    assert body["scenarios"]["B"]["financial_income_total"] <= 20_000_000
    assert body["scenarios"]["B"]["aggregate_subject"] is False
    assert body["scenarios"]["C"]["financial_income_total"] <= 10_000_000

    # 순 현금흐름 = 수입 − 세금 − 건보료
    for row in rows:
        assert row["net"] == row["income"] - row["tax"] - row["insurance"]

    assert len(body["disclaimers"]) >= 1


def test_validation_rejects_negative():
    bad = {**SAMPLE, "income": {"earned": -1}}
    assert client.post("/api/simulate", json=bad).status_code == 422
