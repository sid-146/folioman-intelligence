import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch

from src.folioman_intelligence.repository.fund import standardize_mutual_fund_payload
from src.folioman_intelligence.tools import fund as ft


@pytest.fixture
def sample_fund_data():
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
async def test_fund_tools_execution(sample_fund_data):
    with patch(
        "src.folioman_intelligence.analytics.fund.MutualFundRepository.get_fund_data",
        new=AsyncMock(return_value=sample_fund_data),
    ):
        # 1. Overview tool
        ov = await ft.get_fund_overview_tool.ainvoke({"identifier": "INF966L01721"})
        assert ov["name"] == "Quant Infrastructure Fund"

        # 2. Risk metrics tool
        risk = await ft.get_fund_risk_metrics_tool.ainvoke({"identifier": "INF966L01721"})
        assert risk["alpha"] == 5.38
        assert risk["sharpe_ratio"] == 0.514

        # 3. Top holdings tool
        holdings = await ft.get_fund_top_holdings_tool.ainvoke({"identifier": "INF966L01721", "top_n": 5})
        assert len(holdings["top_holdings"]) == 5

        # 4. Search stock tool
        search = await ft.search_stock_in_fund_tool.ainvoke({"identifier": "INF966L01721", "query": "Bharti"})
        assert search["is_held"] is True

        # 5. Comprehensive master tool
        comp = await ft.analyze_fund_tool.ainvoke({"identifier": "INF966L01721"})
        assert "overview" in comp
        assert "performance" in comp
        assert "risk_and_volatility" in comp


def test_fund_tools_list():
    assert len(ft.fund_tools) == 17
    tool_names = [t.name for t in ft.fund_tools]
    assert "analyze_fund_tool" in tool_names
    assert "get_fund_risk_metrics_tool" in tool_names
    assert "get_fund_top_holdings_tool" in tool_names
