"""Unit tests for MFParser."""

import json
from pathlib import Path
import pytest

from folioman_intelligence.clients.tickertape.errors import TickerTapeParseError
from folioman_intelligence.clients.tickertape.models import MutualFundDetail
from folioman_intelligence.clients.tickertape.parsers.mf import MFParser

SAMPLE_JSON_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "folioman_intelligence"
    / "clients"
    / "tickertape"
    / "sample_mf_parser_response.json"
)


def test_parse_from_dict():
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    parser = MFParser()
    fund = parser.parse(sample_data)

    assert isinstance(fund, MutualFundDetail)
    assert fund.mf_id == "M_QUNG"
    assert fund.name == "Quant Infrastructure Fund"
    assert fund.isin == "INF966L01721"
    assert fund.nav == 45.0937
    assert fund.slug == "/mutualfunds/quant-infrastructure-fund-M_QUNG"

    # Verify security info
    assert fund.security_info is not None
    assert fund.security_info.amc == "Quant Money Managers Limited"
    assert fund.security_info.option == "Growth"
    assert fund.security_info.sector == "Equity"

    # Verify meta
    assert fund.meta is not None
    assert fund.meta.isin == "INF966L01721"
    assert fund.meta.benchmark_index == "Nifty Infrastructure - TRI"
    assert fund.meta.plan == "Direct"
    assert fund.meta.expense_ratio == 0.65
    assert fund.meta.aum == 3163.7059000000004

    # Verify scorecard
    assert len(fund.scorecard) == 5
    scorecard_names = [item.name for item in fund.scorecard]
    assert "Performance" in scorecard_names
    assert "Risk" in scorecard_names
    assert "Cost" in scorecard_names
    assert "Composition" in scorecard_names
    assert "Red flags" in scorecard_names


def test_parse_from_html():
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    html = f"""
    <!DOCTYPE html>
    <html>
      <head><title>Mutual Fund</title></head>
      <body>
        <div>Some content</div>
        <script id="__NEXT_DATA__" type="application/json">
            {json.dumps(sample_data)}
        </script>
      </body>
    </html>
    """

    parser = MFParser()
    fund = parser.parse(html)

    assert fund.mf_id == "M_QUNG"
    assert fund.isin == "INF966L01721"
    assert fund.name == "Quant Infrastructure Fund"


def test_extract_isin():
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    parser = MFParser()
    isin = parser.extract_isin(sample_data)
    assert isin == "INF966L01721"


def test_parse_missing_next_data():
    html = "<html><body><p>No Next Data</p></body></html>"
    parser = MFParser()
    with pytest.raises(
        TickerTapeParseError, match="Could not find <script id='__NEXT_DATA__'>"
    ):
        parser.parse(html)


def test_parse_invalid_json():
    html = '<html><body><script id="__NEXT_DATA__">{invalid json</script></body></html>'
    parser = MFParser()
    with pytest.raises(
        TickerTapeParseError, match="Failed to decode __NEXT_DATA__ JSON"
    ):
        parser.parse(html)
