"""포트폴리오 모드: 상품 유형별 세금 분류와 비교 시뮬레이션 검증."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.portfolio import PortfolioHolding, portfolio_to_financial

client = TestClient(app)


def test_product_type_routing():
    """상품 유형이 올바른 금융소득 칸으로 분류되는지."""
    holdings = [
        PortfolioHolding(product_type="domestic_stock", amount=100_000_000, annual_yield_pct=4),   # 배당 400만
        PortfolioHolding(product_type="domestic_equity_etf", amount=100_000_000, annual_yield_pct=2),  # 분배 200만 (주식형)
        PortfolioHolding(product_type="foreign_etf", amount=100_000_000, annual_yield_pct=1.5),    # 해외 분배 150만
        PortfolioHolding(product_type="separate_or_taxfree", amount=100_000_000, annual_yield_pct=5),  # 비과세 500만
    ]
    m = portfolio_to_financial(holdings)
    fin = m["financial"]
    assert fin.dividend_domestic == 4_000_000
    assert fin.etf_domestic_equity_dist == 2_000_000
    assert fin.etf_foreign_dist == 1_500_000
    assert m["tax_free_income"] == 5_000_000          # 분리과세·비과세는 금융소득 제외
    assert m["total_value"] == 400_000_000
    # 금융소득 합계 = 400+200+150 = 750만 (비과세 500만 제외)


def test_dividend_vs_etf_strategy():
    """배당주 중심 vs 국내 주식형 ETF 중심: 같은 자산이라도 금융소득·종합과세가 갈린다."""
    base = {
        "basic": {"current_age": 50, "target_age": 60, "insurance_status": "지역",
                  "public_pension_start_age": 65, "annual_living_expense": 30_000_000},
        "pension": {}, "property": {},
        "portfolios": [
            {"label": "배당주 중심", "holdings": [
                {"product_type": "domestic_stock", "amount": 600_000_000, "annual_yield_pct": 4}]},
            {"label": "국내 주식형 ETF 중심", "holdings": [
                {"product_type": "domestic_equity_etf", "amount": 600_000_000, "annual_yield_pct": 4}]},
        ],
    }
    res = client.post("/api/simulate-portfolio", json=base)
    assert res.status_code == 200
    body = res.json()
    div, etf = body["portfolios"]

    # 배당주: 금융소득 2,400만 → 종합과세 대상
    assert div["financial_income_total"] == 24_000_000
    assert div["aggregate_subject"] is True
    # 국내 주식형 ETF: 분배금도 똑같이 2,400만으로 잡히면 동일하게 대상
    # (핵심 차이는 매매차익 비과세지만, 분배율을 같게 두면 분배금 자체는 동일)
    assert etf["financial_income_total"] == 24_000_000

    # 60세 시점 스냅샷이 존재하고 건보료가 산출된다
    assert div["target_snapshot"]["age"] == 60
    assert div["target_snapshot"]["health_insurance"]["monthly_premium"] > 0
    assert len(div["cashflow_by_age"]) == 31  # 60~90세


def test_low_yield_avoids_aggregate():
    """저분배 ETF로 금융소득을 2,000만 이하로 누르면 종합과세 비대상."""
    payload = {
        "basic": {"current_age": 50, "target_age": 60, "insurance_status": "피부양자"},
        "portfolios": [
            {"label": "저분배 ETF", "holdings": [
                {"product_type": "foreign_etf", "amount": 800_000_000, "annual_yield_pct": 1.2}]},  # 960만
        ],
    }
    body = client.post("/api/simulate-portfolio", json=payload).json()
    p = body["portfolios"][0]
    assert p["financial_income_total"] == 9_600_000
    assert p["aggregate_subject"] is False
    # 금융소득 1,000만 이하 + 피부양자 → 건보료 0 유지
    assert p["target_snapshot"]["health_insurance"]["dependent_eligible"] is True
    assert p["target_snapshot"]["health_insurance"]["monthly_premium"] == 0


def test_product_types_endpoint():
    body = client.get("/api/product-types").json()
    assert "domestic_equity_etf" in body
    assert "분배금" in body["domestic_equity_etf"]["note"]
