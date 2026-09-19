# LangChain Tools & Autonomous Agents

`folioman-intelligence` integrates deterministic financial analytics with Large Language Models (LLMs) using the [DeepAgents](https://github.com/deepagents/deepagents) framework and [LangChain](https://github.com/langchain-ai/langchain).

This layer bridges financial calculations into callable tools and provides autonomous agents for mutual fund due diligence and portfolio advisory.

---

## Architecture Overview

```
                      User Prompt / Application Query
                                     │
                                     ▼
                      [ Autonomous Agent Layer ]
                 (ask_fund_agent / ask_portfolio_agent)
                 Built on create_deep_agent + ChatOpenAI
                                     │
                 Agent Plans & Invokes Available Tools
                                     │
                                     ▼
                         [ LangChain Tool Layer ]
         (JSON serialization, input schema validation, docstrings)
                   │                                     │
                   ▼                                     ▼
             [ fund_tools ]                      [ portfolio_tools ]
               (17 tools)                             (2 tools)
                   │                                     │
                   ▼                                     ▼
        [ Fund Analytics Engine ]            [ Portfolio Analytics Engine ]
```

---

## Tool Registries

Every tool is decorated with LangChain's `@tool` decorator, features explicit argument type annotations, and passes its output through a JSON serialization helper (`_serialize`) to ensure dates and `Decimal` values are properly encoded.

### 1. Mutual Fund Tools (`tools/fund.py`)

The `fund_tools` list exposes 17 specialized tools:

| Tool Name | Key Parameters | Description |
| :--- | :--- | :--- |
| `analyze_fund_tool` | `identifier: str` | **Master Tool**: Comprehensive 360° audit combining overview, returns, MPT risk, top holdings, top sectors, fees, and health audit. |
| `get_fund_overview_tool` | `identifier: str` | Basic scheme metadata, AMC, category, benchmark, risk rating, current NAV, AUM, and investment limits. |
| `get_fund_trailing_returns_tool` | `identifier: str` | Multi-horizon trailing returns (1Y, 3Y CAGR, 5Y CAGR, Life CAGR). |
| `get_fund_cagr_history_tool` | `identifier: str` | Rolling CAGR statistics (min, max, median, spread) across historical market cycles. |
| `get_fund_risk_metrics_tool` | `identifier: str` | MPT ratios: Alpha, standard deviation, Sharpe, Sortino, and category outperformance. |
| `get_fund_valuation_tool` | `identifier: str` | Portfolio weighted P/E ratio compared against category average P/E. |
| `get_fund_top_holdings_tool` | `identifier: str`, `top_n: int = 10` | Top stock holdings, top 5/10 concentration percentages, and high-conviction bets (>5%). |
| `get_fund_portfolio_activity_tool`| `identifier: str` | Recent fund manager portfolio moves over 3 months (accumulated vs trimmed stocks). |
| `search_stock_in_fund_tool` | `identifier: str`, `query: str` | Searches for a specific company or ticker in the fund's portfolio. |
| `get_fund_asset_allocation_tool` | `identifier: str` | Current asset breakdown across Equity, F&O derivatives, Debt, Cash, and REITs. |
| `check_fund_mandate_compliance_tool` | `identifier: str` | Verifies adherence to SEBI and scheme asset class allocation limits. |
| `get_fund_sector_allocation_tool` | `identifier: str` | Current sector breakdown and top 3/5 sector concentration percentages. |
| `get_sector_rotation_trends_tool`| `identifier: str` | Multi-period sector changes highlighting expanding vs contracting sectors. |
| `get_fund_peer_comparison_tool` | `identifier: str` | Category peer matrix with 1Y return and 3Y CAGR rankings. |
| `get_fund_managers_info_tool` | `identifier: str` | Fund manager qualifications, years of experience, total AUM, and other schemes managed. |
| `get_cost_and_tax_tool` | `identifier: str` | Expense ratio vs category (in basis points), exit load penalty schedules, and tax rules. |
| `get_fund_health_audit_tool` | `identifier: str` | 5-pillar scorecard evaluations and governance red flags count. |

### 2. Portfolio Tools (`tools/portfolio.py`)

The `portfolio_tools` list exposes tools for analyzing investor portfolios:

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_portfolio_analysis` | `investor_id: int = 1` | Aggregated portfolio analysis: total net worth, total invested, absolute returns, XIRR, category mix, and top holdings. |
| `get_holding_details` | `investor_id: int`, `security_id: int` | Individual holding analysis: units held, invested amount, current market value, return %, average buy price, and buy transaction count. |

---

## Autonomous AI Agents

### 1. Funds Analyst Agent (`agents/fund.py`)

An autonomous agent specialized in deep-dive mutual fund research, due diligence, risk audits, and peer benchmarking.

#### System Prompt & Behavioral Guidelines

The agent is governed by strict system guidelines:
1. **Grounded Analytics**: Must use tools to fetch scheme information, returns, MPT ratios, top holdings, sector allocations, and peer comparisons.
2. **Fact vs Observation**: Must strictly distinguish between deterministic facts (from tool outputs) and qualitative commentary.
3. **Master vs Granular Tools**: Instructed to use `analyze_fund_tool` for broad reviews, and granular tools for specific inquiries.
4. **Objective Risk & Cost**: Always evaluates expense ratios relative to category averages and highlights red flags.

#### Execution Function (`ask_fund_agent`)

```python
async def ask_fund_agent(question: str) -> FundAgentResponse
```

- **Arguments**:
  - `question` (*str*): Natural language user inquiry.
- **Returns**: `FundAgentResponse` (contains `.content` string and `.tool_calls` list).

---

### 2. Portfolio Advisor Agent (`agents/portfolio.py`)

An autonomous agent acting as a mutual fund portfolio advisor.

#### System Prompt & Behavioral Guidelines

- Analyzes the user's investment portfolio using the portfolio tools.
- Never calculates financial metrics manually if tools provide them.
- Prohibited from inventing portfolio data or executing real-world trades.
- Provides actionable, concise rebalancing observations.

#### Execution Function (`ask_portfolio_agent`)

```python
async def ask_portfolio_agent(question: str) -> PortfolioAgentResponse
```

- **Arguments**:
  - `question` (*str*): User question about their portfolio.
- **Returns**: `PortfolioAgentResponse`.

---

## Live Event Streaming & Output Formatting

Both `ask_fund_agent` and `ask_portfolio_agent` use LangChain's `astream_events` protocol to provide real-time visibility in terminal environments:

1. **`on_tool_start`**: Intercepted and printed to the terminal with argument inspection:
   ```
   ======================================================================
   🛠️  [TOOL CALL] get_fund_top_holdings_tool
   ----------------------------------------------------------------------
   Arguments:
   {
     "identifier": "INF966L01721",
     "top_n": 5
   }
   ======================================================================
   ```

2. **`on_tool_end`**: Formatted tool output printed to the terminal:
   ```
   ======================================================================
   📦 [TOOL OUTPUT] get_fund_top_holdings_tool
   ----------------------------------------------------------------------
   Output:
   {
     "total_holdings_count": 48,
     "top_5_concentration_pct": 34.2
     ...
   }
   ======================================================================
   ```

3. **`on_chat_model_stream`**: Model tokens are flushed immediately to `sys.stdout`.

---

## Response Object: `FundAgentResponse` & `PortfolioAgentResponse`

The response returned by `ask_fund_agent` or `ask_portfolio_agent` behaves both as a standard dictionary and an object with dot-notation properties:

```python
response = await ask_fund_agent("Analyze Quant Infrastructure Fund")

# Access synthesized answer
print(response.content)

# Access list of tools invoked by the agent
print(f"Total tools called: {len(response.tool_calls)}")
for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}, Args: {tool_call['input']}")

# Standard string conversion
print(str(response))
```

---

## End-to-End Agent Example

```python
import asyncio
from folioman_intelligence.agents.fund import ask_fund_agent

async def main():
    prompt = (
        "Perform a due-diligence audit on Quant Infrastructure Fund (INF966L01721). "
        "Detail its 3-year CAGR, Sharpe ratio compared to its category, "
        "top 3 holdings, and any detected red flags."
    )
    
    response = await ask_fund_agent(prompt)
    print("\n\n=== FINAL AGENT ASSESSMENT ===")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```
