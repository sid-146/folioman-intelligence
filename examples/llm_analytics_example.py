from folioman_intelligence.agents.portfolio import ask_portfolio_agent
import asyncio
import pprint

# response = asyncio.run(
#     ask_portfolio_agent(
#         """Analyze my portfolio and provide summary. With Suggestions for improvement.
#         \ntell me extra details about quant Small Cap Fund - Direct Plan - Growth (Non Demat)"""
#     )
# )

# response = asyncio.run(ask_portfolio_agent("""How is my portfolio performing?"""))
# pprint.pprint(response)


# response = asyncio.run(
#     ask_portfolio_agent("""What are my biggest portfolio concentrations?""")
# )

# response = asyncio.run(
#     ask_portfolio_agent(
#         """I want you to evaluate each holding in detail and tell what are the red flags in my current folios?"""
#     )
# )

# response = asyncio.run(
#     ask_portfolio_agent(
#         """I want you to evaluate risk of the portfolio in detail and tell what are the red flags in my current portfolio?"""
#     )
# )

# response = asyncio.run(ask_portfolio_agent("""Analyse my portfolio."""))

# response = asyncio.run(
#     ask_portfolio_agent("""What are the biggest risk in my portfolio.""")
# )
# response = asyncio.run(ask_portfolio_agent("""Why is my portfolio concentrated?"""))
response = asyncio.run(
    ask_portfolio_agent(
        """
Analyze my portfolio comprehensively.

Start by giving me a concise overview of my current portfolio value, invested amount, absolute and percentage returns, and overall allocation.

Then investigate the portfolio in more detail:
- Identify my largest holdings and determine how concentrated my portfolio is.
- Identify the holdings that contribute most to the portfolio's current exposure and returns.
- Examine the risk characteristics of the portfolio, including concentration, diversification, volatility, drawdown, and major exposures.
- For the most significant funds/holdings, inspect their individual fund-level information where available and explain anything important that affects how I should understand their role in the portfolio.
- Identify any notable overlap or concentration across holdings if the available data supports it.
- Distinguish clearly between portfolio-level facts and fund-level observations.

Do not call every tool automatically. Decide which tools are actually necessary for each part of the investigation and use the minimum required tools.

Base all numerical claims on tool results. Do not invent missing information.

At the end, give me:
1. Portfolio summary
2. Key findings
3. Main concentration/risk observations
4. Important fund-level observations
5. Data gaps or things that cannot be determined from the available data

Do not recommend buying or selling anything. Focus on analysis and evidence.
"""
    )
)


pprint.pprint(response)
