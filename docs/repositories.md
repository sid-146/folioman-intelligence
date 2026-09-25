# Data Repository Layer

The repository layer provides clean data access abstractions for the analytics engine and AI agents. It isolates financial calculations from transport protocols (HTTP requests, JWT headers) and web scraping details (Next.js payloads, HTML tags).

---

## Architectural Role

```
  [ Financial Analytics Layer ]          [ Autonomous AI Agents ]
               │                                   │
               └─────────────────┬─────────────────┘
                                 │ Clean Dictionaries / Domain Models
                                 ▼
                     ┌───────────────────────┐
                     │   Repository Layer    │
                     └───────────┬───────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
[ MutualFundRepository ]                      [ PortfolioRepository ]
  - Payload normalizer                          - Investor portfolio queries
  - Multi-tier ISIN / slug resolution           - Holding transaction queries
         │                                               │
         ▼                                               ▼
[ TickerTapeClient ]                            [ FoliomanClient ]
```

---

## Mutual Fund Repository (`MutualFundRepository`)

Located in `folioman_intelligence.repository.fund`.

### Purpose

Interacts with `TickerTapeClient` to fetch mutual fund details, strips frontend Next.js artifacts (`pageProps`, SSR hydrations), and normalizes the output into a standardized dictionary containing only mutual fund attributes.

### Initialization

```python
from folioman_intelligence.repository.fund import MutualFundRepository
from folioman_intelligence import TickerTapeClient

# Option 1: Automatic client lifecycle (instantiates TickerTapeClient internally)
repo = MutualFundRepository()

# Option 2: Inject an existing TickerTapeClient instance
async with TickerTapeClient() as client:
    repo = MutualFundRepository(client=client)
    fund_data = await repo.get_fund_data("INF966L01721")
```

### Methods

#### `get_fund_data(identifier, hint_name=None)`

```python
async def get_fund_data(
    self,
    identifier: str,
    hint_name: str | None = None,
) -> dict[str, Any]
```

Retrieves a normalized mutual fund information dictionary using a 3-tier resolution strategy:

1. **ISIN Lookup**: If `identifier` is a 12-character Indian ISIN starting with `"IN"` (e.g. `"INF966L01721"`), queries the SQLite lookup table and heuristic resolver.
2. **Direct Slug / MFID**: If `identifier` contains no spaces, attempts to fetch directly as a TickerTape slug (e.g. `"quant-infrastructure-fund-M_QUNG"`) or MFID (`"M_QUNG"`).
3. **Sitemap Token Fallback**: If direct fetch fails or `identifier` is a scheme name (e.g. `"Quant Infrastructure Fund"`), searches the cached sitemap using token overlap scoring.

- **Parameters**:
    - `identifier` (_str_): ISIN, URL slug, MFID, or scheme name.
    - `hint_name` (_str | None_): Optional scheme name hint to assist dynamic ISIN matching.
- **Returns**: `dict[str, Any]` (standardized mutual fund dictionary).

---

### Payload Normalization (`standardize_mutual_fund_payload`)

Transforms raw Next.js `pageProps` into a standardized dictionary containing the following sections:

| Category                   | Dictionary Keys                                                                                                                                                                                                                                                        | Description                                                                            |
| :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------- |
| **Identification & Info**  | `mf_id`, `name`, `full_name`, `isin`, `slug`, `nav`, `nav_1d_change`, `amc`, `amc_code`, `plan`, `option`, `category`, `subsector`, `subsector_desc`, `benchmark`, `risk_classification`, `inception_date`, `objective`, `scheme_type`, `cams_code`, `rta_scheme_code` | Scheme profile, current price, classification, benchmark, and registration codes.      |
| **Rules & Limits**         | `sip_allowed`, `lumpsum_allowed`, `investment_amount_info`, `exit_load_remarks`                                                                                                                                                                                        | Minimum SIP and lumpsum amounts, exit load penalty terms.                              |
| **Ratios**                 | `key_ratios`, `faq_ratios`                                                                                                                                                                                                                                             | P/E ratio, category P/E, Sharpe, Alpha, Sortino, volatility, expense ratio, AUM.       |
| **Returns**                | `trailing_returns`, `cagr_series`                                                                                                                                                                                                                                      | Trailing return windows (1M, 3M, 6M, 1Y, 3Y, 5Y) and rolling CAGR intervals.           |
| **Scorecard & Governance** | `scorecard`, `total_red_flags`                                                                                                                                                                                                                                         | Qualitative health check pillars and count of red flag companies held.                 |
| **Holdings**               | `current_allocation`, `asset_allocation_history`, `target_asset_allocation`                                                                                                                                                                                            | Underlying equity holdings, weights, 3-month weight changes, asset class distribution. |
| **Sectors**                | `sector_distribution`, `sector_weightage`, `sector_taxonomy`                                                                                                                                                                                                           | Current sector breakdown and historical sector allocation series.                      |
| **Peers**                  | `peers`, `peers_tab_data`                                                                                                                                                                                                                                              | Direct category competitors, peer returns, and peer expense ratios.                    |
| **Management**             | `fund_managers`, `amc_details`                                                                                                                                                                                                                                         | Manager names, experience, qualifications, AUM overseen, and AMC profile.              |
| **Taxation**               | `scheme_info`, `tax_meta`                                                                                                                                                                                                                                              | Capital gains tax rules (STCG, LTCG) and asset holding thresholds.                     |

---

## Portfolio Repository (`PortfolioRepository`)

Located in `folioman_intelligence.repository.portfolio`.

### Purpose

Provides a clean data retrieval interface over `FoliomanClient` to fetch raw investor summaries and scheme transaction ledgers.

### Methods

#### `get_portfolio(investor_id)`

```python
async def get_portfolio(self, investor_id: int) -> PortfolioSummary
```

Fetches the complete portfolio summary for an investor from the Folioman backend.

- **Parameters**:
    - `investor_id` (_int_): Investor unique identifier.
- **Returns**: `PortfolioSummary`

#### `get_holding(investor_id, security_id)`

```python
async def get_holding(self, investor_id: int, security_id: int, *, as_of: date | str | None = None) -> SchemeDetail
```

Fetches the detailed holding view for an individual scheme, including folio balances, full historical NAV points, and transaction ledger records.

- **Parameters**:
    - `investor_id` (_int_): Investor ID.
    - `security_id` (_int_): Security / Scheme ID.
- **Returns**: `SchemeDetail`

#### `get_value_series(investor_id, from_date=None, to_date=None, granularity="monthly")`

```python
async def get_value_series(
    self,
    investor_id: int,
    *,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
) -> ValueSeries
```

Reconstructs net worth and cumulative invested capital historical time series from transactions and NAV curves.

#### `get_valuation_status(investor_id)`

```python
async def get_valuation_status(self, investor_id: int) -> ValuationStatus
```

Queries calculation readiness, computed-through date, and provisional state of the valuation engine.

#### `get_transactions(investor_id)`

```python
async def get_transactions(self, investor_id: int) -> list[Transaction]
```

Returns all transaction ledger entries (buys, sells, switches, SIPs, dividends) for the investor.

#### `get_capital_gains_summary(investor_id, include_unreconciled=False)`

```python
async def get_capital_gains_summary(
    self, investor_id: int, *, include_unreconciled: bool = False
) -> list[CapitalGainsFyPoint]
```

Lists realized STCG and LTCG across financial years.

#### `get_capital_gains_report(investor_id, fy, include_unreconciled=False)`

```python
async def get_capital_gains_report(
    self, investor_id: int, *, fy: str, include_unreconciled: bool = False
) -> CapitalGainsReport
```

Fetches lot-level disposal records and realized capital gains for a specific financial year.

---

## Usage Example

```python
import asyncio
from folioman_intelligence.repository.fund import MutualFundRepository
from folioman_intelligence.repository.portfolio import PortfolioRepository

async def main():
    # 1. Access normalized fund data
    fund_repo = MutualFundRepository()
    fund = await fund_repo.get_fund_data("INF966L01721")
    print(f"Fund: {fund['name']} | NAV: ₹{fund['nav']}")
    print(f"Top Holding: {fund['current_allocation'][0]['title']} ({fund['current_allocation'][0]['latest']}%)")

    # 2. Access portfolio data
    portfolio_repo = PortfolioRepository()
    portfolio = await portfolio_repo.get_portfolio(investor_id=1)
    print(f"Portfolio Total: ₹{portfolio.total_inr} across {len(portfolio.holdings)} holdings")

if __name__ == "__main__":
    asyncio.run(main())
```
