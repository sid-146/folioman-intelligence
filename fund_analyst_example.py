"""Funds Analyst Example.
Agent Layer       -> Autonomous Funds Analyst reasoning agent
"""

import asyncio
import sys
from typing import Optional

# Ensure console supports UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


async def demonstrate_agent_layer(query: Optional[str] = None):
    print("=" * 80)
    print("4. AGENT LAYER (Autonomous AI Funds Analyst - Live Execution)")
    print("=" * 80)

    from src.folioman_intelligence.agents.fund import ask_fund_agent

    if not query:
        query = (
            "Provide a concise analysis of Quant Infrastructure Fund (INF966L01721). "
            "What are its risk-adjusted returns (Sharpe and Alpha), its top 3 stock holdings, "
            "and how does it compare to peers like ICICI Pru Infrastructure Fund?"
        )

    print(f'User Query:\n"{query}"\n')
    print(
        "Running query through FundsAnalystAgent (with live tool-call streaming)...\n"
    )

    response = await ask_fund_agent(query)

    print("=" * 80)
    print("AGENT REPORT SUMMARY:")
    print("=" * 80)
    print(response.content)
    print(f"\nTotal Tools Executed by Agent: {len(response.tool_calls)}")
    for idx, tc in enumerate(response.tool_calls, start=1):
        print(f"  {idx}. {tc.get('name')} (args: {tc.get('input')})")
    print()


if __name__ == "__main__":
    asyncio.run(demonstrate_agent_layer())
