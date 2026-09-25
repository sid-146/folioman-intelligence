import pytest
from unittest.mock import AsyncMock, patch

from src.folioman_intelligence.agents.fund import (
    FundAgentResponse,
    _extract_final_text,
    _extract_text_chunk,
    _parse_output_value,
    _safe_format,
    agent,
    ask_fund_agent,
)
from src.folioman_intelligence.tools.fund import fund_tools


def test_agent_initialization():
    assert agent is not None
    # Verify tools registered on agent
    registered_tools = getattr(agent, "tools", None)
    if registered_tools:
        assert len(registered_tools) == len(fund_tools)


def test_fund_agent_response_model():
    resp = FundAgentResponse(
        {
            "content": "Quant Infrastructure is a top performer with Sharpe 0.51.",
            "tool_calls": [
                {"name": "analyze_fund_tool", "input": {"identifier": "M_QUNG"}}
            ],
        }
    )
    assert "top performer" in resp.content
    assert str(resp) == resp.content
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["name"] == "analyze_fund_tool"


def test_safe_format_and_parsing():
    assert _safe_format(None) == ""
    assert '"a": 1' in _safe_format({"a": 1})
    assert _parse_output_value('{"valid": "json"}') == {"valid": "json"}
    assert _extract_text_chunk("plain text") == "plain text"
    assert _extract_text_chunk([{"type": "text", "text": "chunk"}]) == "chunk"
    assert _extract_final_text("final message") == "final message"


@pytest.mark.asyncio
async def test_ask_fund_agent_mock():
    mock_events = [
        {
            "event": "on_tool_start",
            "name": "get_fund_overview_tool",
            "data": {"input": {"identifier": "INF966L01721"}},
        },
        {
            "event": "on_tool_end",
            "name": "get_fund_overview_tool",
            "data": {"output": '{"name": "Quant Infrastructure Fund"}'},
        },
        {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "data": {
                "chunk": type(
                    "Chunk",
                    (),
                    {"content": "Quant Infrastructure Fund is direct/growth."},
                )()
            },
        },
        {
            "event": "on_chat_model_end",
            "name": "ChatOpenAI",
            "data": {},
        },
    ]

    async def mock_stream(*args, **kwargs):
        for ev in mock_events:
            yield ev

    with patch.object(agent, "astream_events", side_effect=mock_stream):
        response = await ask_fund_agent("Analyze Quant Infrastructure Fund")
        assert "Quant Infrastructure Fund is direct/growth." in response.content
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "get_fund_overview_tool"
