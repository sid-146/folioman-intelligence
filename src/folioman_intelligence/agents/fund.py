"""Funds Analyst Agent.

An autonomous AI agent for deep-dive mutual fund research,
due-diligence, risk audit, and peer benchmarking.
"""

from __future__ import annotations

import logging

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from folioman_intelligence.config import llm_settings
from folioman_intelligence.tools.fund import fund_tools
from folioman_intelligence.agents.logger import (
    AgentResponse,
    AgentRunLogger,
    run_agent,
)

logger = logging.getLogger(__name__)

# Chat Model initialization
model_name = getattr(
    llm_settings, "MODEL_NAME", getattr(llm_settings, "model_name", "gpt-4")
)
chat_model = ChatOpenAI(
    model=model_name,
    api_key=llm_settings.api_key,
    temperature=llm_settings.temperature,
    use_responses_api=True,
)

SYSTEM_PROMPT = """
You are a premier Mutual Fund Research and Due-Diligence Analyst.
Your objective is to thoroughly analyze mutual fund schemes, compare performance against benchmarks and peers, dissect underlying holdings and sector exposures, audit risk and volatility, and provide clear, fact-grounded investment assessments.

Key Guidelines:
1. Grounded Analytics: Always use the mutual fund tools to fetch scheme information, returns, MPT ratios (Sharpe, Sortino, Alpha), top holdings, sector allocation, and peer comparisons.
2. Fact vs Observation: Strictly distinguish between deterministic factual metrics (from tool outputs) and qualitative commentary.
3. Master Tool vs Granular Tools:
   - Use `analyze_fund_tool` when asked for an overall fund review, health audit, or broad due diligence.
   - Use specific tools (`get_fund_risk_metrics_tool`, `get_fund_top_holdings_tool`, `get_sector_rotation_trends_tool`, `get_fund_peer_comparison_tool`, etc.) when addressing targeted questions about volatility, holdings, manager actions, sectors, or fees.
4. Objective Risk & Cost Assessment: Always examine expense ratios relative to category averages, look for red flags in underlying holdings, and assess risk-adjusted return efficiency.
"""

agent = create_deep_agent(
    model=chat_model,
    tools=fund_tools,
    system_prompt=SYSTEM_PROMPT,
)


class FundAgentResponse(AgentResponse):
    """Response returned by ask_fund_agent.

    Acts as a dictionary containing 'content' and 'tool_calls',
    while supporting direct property access (.content, .tool_calls).
    """

    pass


agent_logger = AgentRunLogger(logger=logger, agent_name="Funds Analyst")


async def ask_fund_agent(
    question: str,
    logger: AgentRunLogger | None = None,
) -> FundAgentResponse:
    """Execute a query through the Funds Analyst Agent.

    Streams tokens and tool execution steps to stdout and returns the final response.
    """
    return await run_agent(
        agent=agent,
        question=question,
        logger=logger or agent_logger,
        response_cls=FundAgentResponse,
    )
