"""Unit tests for portfolio agent tools, response model, and workflow."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.folioman_intelligence.agents.portfolio import (
    PortfolioAgentResponse,
    ask_portfolio_agent,
)
from src.folioman_intelligence.tools.portfolio import get_portfolio_analysis


# ============================================================================
# Tests for PortfolioAgentResponse
# ============================================================================


def test_portfolio_agent_response():
    """Test PortfolioAgentResponse properties, dictionary interface, and string casting."""
    data = {
        "content": "Your portfolio is well balanced.",
        "tool_calls": [{"name": "get_portfolio_analysis", "input": {"investor_id": 1}}],
    }
    resp = PortfolioAgentResponse(data)

    assert resp.content == "Your portfolio is well balanced."
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["name"] == "get_portfolio_analysis"
    assert resp["content"] == "Your portfolio is well balanced."
    assert str(resp) == "Your portfolio is well balanced."

    # Empty response defaults
    empty_resp = PortfolioAgentResponse({})
    assert empty_resp.content == ""
    assert empty_resp.tool_calls == []
    assert str(empty_resp) == ""


# ============================================================================
# Tests for get_portfolio_analysis Tool
# ============================================================================


@pytest.mark.asyncio
async def test_get_portfolio_analysis_tool():
    """Test get_portfolio_analysis tool calling analyze_portfolio and converting Decimals/dates."""
    mock_analytics = {
        "currency": "INR",
        "total_value": Decimal("100000.50"),
        "as_of": date(2026, 3, 1),
        "top_3_holdings": ["Fund A", "Fund B"],
    }

    with patch(
        "src.folioman_intelligence.tools.portfolio.analyze_portfolio",
        new_callable=AsyncMock,
    ) as mock_analyze:
        mock_analyze.return_value = mock_analytics

        # Test default investor_id=1
        result_default = await get_portfolio_analysis.ainvoke({})
        mock_analyze.assert_awaited_with(1)
        # Verify JSON serializability and stringified types
        assert result_default["total_value"] == "100000.50"
        assert result_default["as_of"] == "2026-03-01"
        assert result_default["currency"] == "INR"

        # Test custom investor_id
        await get_portfolio_analysis.ainvoke({"investor_id": 42})
        mock_analyze.assert_awaited_with(42)


# ============================================================================
# Tests for ask_portfolio_agent Workflow
# ============================================================================


@pytest.mark.asyncio
async def test_ask_portfolio_agent_streaming_workflow():
    """Test ask_portfolio_agent processing streaming events including tool calls and text chunks."""

    # Define an async generator yielding simulated LangChain events
    async def mock_events(*args, **kwargs):
        # 1. Tool start
        yield {
            "event": "on_tool_start",
            "name": "get_portfolio_analysis",
            "data": {"input": {"investor_id": 1}},
        }
        # 2. Tool end (using artifact / content wrapper)
        tool_output_msg = MagicMock()
        tool_output_msg.artifact = None
        tool_output_msg.content = (
            '{"total_value": 150000, "top_3_holdings": ["Fund A"]}'
        )
        yield {
            "event": "on_tool_end",
            "name": "get_portfolio_analysis",
            "data": {"output": tool_output_msg},
        }
        # 3. Stream text chunk 1
        chunk1 = MagicMock()
        chunk1.content = "Based on your portfolio analysis, "
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": chunk1},
        }
        # 4. Stream text chunk 2
        chunk2 = MagicMock()
        chunk2.content = "your equity allocation is strong."
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": chunk2},
        }
        # 5. Model end
        yield {
            "event": "on_chat_model_end",
            "data": {},
        }

    with patch(
        "src.folioman_intelligence.agents.portfolio.agent.astream_events",
        side_effect=mock_events,
    ):
        response = await ask_portfolio_agent("Analyze my investments")

        assert isinstance(response, PortfolioAgentResponse)
        assert (
            response.content
            == "Based on your portfolio analysis, your equity allocation is strong."
        )
        assert len(response.tool_calls) == 1
        tool_call = response.tool_calls[0]
        assert tool_call["name"] == "get_portfolio_analysis"
        assert tool_call["input"] == {"investor_id": 1}
        assert tool_call["output"] == {
            "total_value": 150000,
            "top_3_holdings": ["Fund A"],
        }
