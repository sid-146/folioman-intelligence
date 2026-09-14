# folioman-intelligence

Intelligence, portfolio analytics, and AI reasoning service for [Folioman](https://github.com/codereverser/folioman).

## Folioman Python Client

A thin, async, typed Python client wrapping the Folioman REST API. It handles:

- Asynchronous HTTP transport via `httpx`
- JWT authentication (`/api/auth/token/pair`)
- Transparent access token refresh (`/api/auth/token/refresh`)
- Automatic retry on HTTP 401 with refreshed credentials
- Single-flight concurrent token refresh locking
- Typed response parsing into Pydantic models
- Clean, focused exception hierarchy

### Architecture

```
DeepAgents / LLM Reasoning
         ↓
Portfolio Analytics
         ↓
Folioman Client (this client)
         ↓
Folioman API (REST / OpenAPI)
```

Tokens and raw HTTP details are encapsulated within `FoliomanClient` and are never exposed to agents or analytics logic.

---

## Installation & Configuration

### Environment Variables

Configure via environment variables or a `.env` file:

```env
FOLIOMAN_BASE_URL=http://localhost:8000
FOLIOMAN_USERNAME=advisor
FOLIOMAN_PASSWORD=supersecret
FOLIOMAN_TIMEOUT=30.0
```

---

## Usage Example

```python
import asyncio
from folioman_intelligence import FoliomanClient, settings

async def main():
    # Instantiate from environment variables or settings:
    async with FoliomanClient.from_env() as client:
        # 1. Investors
        investors = await client.investors.list()
        investor = await client.investors.get(investors[0].id)
        print(f"Investor: {investor.name}, PAN: {investor.pan_masked}")

        # 2. Portfolio Summary & Holdings
        summary = await client.portfolio.get(investor.id)
        print(f"Net Worth: INR {summary.total_inr}, Holdings: {summary.holdings_count}")

        holdings = await client.holdings.list(investor.id)
        for h in holdings:
            print(f" - {h.name}: {h.units} units (₹{h.value_inr})")

        # 3. Scheme Details
        if holdings:
            scheme = await client.holdings.get(investor.id, holdings[0].security_id)
            print(f"Scheme ISIN: {scheme.security.isin}, NAV History points: {len(scheme.nav_history)}")

        # 4. Transactions
        txns = await client.transactions.list(investor.id)
        print(f"Total Transactions: {len(txns)}")

        # 5. Valuations Time-Series & Status
        status = await client.valuations.status(investor.id)
        print(f"Valuation Status: {status.status}")

        series = await client.valuations.list(investor.id, granularity="monthly")
        print(f"Valuation points: {len(series.points)}")

        # 6. Capital Gains
        fy_gains = await client.capital_gains.list(investor.id)
        if fy_gains:
            latest_fy = fy_gains[-1].fy
            report = await client.capital_gains.get(investor.id, fy=latest_fy)
            print(f"FY {report.fy} LTCG: INR {report.ltcg_total}, STCG: INR {report.stcg_total}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Available Client Resources

- **`client.investors`**:
    - `list(family_id=None, unaffiliated=False)`: List all accessible investors.
    - `get(investor_id)`: Fetch investor details (includes masked PAN).
- **`client.portfolio`**:
    - `get(investor_id, as_of=None)`: Fetch portfolio summary, net worth, XIRR, and asset allocation breakdown.
- **`client.holdings`**:
    - `list(investor_id, as_of=None)`: List all priced holdings under an investor.
    - `get(investor_id, security_id, as_of=None)`: Detailed view of a single holding (transactions, folios, NAV history).
- **`client.transactions`**:
    - `list(investor_id)`: List transaction ledger entries for an investor.
- **`client.valuations`**:
    - `list(investor_id, from_date=None, to_date=None, granularity="monthly")`: Net-worth historical series.
    - `status(investor_id)`: Check valuation computation readiness.
- **`client.capital_gains`**:
    - `list(investor_id, include_unreconciled=False)`: Realised STCG/LTCG by financial year.
    - `get(investor_id, fy="...", include_unreconciled=False)`: Realised capital gains report with disposal lots.

---

## Error Handling

Errors raised by the client inherit from `FoliomanError`:

| Exception               | Cause                                                                       |
| ----------------------- | --------------------------------------------------------------------------- |
| `FoliomanError`         | Base exception for all client errors                                        |
| `FoliomanAuthError`     | Authentication failure (bad credentials, expired or rejected refresh token) |
| `FoliomanNotFoundError` | Resource not found (HTTP 404)                                               |
| `FoliomanAPIError`      | Other API errors (HTTP 4xx/5xx) with `status_code` and `response_data`      |

---

## Running Tests

Tests use `pytest`, `pytest-asyncio`, and `respx` for mock-based HTTP assertions without requiring a live backend:

```bash
uv run pytest -v
```
