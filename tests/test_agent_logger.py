"""Unit tests for the common AgentRunLogger, AgentResponse, and run_agent runner."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import io
import logging
from unittest.mock import MagicMock

import pytest

from src.folioman_intelligence.agents.logger import (
    AgentResponse,
    AgentRunLogger,
    configure_utf8_stdout,
    extract_final_text,
    extract_text_chunk,
    parse_output_value,
    run_agent,
    safe_format,
)


def test_utf8_configuration():
    """Verify configure_utf8_stdout runs without error."""
    configure_utf8_stdout()


def test_safe_format():
    """Test safe_format with various data types."""
    assert safe_format(None) == ""
    assert safe_format(123) == "123"
    assert '"key": "value"' in safe_format({"key": "value"})
    assert '"item"' in safe_format(["item"])
    assert '"status": 200' in safe_format('{"status": 200}')
    # Python repr with Decimal and date
    py_repr = "{'amount': Decimal('99.99'), 'as_of': datetime.date(2026, 9, 27)}"
    formatted = safe_format(py_repr)
    assert '"amount": "99.99"' in formatted
    # Plain text
    assert safe_format("plain message") == "plain message"


def test_parse_output_value():
    """Test parse_output_value converting strings and data structures."""
    assert parse_output_value({"a": 1}) == {"a": 1}
    assert parse_output_value([1, 2, 3]) == [1, 2, 3]
    assert parse_output_value('{"valid": "json"}') == {"valid": "json"}

    eval_str = "{'units': Decimal('10.5'), 'd': datetime.date(2026, 1, 1)}"
    parsed_eval = parse_output_value(eval_str)
    assert isinstance(parsed_eval, dict)
    assert parsed_eval["units"] == Decimal("10.5")

    assert parse_output_value("simple string") == "simple string"
    assert parse_output_value(42) == 42
    assert parse_output_value(None) is None


def test_extract_text_chunk():
    """Test extract_text_chunk with multiple chunk representations."""
    assert extract_text_chunk("direct text") == "direct text"
    assert extract_text_chunk(["a", "b", "c"]) == "abc"
    assert extract_text_chunk([{"type": "text", "text": "hello"}]) == "hello"
    assert extract_text_chunk([{"type": "tool_call"}]) == ""
    assert extract_text_chunk(None) == ""
    assert extract_text_chunk(100) == ""


def test_extract_final_text():
    """Test extract_final_text extraction from messages and models."""
    assert extract_final_text(None) == ""
    assert extract_final_text("raw string") == "raw string"

    msg = MagicMock()
    msg.content = "Final analysis"
    assert extract_final_text(msg) == "Final analysis"

    msg_blocks = MagicMock()
    msg_blocks.content = [
        {"type": "text", "text": "Part 1 "},
        {"type": "text", "text": "Part 2"},
    ]
    assert extract_final_text(msg_blocks) == "Part 1 Part 2"


def test_agent_response():
    """Test AgentResponse dictionary and attribute interface."""
    data = {
        "content": "Agent analysis result",
        "tool_calls": [{"name": "test_tool", "input": {"a": 1}, "output": {"b": 2}}],
    }
    resp = AgentResponse(data)
    assert resp.content == "Agent analysis result"
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0]["name"] == "test_tool"
    assert str(resp) == "Agent analysis result"
    assert resp["content"] == "Agent analysis result"

    empty_resp = AgentResponse({})
    assert empty_resp.content == ""
    assert empty_resp.tool_calls == []
    assert str(empty_resp) == ""


def test_agent_run_logger_tool_start_and_end():
    """Test AgentRunLogger logging tool calls and outputs to a stream."""
    buffer = io.StringIO()
    custom_logger = logging.getLogger("test_logger")
    agent_logger = AgentRunLogger(
        stream=buffer,
        logger=custom_logger,
        agent_name="TestAgent",
        line_width=40,
    )

    agent_logger.log_tool_start("search_tool", {"query": "Quant Fund"})
    agent_logger.log_tool_end("search_tool", '{"result": "success"}')

    output = buffer.getvalue()
    assert "🛠️  [TOOL CALL] search_tool" in output
    assert "Arguments:\n" in output
    assert '"query": "Quant Fund"' in output
    assert "📦 [TOOL OUTPUT] search_tool" in output
    assert '"result": "success"' in output


def test_agent_run_logger_tool_artifact_output():
    """Test log_tool_end extracting value from raw_output with artifact attribute."""
    buffer = io.StringIO()
    agent_logger = AgentRunLogger(stream=buffer)

    raw_output = MagicMock()
    raw_output.artifact = {"metric": "value"}
    parsed = agent_logger.log_tool_end("test_tool", raw_output)
    assert parsed == {"metric": "value"}
    assert '"metric": "value"' in buffer.getvalue()


def test_agent_run_logger_llm_streaming():
    """Test AgentRunLogger streaming LLM chunks and closing stream banner."""
    buffer = io.StringIO()
    agent_logger = AgentRunLogger(stream=buffer, line_width=40)

    # First chunk should print banner
    text1 = agent_logger.log_llm_chunk("Thinking...")
    assert text1 == "Thinking..."
    # Second chunk should directly write
    text2 = agent_logger.log_llm_chunk(" Here is the answer.")
    assert text2 == " Here is the answer."

    assert agent_logger.streaming_llm_active is True
    agent_logger.end_llm_stream()
    assert agent_logger.streaming_llm_active is False

    output = buffer.getvalue()
    assert "🤖 [LLM RESPONSE]" in output
    assert "Thinking... Here is the answer." in output


def test_agent_run_logger_tool_interrupts_llm_stream():
    """Test that a tool call automatically closes an active LLM stream banner."""
    buffer = io.StringIO()
    agent_logger = AgentRunLogger(stream=buffer)

    agent_logger.log_llm_chunk("Let me check the holdings.")
    assert agent_logger.streaming_llm_active is True

    # Starting a tool call while streaming should close LLM stream
    agent_logger.log_tool_start("get_holdings", {"fund": "123"})
    assert agent_logger.streaming_llm_active is False

    output = buffer.getvalue()
    assert "🤖 [LLM RESPONSE]" in output
    assert "🛠️  [TOOL CALL] get_holdings" in output


def test_agent_run_logger_model_end_fallback():
    """Test fallback text extraction in log_model_end."""
    buffer = io.StringIO()
    agent_logger = AgentRunLogger(stream=buffer)

    msg = MagicMock()
    msg.content = "Non-streamed fallback text"
    gen_mock = MagicMock()
    gen_mock.message = msg
    output_obj = MagicMock(generations=[gen_mock])

    extracted = agent_logger.log_model_end(output_obj, has_generated_chunks=False)
    assert extracted == "Non-streamed fallback text"

    # When chunks were already generated, should not return fallback
    extracted_skip = agent_logger.log_model_end(output_obj, has_generated_chunks=True)
    assert extracted_skip == ""


def test_agent_run_logger_verbose_false():
    """Test that verbose=False suppresses stream writes."""
    buffer = io.StringIO()
    agent_logger = AgentRunLogger(stream=buffer, verbose=False)

    agent_logger.log_tool_start("silent_tool", {"x": 1})
    agent_logger.log_tool_end("silent_tool", {"status": "ok"})
    agent_logger.log_llm_chunk("Silent response")
    agent_logger.end_llm_stream()

    assert buffer.getvalue() == ""


@pytest.mark.asyncio
async def test_run_agent_complete_flow():
    """Test run_agent orchestrating a full agent run with events."""
    buffer = io.StringIO()
    agent_logger = AgentRunLogger(stream=buffer)

    mock_events = [
        {
            "event": "on_tool_start",
            "name": "calc_metrics",
            "data": {"input": {"metric": "sharpe"}},
        },
        {
            "event": "on_tool_end",
            "name": "calc_metrics",
            "data": {"output": '{"sharpe": 1.45}'},
        },
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": "The Sharpe ratio is 1.45."},
        },
        {
            "event": "on_chat_model_end",
            "data": {},
        },
    ]

    mock_agent = MagicMock()

    async def mock_stream(*args, **kwargs):
        for ev in mock_events:
            yield ev

    mock_agent.astream_events = mock_stream

    # Test run_agent with string input
    response = await run_agent(
        mock_agent,
        "What is the fund Sharpe?",
        logger=agent_logger,
    )

    assert isinstance(response, AgentResponse)
    assert response.content == "The Sharpe ratio is 1.45."
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["name"] == "calc_metrics"
    assert response.tool_calls[0]["output"] == {"sharpe": 1.45}


@pytest.mark.asyncio
async def test_agent_logger_run_method():
    """Test AgentRunLogger.run instance method."""
    mock_agent = MagicMock()

    async def mock_stream(*args, **kwargs):
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": "Direct logger run."},
        }

    mock_agent.astream_events = mock_stream
    agent_logger = AgentRunLogger(verbose=False)

    class CustomResponse(AgentResponse):
        pass

    response = await agent_logger.run(
        mock_agent,
        {"messages": [{"role": "user", "content": "Hi"}]},
        response_cls=CustomResponse,
    )

    assert isinstance(response, CustomResponse)
    assert response.content == "Direct logger run."
