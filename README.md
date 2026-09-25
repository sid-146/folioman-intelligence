# folioman-intelligence

Intelligence, portfolio analytics, and AI reasoning service for [Folioman](https://github.com/codereverser/folioman).

## Overview

`folioman-intelligence` bridges user portfolios with real-time financial market analytics and autonomous AI agents:

- **Autonomous AI Agents**: Multi-agent reasoning for mutual funds and portfolios using `deepagents` and `langchain`.
- **Deterministic Analytics Engine**: Rigorous, reproducible Modern Portfolio Theory (MPT) metrics (Alpha, Sharpe, Sortino, rolling CAGR, sector trends, mandate compliance).
- **Domain Repositories**: Normalizes and cleans financial payloads (`MutualFundRepository`, `PortfolioRepository`).
- **External Client Integrations**: Consumes standalone [`folioman-client`](https://github.com/sid-146/folioman-client) and [`tickertape-client`](https://github.com/sid-146/tickertape-client).

### Architecture

```
┌────────────────────────────────────────────────────────┐
│                  Autonomous AI Agents                  │
│       (ask_fund_agent, ask_portfolio_agent)            │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    LangChain Tools                     │
│         (fund_tools: 17, portfolio_tools: 3)           │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               Financial Analytics Engine               │
│         (analytics.fund, analytics.portfolio)          │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
┌─────────────▼────────────┐  ┌────────────▼─────────────┐
│   MutualFundRepository   │  │   PortfolioRepository    │
└─────────────┬────────────┘  └────────────┬─────────────┘
              │                            │
┌─────────────▼────────────┐  ┌────────────▼─────────────┐
│    tickertape-client     │  │     folioman-client      │
│  (TickerTapeClient SDK)  │  │  (FoliomanClient REST)   │
└─────────────┬────────────┘  └────────────┬─────────────┘
              │                            │
              ▼                            ▼
      [ TickerTape.in ]          [ Folioman REST API ]
```

---

## Installation & Setup

### Requirements
- Python `>= 3.12`
- Package manager: [`uv`](https://github.com/astral-sh/uv) (recommended)

### Install Dependencies
```bash
uv sync
```

### Environment Variables

Configure via environment variables or a `.env` file:

```env
# Folioman REST API
FOLIOMAN_BASE_URL=http://localhost:8000
FOLIOMAN_USERNAME=advisor
FOLIOMAN_PASSWORD=supersecret
FOLIOMAN_TIMEOUT=30.0

# LLM Configuration (for AI Agents)
LLM_MODEL_NAME=gpt-4
LLM_TEMPERATURE=0.7
LLM_API_KEY=your-openai-api-key
```

---

## Quick Usage

### 1. Folioman Client
```python
import asyncio
from folioman_intelligence import FoliomanClient

async def main():
    async with FoliomanClient.from_env() as client:
        investors = await client.investors.list()
        summary = await client.portfolio.get(investors[0].id)
        print(f"Net Worth: INR {summary.total_inr}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Mutual Fund Repository & Analytics
```python
import asyncio
from folioman_intelligence.repository.fund import MutualFundRepository
from folioman_intelligence.analytics.fund import get_fund_overview, get_risk_and_volatility

async def main():
    repo = MutualFundRepository()
    fund = await repo.get_fund_data("INF966L01721")  # by ISIN or slug
    overview = await get_fund_overview("INF966L01721", fund_data=fund)
    risk = await get_risk_and_volatility("INF966L01721", fund_data=fund)
    print(f"Fund: {overview['name']}, NAV: {overview['nav']}")
    print(f"Sharpe: {risk.get('sharpe_ratio')}, Alpha: {risk.get('alpha')}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Autonomous AI Agent
```python
import asyncio
from folioman_intelligence.agents.fund import ask_fund_agent

async def main():
    response = await ask_fund_agent("Analyze Quant Infrastructure Fund and evaluate its risk profile.")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Running Tests

Run unit and integration tests using `pytest`:

```bash
uv run pytest -v
```

Run test suite with code coverage:

```bash
uv run pytest --cov=src/folioman_intelligence
```

---

## Building Documentation

Documentation is built with Material for MkDocs:

```bash
uv run --group docs mkdocs build
# Or serve locally:
uv run --group docs mkdocs serve
```
