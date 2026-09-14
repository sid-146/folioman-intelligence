from src.folioman_intelligence.agents.portfolio import ask_portfolio_agent
import asyncio
import pprint

response = asyncio.run(
    ask_portfolio_agent(
        "Analyze my portfolio and provide summary. With Suggestions for improvement."
    )
)
pprint.pprint(response)
