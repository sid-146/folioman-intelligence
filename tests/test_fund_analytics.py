import json
from pathlib import Path
import pytest

from src.folioman_intelligence.analytics import fund as fa
from src.folioman_intelligence.repository.fund import standardize_mutual_fund_payload


@pytest.fixture(scope="module")
def fund_data():
    sample_path = (
        Path(__file__).parent.parent
        / "src"
        / "folioman_intelligence"
        / "clients"
        / "tickertape"
        / "sample_mf_parser_response.json"
    )
    with open(sample_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return standardize_mutual_fund_payload(raw.get("props", {}).get("pageProps", {}))


@pytest.mark.asyncio
async def test_get_fund_overview(fund_data):
    overview = await fa.get_fund_overview("test", fund_data=fund_data)
    assert overview["name"] == "Quant Infrastructure Fund"
    assert overview["nav"] == 45.0937
    assert overview["fund_age_years"] is not None and overview["fund_age_years"] > 10
    assert overview["aum_in_cr"] == 3163.7059000000004
    assert overview["category"] == "Equity"
    assert overview["subsector"] == "Sectoral Fund - Infrastructure"


@pytest.mark.asyncio
async def test_get_trailing_returns(fund_data):
    returns = await fa.get_trailing_returns("test", fund_data=fund_data)
    assert returns["return_1y"] == 8.88
    assert returns["return_3y_cagr"] == 16.83
    assert returns["return_5y_cagr"] == 18.12
    assert returns["life_cagr"] == 16.96


@pytest.mark.asyncio
async def test_get_cagr_history(fund_data):
    cagr_hist = await fa.get_cagr_history("test", fund_data=fund_data)
    assert cagr_hist["data_points_count"] == 27
    assert cagr_hist["min_cagr"] <= cagr_hist["median_cagr"] <= cagr_hist["max_cagr"]
    assert len(cagr_hist["observations"]) <= 10


@pytest.mark.asyncio
async def test_get_risk_and_volatility(fund_data):
    risk = await fa.get_risk_and_volatility("test", fund_data=fund_data)
    assert risk["alpha"] == 5.38
    assert risk["standard_deviation"] == 18.42
    assert risk["sharpe_ratio"] == 0.514
    assert risk["category_sharpe_ratio"] == 0.032
    assert risk["sharpe_outperformance_vs_category"] == 0.482
    assert "High Risk-Adjusted Return" in risk["risk_profile"]


@pytest.mark.asyncio
async def test_get_portfolio_valuation(fund_data):
    val = await fa.get_portfolio_valuation("test", fund_data=fund_data)
    assert val["portfolio_pe"] == 30.11
    assert val["category_pe"] == 27.22
    assert val["valuation_premium_pct"] > 0
    assert "premium" in val["valuation_status"]


@pytest.mark.asyncio
async def test_get_top_holdings(fund_data):
    holdings = await fa.get_top_holdings("test", top_n=5, fund_data=fund_data)
    assert holdings["total_holdings_count"] == 49
    assert len(holdings["top_holdings"]) == 5
    assert holdings["top_5_concentration_pct"] == pytest.approx(38.87, abs=0.1)
    assert holdings["top_holdings"][0]["title"] == "Samvardhana Motherson International Ltd"
    assert holdings["high_conviction_bets_count"] >= 5


@pytest.mark.asyncio
async def test_get_portfolio_activity(fund_data):
    act = await fa.get_portfolio_activity("test", fund_data=fund_data)
    assert act["accumulated_stocks_count"] > 0
    assert act["trimmed_stocks_count"] > 0
    # Adani Green should be in trimmed
    trimmed_titles = [t["title"] for t in act["top_trimmed"]]
    assert "Adani Green Energy Ltd" in trimmed_titles


@pytest.mark.asyncio
async def test_search_stock_in_fund(fund_data):
    result = await fa.search_stock_in_fund("test", query="Adani", fund_data=fund_data)
    assert result["is_held"] is True
    assert result["matches_count"] >= 2  # Adani Green & Adani Power

    not_found = await fa.search_stock_in_fund("test", query="NonExistentXYZCompany", fund_data=fund_data)
    assert not_found["is_held"] is False
    assert not_found["matches_count"] == 0


@pytest.mark.asyncio
async def test_get_asset_allocation(fund_data):
    alloc = await fa.get_asset_allocation("test", fund_data=fund_data)
    cur = alloc["current_allocation"]
    assert cur["equity_pct"] == 88.8
    assert cur["derivatives_fo_pct"] == 10.55
    assert alloc["has_active_derivatives"] is True


@pytest.mark.asyncio
async def test_check_mandate_compliance(fund_data):
    mandate = await fa.check_mandate_compliance("test", fund_data=fund_data)
    assert len(mandate["target_limits"]) >= 3


@pytest.mark.asyncio
async def test_get_sector_allocation(fund_data):
    sec = await fa.get_sector_allocation("test", fund_data=fund_data)
    assert sec["sectors_count"] > 10
    assert sec["top_3_sectors_concentration_pct"] > 0


@pytest.mark.asyncio
async def test_get_sector_rotation_trends(fund_data):
    rot = await fa.get_sector_rotation_trends("test", fund_data=fund_data)
    assert len(rot["expanding_sectors"]) > 0
    assert len(rot["contracting_sectors"]) > 0


@pytest.mark.asyncio
async def test_get_peer_comparison(fund_data):
    peers = await fa.get_peer_comparison("test", fund_data=fund_data)
    assert peers["peer_group_size"] == 6
    assert peers["rank_1y_return"] == "2 of 6"
    assert peers["rank_3y_cagr"] == "2 of 6"


@pytest.mark.asyncio
async def test_get_fund_managers_analysis(fund_data):
    mgr = await fa.get_fund_managers_analysis("test", fund_data=fund_data)
    assert mgr["fund_managers_count"] == 4
    names = [m["name"] for m in mgr["manager_profiles"]]
    assert "Sandeep Tandon" in names


@pytest.mark.asyncio
async def test_get_cost_and_tax_profile(fund_data):
    costs = await fa.get_cost_and_tax_profile("test", fund_data=fund_data)
    assert costs["expense_ratio_pct"] == 0.65
    assert costs["category_expense_ratio_pct"] == 1.36256
    assert costs["cost_advantage_basis_points"] > 70  # ~71.3 bps advantage
    assert len(costs["taxation_rules"]) >= 2


@pytest.mark.asyncio
async def test_get_fund_health_audit(fund_data):
    health = await fa.get_fund_health_audit("test", fund_data=fund_data)
    assert len(health["scorecard_pillars"]) == 5
    assert health["total_red_flags"]["equity"] == 5
    assert health["has_red_flags"] is True


@pytest.mark.asyncio
async def test_analyze_fund_comprehensive(fund_data):
    comp = await fa.analyze_fund_comprehensive("test", fund_data=fund_data)
    assert "overview" in comp
    assert "performance" in comp
    assert "risk_and_volatility" in comp
    assert "top_holdings_concentration" in comp
    assert "top_sectors" in comp
    assert "costs_and_taxes" in comp
    assert "health_and_red_flags" in comp
