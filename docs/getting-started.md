# Getting Started

This guide walks through prerequisites, installation, environment setup, and running your first queries with `folioman-intelligence`.

---

## Prerequisites

Before setting up `folioman-intelligence`, ensure your development environment satisfies the following requirements:

1. **Python Version**:
   - Python **3.12** or newer is required (`requires-python = ">=3.12"`).
   - Verify your installed version:
     ```bash
     python --version
     ```

2. **Package Manager**:
   - [uv](https://github.com/astral-sh/uv) is the recommended fast Python package manager and build tool.
   - Alternatively, standard `pip` and `virtualenv` can be used.

3. **External Dependencies**:
   - Running instance of [Folioman](https://github.com/codereverser/folioman) (usually on `http://localhost:8000`) for portfolio analytics and investor data.
   - Valid credentials (username and password) on the target Folioman instance.
   - An OpenAI API key (or compatible LLM endpoint) if using the autonomous reasoning agents (`ask_fund_agent`, `ask_portfolio_agent`).
   - Internet connectivity to query TickerTape (`https://www.tickertape.in`) for live mutual fund scraping and sitemap indexing.

---

## Installation

### Method 1: Using `uv` (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/codereverser/folioman-intelligence.git
   cd folioman-intelligence
   ```

2. Install dependencies and synchronize virtual environment:
   ```bash
   uv sync
   ```

3. (Optional) Run commands directly using `uv run`:
   ```bash
   uv run pytest -v
   ```

### Method 2: Using standard `pip` and `venv`

1. Create and activate a Python 3.12+ virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the project in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

---

## Environment Configuration

Configuration is managed via Pydantic Settings (`pydantic_settings.BaseSettings`) and loaded from environment variables or a `.env` file located at the project root.

### Setup `.env` File

Copy the template file `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Configuration Variables Reference

#### 1. Folioman Client Settings (`FOLIOMAN_` Prefix)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `FOLIOMAN_BASE_URL` | String | `http://localhost:8000` | The base URL of the running Folioman REST API backend. |
| `FOLIOMAN_USERNAME` | String | `""` | Username / advisor credential for JWT token generation. |
| `FOLIOMAN_PASSWORD` | String | `""` | Password corresponding to the user/advisor account. |
| `FOLIOMAN_TIMEOUT` | Float | `30.0` | Default timeout in seconds for HTTP requests to Folioman. |

#### 2. LLM Settings (`LLM_` Prefix)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `LLM_MODEL_NAME` | String | `gpt-4` | LLM model identifier (e.g., `gpt-4o`, `gpt-4`, `gpt-3.5-turbo`). |
| `LLM_TEMPERATURE` | Float | `0.7` | Sampling temperature for LLM responses (lower for deterministic factual output). |
| `LLM_MAX_TOKENS` | Integer | `2048` | Maximum output tokens generated per completion step. |
| `LLM_API_KEY` | Secret | `None` | OpenAI API key (or OpenAI-compatible API key). |

### Example `.env` File

```env
# Folioman REST API Settings
FOLIOMAN_BASE_URL=http://localhost:8000
FOLIOMAN_USERNAME=advisor
FOLIOMAN_PASSWORD=supersecret
FOLIOMAN_TIMEOUT=30.0

# LLM Agent Configuration
LLM_MODEL_NAME=gpt-4o
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Verifying the Installation

Execute the test suite to ensure the client, parser, storage, and analytics modules are fully functioning:

```bash
# Using uv
uv run pytest -v

# Using active virtual environment
pytest -v
```

All mock tests use `respx` to test HTTP routes without requiring a live backend server.

---

## Quick Start Tutorials

### 1. Querying Investor Portfolio Data

```python
import asyncio
from folioman_intelligence import FoliomanClient

async def main():
    async with FoliomanClient.from_env() as client:
        # List all accessible investors
        investors = await client.investors.list()
        for inv in investors:
            print(f"ID: {inv.id} | Name: {inv.name} | Family ID: {inv.family_id}")

        if investors:
            investor_id = investors[0].id

            # Get portfolio summary
            summary = await client.portfolio.get(investor_id)
            print(f"\nNet Worth: ₹{summary.total_inr}")
            print(f"Holdings Count: {summary.holdings_count}")
            print(f"XIRR: {summary.xirr}%")

            # List individual scheme holdings
            holdings = await client.holdings.list(investor_id)
            for h in holdings:
                print(f" - {h.name}: {h.units} units (Current: ₹{h.value_inr}, Invested: ₹{h.invested_inr})")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Looking Up Mutual Funds via TickerTape

```python
import asyncio
from folioman_intelligence import TickerTapeClient

async def main():
    async with TickerTapeClient() as client:
        # Resolve fund by ISIN
        isin = "INF966L01721"
        hint = "Quant Infrastructure Fund - Direct Plan - Growth"
        fund = await client.mf.get_by_isin(isin, hint_name=hint)

        if fund:
            print(f"Scheme: {fund.name}")
            print(f"NAV: ₹{fund.nav}")
            print(f"AUM: ₹{fund.meta.aum} Cr" if fund.meta else "AUM: N/A")
            print(f"Expense Ratio: {fund.meta.expense_ratio}%" if fund.meta else "ER: N/A")

        # Discover peer schemes in the same category
        peers = client.mf.get_peers(isin, limit=3)
        print(f"\nCategory Peers ({len(peers)}):")
        for peer in peers:
            print(f" - {peer.name} (ISIN: {peer.isin})")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Interacting with the AI Funds Analyst Agent

```python
import asyncio
from folioman_intelligence.agents.fund import ask_fund_agent

async def main():
    query = (
        "Analyze Quant Infrastructure Fund (INF966L01721). "
        "Summarize its Sharpe ratio, top 3 stock holdings, and expense ratio relative to category."
    )
    response = await ask_fund_agent(query)
    print("\nAgent Final Assessment:\n")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```
