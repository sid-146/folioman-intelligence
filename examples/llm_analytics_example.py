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
        """What are top funds from my portfolio and what are sector distribution of these funds."""
    )
)


pprint.pprint(response)
