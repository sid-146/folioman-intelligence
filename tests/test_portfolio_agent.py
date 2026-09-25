"""Unit tests for portfolio agent tools, helpers, and workflow."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.folioman_intelligence.tools.portfolio import get_portfolio_analysis
from src.folioman_intelligence.agents.portfolio import (
    PortfolioAgentResponse,
    _extract_final_text,
    _extract_text_chunk,
    _parse_output_value,
    _safe_format,
    ask_portfolio_agent,
)

# ============================================================================
# Tests for Helper Functions
# ============================================================================


def test_safe_format_with_dict_and_list():
    """Test _safe_format with dictionary and list structures."""
    data_dict = {"name": "Fund Alpha", "amount": 1000}
    formatted = _safe_format(data_dict)
    assert '"name": "Fund Alpha"' in formatted
    assert '"amount": 1000' in formatted

    data_list = [1, "two", {"three": 3}]
    formatted_list = _safe_format(data_list)
    assert '"three": 3' in formatted_list


def test_safe_format_with_json_and_eval_strings():
    """Test _safe_format with json strings and Python repr strings containing Decimals."""
    json_str = '{"status": "ok", "code": 200}'
    assert '"status": "ok"' in _safe_format(json_str)

    # String with Decimal and datetime representation
    py_repr = "{'balance': Decimal('123.45'), 'updated': datetime.date(2026, 3, 1)}"
    formatted_py = _safe_format(py_repr)
    assert '"balance": "123.45"' in formatted_py

    # Normal string that cannot be evaluated as dict/list
    plain_str = "Simple text notification"
    assert _safe_format(plain_str) == "Simple text notification"

    # None and empty values
    assert _safe_format(None) == ""


def test_parse_output_value():
    """Test _parse_output_value parsing logic for dicts, json strings, and fallbacks."""
    # Dict and list passthrough
    raw_dict = {"a": 1}
    assert _parse_output_value(raw_dict) == raw_dict

    raw_list = [1, 2]
    assert _parse_output_value(raw_list) == raw_list

    # JSON string
    assert _parse_output_value('{"valid": "json"}') == {"valid": "json"}

    # Python dict string representation with Decimal
    repr_str = "{'units': Decimal('55.5')}"
    parsed_repr = _parse_output_value(repr_str)
    assert isinstance(parsed_repr, dict)
    assert parsed_repr["units"] == Decimal("55.5")

    # Plain non-json string
    assert _parse_output_value("regular text") == "regular text"

    # Number / None
    assert _parse_output_value(12345) == 12345
    assert _parse_output_value(None) is None


def test_extract_text_chunk():
    """Test _extract_text_chunk with strings, lists, and dict blocks."""
    # Direct string
    assert _extract_text_chunk("chunk of text") == "chunk of text"

    # List of strings
    assert _extract_text_chunk(["hello ", "world"]) == "hello world"

    # List of structured blocks (e.g. text block + tool_use block)
    blocks = [
        {"type": "text", "text": "Analyzing holdings..."},
        {"type": "tool_use", "id": "call_1"},
    ]
    assert _extract_text_chunk(blocks) == "Analyzing holdings..."

    # Invalid / None content
    assert _extract_text_chunk(None) == ""
    assert _extract_text_chunk(12345) == ""


def test_extract_final_text():
    """Test _extract_final_text extracting text from AIMessages and raw structures."""
    # None or empty
    assert _extract_final_text(None) == ""

    # Message object with string content
    msg_obj = MagicMock()
    msg_obj.content = "Summary completed."
    assert _extract_final_text(msg_obj) == "Summary completed."

    # Message object with structured content blocks
    msg_blocks = MagicMock()
    msg_blocks.content = [
        {"type": "text", "text": "Recommendation: "},
        {"type": "text", "text": "Rebalance portfolio"},
    ]
    assert _extract_final_text(msg_blocks) == "Recommendation: Rebalance portfolio"

    # Raw string
    assert _extract_final_text("Direct content string") == "Direct content string"


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


@pytest.mark.asyncio
async def test_ask_portfolio_agent_artifact_output():
    """Test ask_portfolio_agent capturing tool output when raw_output has an artifact attribute."""

    async def mock_events(*args, **kwargs):
        yield {
            "event": "on_tool_start",
            "name": "get_portfolio_analysis",
            "data": {"input": {"investor_id": 2}},
        }
        tool_output_msg = MagicMock()
        tool_output_msg.artifact = {"metric": "value"}
        yield {
            "event": "on_tool_end",
            "name": "get_portfolio_analysis",
            "data": {"output": tool_output_msg},
        }
        chunk = MagicMock()
        chunk.content = "Done."
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": chunk},
        }

    with patch(
        "src.folioman_intelligence.agents.portfolio.agent.astream_events",
        side_effect=mock_events,
    ):
        response = await ask_portfolio_agent("Check portfolio")
        assert response.tool_calls[0]["output"] == {"metric": "value"}


@pytest.mark.asyncio
async def test_ask_portfolio_agent_fallback_text_extraction():
    """Test ask_portfolio_agent fallback when chunks are absent and text is only in on_chat_model_end."""

    async def mock_events(*args, **kwargs):
        generation_msg = MagicMock()
        generation_msg.content = "Fallback generated summary without stream chunks."
        gen_mock = MagicMock()
        gen_mock.message = generation_msg

        yield {
            "event": "on_chat_model_end",
            "data": {"output": MagicMock(generations=[gen_mock])},
        }

    with patch(
        "src.folioman_intelligence.agents.portfolio.agent.astream_events",
        side_effect=mock_events,
    ):
        response = await ask_portfolio_agent("What is my summary?")

        assert response.content == "Fallback generated summary without stream chunks."
        assert response.tool_calls == []
