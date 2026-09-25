import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch

from tickertape import MutualFundDetail
from src.folioman_intelligence.repository.fund import (
    MutualFundRepository,
    standardize_mutual_fund_payload,
)


@pytest.fixture
def sample_raw_props():
    sample_path = Path(__file__).parent / "fixtures" / "sample_mf_parser_response.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("props", {}).get("pageProps", {})


def test_standardize_mutual_fund_payload(sample_raw_props):
    fund_data = standardize_mutual_fund_payload(sample_raw_props)

    # Verify essential mutual fund fields
    assert fund_data["name"] == "Quant Infrastructure Fund"
    assert fund_data["isin"] == "INF966L01721"
    assert fund_data["mf_id"] == "M_QUNG"
    assert fund_data["nav"] == 45.0937
    assert fund_data["nav_1d_change"] == -1.096499999999999
    assert fund_data["category"] == "Equity"
    assert fund_data["subsector"] == "Sectoral Fund - Infrastructure"
    assert fund_data["benchmark"] == "Nifty Infrastructure - TRI"
    assert fund_data["risk_classification"] == "Very High"

    # Verify Next.js page plumbing was stripped
    assert "dehydratedState" not in fund_data
    assert "bannerConfig" not in fund_data
    assert "strapiFAQConfig" not in fund_data
    assert "strapiCrumbConfig" not in fund_data
    assert "isListicle" not in fund_data
    assert "tab" not in fund_data
    assert "pageType" not in fund_data
    assert "videos" not in fund_data

    # Verify structured mutual fund collections exist
    assert len(fund_data["current_allocation"]) == 49
    assert len(fund_data["fund_managers"]) == 4
    assert len(fund_data["cagr_series"]) == 27
    assert len(fund_data["peers_tab_data"]) == 6
    assert fund_data["total_red_flags"]["equity"] == 5


@pytest.mark.asyncio
async def test_repository_get_fund_data(sample_raw_props):
    mock_detail = MutualFundDetail(
        mf_id="M_QUNG",
        name="Quant Infrastructure Fund",
        isin="INF966L01721",
        raw_props=sample_raw_props,
    )

    mock_client = AsyncMock()
    mock_client.mf.get = AsyncMock(return_value=mock_detail)
    mock_client.mf.get_by_isin = AsyncMock(return_value=mock_detail)

    repo = MutualFundRepository(client=mock_client)

    # Test by slug
    data = await repo.get_fund_data("quant-infrastructure-fund-M_QUNG")
    assert data["name"] == "Quant Infrastructure Fund"
    assert data["isin"] == "INF966L01721"
    mock_client.mf.get.assert_awaited_once_with("quant-infrastructure-fund-M_QUNG")

    # Test by ISIN
    mock_client.mf.get.reset_mock()
    data_isin = await repo.get_fund_data("INF966L01721")
    assert data_isin["name"] == "Quant Infrastructure Fund"
    mock_client.mf.get_by_isin.assert_awaited_once_with("INF966L01721", hint_name=None)
