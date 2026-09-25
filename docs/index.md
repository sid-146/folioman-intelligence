# Folioman Intelligence Documentation

Welcome to the technical documentation for **`folioman-intelligence`**.

`folioman-intelligence` is an intelligence, portfolio analytics, and AI reasoning service designed for [Folioman](https://github.com/codereverser/folioman) (a comprehensive mutual funds, equities, and portfolio management system). It bridges core financial portfolio data with external market intelligence and autonomous Large Language Model (LLM) agents.

---

## Key Capabilities

1. **Async Folioman API Client**:
    - High-performance asynchronous HTTP transport using `httpx`.
    - Complete JWT authentication lifecycle (`/api/auth/token/pair`, `/api/auth/token/refresh`).
    - Concurrency-safe single-flight token refresh locking with proactive expiration detection.
    - Transparent retry on HTTP 401 with refreshed credentials.
    - Strictly typed Pydantic models for investors, portfolios, holdings, NAV histories, transactions, valuations, and capital gains.

2. **TickerTape Scraper & Market Data Client**:
    - Asynchronous crawling and parsing of TickerTape XML sitemaps and mutual fund pages.
    - Extraction of Next.js server-side rendered hydration payloads (`__NEXT_DATA__`).
    - Persistent local caching of sitemaps in `.cache/tickertape/sitemaps/`.
    - Persistent SQLite lookup database (`.cache/tickertape/isin_lookup.db`) mapping Indian mutual fund ISINs directly to TickerTape entities, schemes, sectors, benchmarks, and NAVs.
    - On-demand heuristic ISIN resolver with token scoring.
    - Peer group clustering and category similarity search.

3. **Domain Repository Layer**:
    - Clean data access abstraction separating external web scraping and REST details from financial logic.
    - `MutualFundRepository`: Standardizes raw Next.js props into pure mutual fund schema dictionaries with 3-tier fallback resolution (ISIN lookup $\rightarrow$ direct slug/MFID $\rightarrow$ sitemap keyword search).
    - `PortfolioRepository`: Thin abstraction over Folioman client for investor summaries and holding details.

4. **Deterministic Financial Analytics**:
    - Modern Portfolio Theory (MPT) metrics: Alpha, Standard Deviation (volatility), Sharpe ratio, Sortino ratio, category benchmark outperformance.
    - Return analysis: Multi-horizon trailing returns (1Y, 3Y, 5Y, Since Inception) and historical rolling CAGR trajectory analysis.
    - Portfolio holdings & activity: Top 5/10 concentration percentages, high-conviction bets (>5%), 3-month accumulated vs trimmed stocks, and individual stock search.
    - Asset allocation: Equity, Derivatives/F&O, Debt/T-Bills, Cash & equivalents, REITs/InvITs, and SEBI/Scheme mandate compliance checking.
    - Sector dynamics: Sector weight distribution and historical macro sector rotation trends.
    - Peer benchmarking: Comparative matrix with category rankings for 1Y returns and 3Y CAGR.
    - Manager profile: Experience, qualification, AUM overseen, and multi-scheme workload.
    - Cost & taxation: Expense ratio vs category (in basis points), exit load penalty schedules, and capital gains tax rules.
    - Scorecard & red flags: 5-pillar health check (Performance, Risk, Cost, Composition, Red flags).
    - Portfolio-level analytics: Total invested, current valuation, absolute gains, XIRR, category mix, and buy transaction statistics.

5. **AI Tools & Autonomous Agents**:
    - 17 LangChain `@tool` definitions for mutual fund analysis.
    - 3 LangChain `@tool` definitions for portfolio advisory.
    - DeepAgents-based autonomous reasoning agents:
        - `ask_fund_agent`: Deep mutual fund due diligence, risk assessment, and peer comparison.
        - `ask_portfolio_agent`: Mutual fund portfolio advisor providing actionable portfolio rebalancing insights.
    - Real-time token streaming and formatted tool-call/output console visualization.

---

## Documentation Roadmap

| Section                                       | Description                                                                                          |
| :-------------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| **[Getting Started](getting-started.md)**     | System prerequisites, installation guide, environment configuration, and quick start code.           |
| **[Architecture](architecture.md)**           | Layered system design, data flow, security model, and concurrency architecture.                      |
| **[Folioman Client](folioman-client.md)**     | REST client details, JWT auth manager, endpoints, methods, models, and error handling.               |
| **[TickerTape Client](tickertape-client.md)** | Scraper engine, sitemap caching, SQLite ISIN lookup, resolver, indexer, and models.                  |
| **[Repositories](repositories.md)**           | Repository abstractions (`MutualFundRepository`, `PortfolioRepository`) and payload standardization. |
| **[Financial Analytics](analytics.md)**       | Complete calculation engine, formulas, MPT ratios, and portfolio analytics.                          |
| **[Tools & Agents](tools-and-agents.md)**     | LangChain tools registry, DeepAgents configuration, and execution workflows.                         |
| **[API Reference](api-reference.md)**         | Comprehensive class, method, attribute, parameter, and exception reference.                          |

---

## Quick Example

```python
import asyncio
from folioman_intelligence import FoliomanClient
from folioman_intelligence.analytics.fund import analyze_fund_comprehensive

async def main():
    # 1. Fetch investor portfolio from Folioman
    async with FoliomanClient.from_env() as client:
        investors = await client.investors.list()
        if investors:
            summary = await client.portfolio.get(investors[0].id)
            print(f"Investor: {investors[0].name} | Total Net Worth: ₹{summary.total_inr}")

    # 2. Run 360-degree due diligence on a mutual fund scheme by ISIN
    report = await analyze_fund_comprehensive("INF966L01721")
    print(f"Fund: {report['overview']['name']}")
    print(f"Sharpe Ratio: {report['risk_and_volatility']['sharpe_ratio']}")
    print(f"Top 5 Concentration: {report['top_holdings_concentration']['top_5_concentration_pct']}%")

if __name__ == "__main__":
    asyncio.run(main())
```
