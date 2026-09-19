# Folioman Client

The `FoliomanClient` is a typed, asynchronous Python client for interacting with the Folioman REST API. It handles HTTP communication, JWT authentication lifecycles, proactive and reactive token refresh, concurrent locking, and response mapping into Pydantic models.

---

## Key Features

- **Asynchronous Transport**: Built on top of `httpx.AsyncClient`.
- **Automated JWT Lifecycle**: Obtains initial tokens from `/api/auth/token/pair`, automatically refreshes via `/api/auth/token/refresh`, and transparently retries requests on HTTP 401.
- **Concurrency-Safe Token Refresh**: Utilizes an internal `asyncio.Lock` to guarantee that only one concurrent refresh request runs at any time.
- **Proactive Expiry Absorption**: Evaluates token expiry using an embedded payload decoder and proactively refreshes 30 seconds before actual token expiration (`EXP_SKEW_SECONDS = 30`).
- **Typed Response Parsing**: Parses JSON payloads into Pydantic v2 models that handle `Decimal` serializations and ignore unknown extra attributes for forward-compatibility.
- **Structured Exception Hierarchy**: Maps HTTP status codes into specific client exceptions (`FoliomanAuthError`, `FoliomanNotFoundError`, `FoliomanAPIError`).

---

## Client Initialization

The client can be instantiated in three ways:

### 1. Directly with Arguments

```python
from folioman_intelligence import FoliomanClient

client = FoliomanClient(
    base_url="http://localhost:8000",
    username="advisor",
    password="supersecretpassword",
    timeout=30.0,
)
```

### 2. From a `FoliomanSettings` Instance

```python
from folioman_intelligence.config import FoliomanSettings
from folioman_intelligence import FoliomanClient

settings = FoliomanSettings(
    base_url="http://localhost:8000",
    username="advisor",
    password="supersecretpassword",
)
client = FoliomanClient.from_settings(settings)
```

### 3. From Environment Variables (`from_env`)

Automatically loads configuration from environment variables or `.env` file using the `FOLIOMAN_` prefix:

```python
from folioman_intelligence import FoliomanClient

client = FoliomanClient.from_env()
```

### Context Manager Usage

It is recommended to use `FoliomanClient` as an asynchronous context manager to ensure proper cleanup of underlying HTTP connections:

```python
async with FoliomanClient.from_env() as client:
    investors = await client.investors.list()
```

---

## Core Methods and Dispatcher

### `client.request(...)`

```python
async def request(
    self,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any | None = None,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> Any
```

Executes an authenticated HTTP request with automatic token injection, refresh, and retry on 401.

- **Parameters**:
  - `method` (*str*): HTTP method (`"GET"`, `"POST"`, `"PUT"`, `"DELETE"`, etc.).
  - `path` (*str*): Relative API path (e.g. `"/investors/1"` or `"/api/investors/1"`).
  - `params` (*dict[str, Any] | None*): Query string parameters.
  - `json` (*Any | None*): JSON payload for request body.
  - `headers` (*dict[str, str] | None*): Optional extra headers.
- **Returns**: Parsed JSON response, or `None` if the status code is 204.
- **Raises**: `FoliomanAuthError`, `FoliomanNotFoundError`, `FoliomanAPIError`.

### `client.close()`

```python
async def close(self) -> None
```

Closes the underlying `httpx.AsyncClient` transport if the client owns the transport instance.

---

## Resource Sub-Clients

`FoliomanClient` exposes its API through organized resource sub-clients:

### 1. `client.investors` (InvestorsResource)

Endpoints for querying advisor-accessible investors and investor details.

#### `list(...)`
```python
async def list(
    self,
    *,
    family_id: int | None = None,
    unaffiliated: bool = False,
) -> list[Investor]
```
Lists investors accessible to the authenticated advisor.
- **Arguments**:
  - `family_id` (*int | None*): Filter investors belonging to a specific family ID.
  - `unaffiliated` (*bool*): If `True`, only returns investors not affiliated with any family.
- **Returns**: `list[Investor]`

#### `get(...)`
```python
async def get(self, investor_id: int) -> InvestorDetail
```
Fetches detailed investor profile including masked PAN (`pan_masked`).
- **Arguments**:
  - `investor_id` (*int*): Unique identifier of the investor.
- **Returns**: `InvestorDetail`

---

### 2. `client.portfolio` (PortfolioResource)

Endpoints for querying aggregated portfolio summaries and asset mix.

#### `get(...)`
```python
async def get(
    self,
    investor_id: int,
    *,
    as_of: date | str | None = None,
) -> PortfolioSummary
```
Fetches full portfolio metrics, total net worth, day change, XIRR, asset class mix, AMC mix, category breakdown, and holdings list.
- **Arguments**:
  - `investor_id` (*int*): Unique identifier of the investor.
  - `as_of` (*date | str | None*): Optional point-in-time valuation date (`YYYY-MM-DD`).
- **Returns**: `PortfolioSummary`

---

### 3. `client.holdings` (HoldingsResource)

Endpoints for querying priced holdings and individual scheme histories.

#### `list(...)`
```python
async def list(
    self,
    investor_id: int,
    *,
    as_of: date | str | None = None,
) -> list[Holding]
```
Returns all priced holdings under an investor (derived from the portfolio summary).
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
  - `as_of` (*date | str | None*): Point-in-time valuation date.
- **Returns**: `list[Holding]`

#### `get(...)`
```python
async def get(
    self,
    investor_id: int,
    security_id: int,
    *,
    as_of: date | str | None = None,
) -> SchemeDetail
```
Fetches detailed view of a single scheme holding, including folio balances, full historical NAV points, and transactions.
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
  - `security_id` (*int*): Security / Scheme ID.
  - `as_of` (*date | str | None*): Optional point-in-time date.
- **Returns**: `SchemeDetail`

---

### 4. `client.transactions` (TransactionsResource)

Endpoints for accessing raw transaction ledgers.

#### `list(...)`
```python
async def list(self, investor_id: int) -> list[Transaction]
```
Returns all transaction ledger records (buys, sells, switches, dividends, STP, SIP) for an investor.
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
- **Returns**: `list[Transaction]`

---

### 5. `client.valuations` (ValuationsResource)

Endpoints for historical net-worth series and valuation engine status.

#### `list(...)`
```python
async def list(
    self,
    investor_id: int,
    *,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
) -> ValueSeries
```
Reconstructs net-worth historical time series from transactions and NAV curves.
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
  - `from_date` (*date | str | None*): Start date of the time series.
  - `to_date` (*date | str | None*): End date of the time series.
  - `granularity` (*Literal["daily", "weekly", "monthly"]*): Time-series sampling frequency. Default is `"monthly"`.
- **Returns**: `ValueSeries`

#### `status(...)`
```python
async def status(self, investor_id: int) -> ValuationStatus
```
Queries current calculation readiness and staleness status of the portfolio valuation engine.
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
- **Returns**: `ValuationStatus`

---

### 6. `client.capital_gains` (CapitalGainsResource)

Endpoints for tax and realized capital gains reporting.

#### `list(...)`
```python
async def list(
    self,
    investor_id: int,
    *,
    include_unreconciled: bool = False,
) -> list[CapitalGainsFyPoint]
```
Lists realized STCG and LTCG totals broken down across financial years.
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
  - `include_unreconciled` (*bool*): Whether to include unreconciled transactions.
- **Returns**: `list[CapitalGainsFyPoint]`

#### `get(...)`
```python
async def get(
    self,
    investor_id: int,
    *,
    fy: str,
    include_unreconciled: bool = False,
) -> CapitalGainsReport
```
Fetches realized capital gains report for a specific financial year, including granular disposal lots.
- **Arguments**:
  - `investor_id` (*int*): Investor ID.
  - `fy` (*str*): Financial year string (e.g. `"2024-25"`).
  - `include_unreconciled` (*bool*): Whether to include unreconciled transactions.
- **Returns**: `CapitalGainsReport`

---

## Data Models

All models inherit from `FoliomanBaseModel`, which automatically serializes `Decimal` instances to standard Python `float` during dictionary conversion and ignores unexpected backend fields.

### Core Models Summary

| Model Name | Key Attributes |
| :--- | :--- |
| `Investor` | `id: int`, `name: str`, `email: str`, `is_huf: bool`, `family_id: int \| None`, `has_pan: bool`, `pan_locked: bool` |
| `InvestorDetail` | Inherits `Investor`; adds `pan_masked: str` |
| `Holding` | `security_id: int`, `name: str`, `security_type: str`, `units: Decimal`, `value_inr: Decimal \| None`, `invested_inr: Decimal \| None`, `latest_nav: Decimal \| None`, `return_pct: float \| None`, `xirr: float \| None`, `day_change_inr: Decimal \| None` |
| `SchemeRef` | `id: int`, `name: str`, `isin: str`, `symbol: str`, `amc: str \| None`, `category: str \| None` |
| `SchemeDetail` | `security: SchemeRef`, `as_of: date`, `units: Decimal`, `value_inr: Decimal`, `xirr: float`, `folios: list[FolioBalance]`, `nav_history: list[NavPoint]`, `transactions: list[Transaction]` |
| `PortfolioSummary` | `investor_id: int`, `as_of: date`, `total_inr: Decimal`, `holdings_count: int`, `xirr: float \| None`, `asset_mix: list[AssetMixRow]`, `amc_mix: list[AllocationBucket]`, `category_mix: list[AllocationBucket]`, `holdings: list[Holding]` |
| `Transaction` | `id: int`, `investor_id: int`, `security_id: int`, `date: date`, `transaction_type: str`, `units: Decimal`, `nav_or_price: Decimal`, `amount: Decimal \| None` |
| `ValueSeries` | `start: date`, `end: date`, `granularity: str`, `points: list[ValueSeriesPoint]` |
| `CapitalGainsReport`| `fy: str`, `stcg_total: Decimal`, `ltcg_total: Decimal`, `rows: list[CapitalGainRow]`, `disclaimer: str` |

---

## Exception Hierarchy

All exceptions raised by the Folioman client inherit from `FoliomanError`:

```
FoliomanError (base exception)
├── FoliomanAuthError (HTTP 401, bad credentials, expired/rejected refresh token)
├── FoliomanNotFoundError (HTTP 404 resource missing)
└── FoliomanAPIError (HTTP 4xx / 5xx API errors, contains status_code & response_data)
```

### Exception Attributes

`FoliomanAPIError` provides structured access to HTTP status codes and backend response data:

```python
from folioman_intelligence import FoliomanClient, FoliomanAPIError, FoliomanAuthError

async with FoliomanClient.from_env() as client:
    try:
        await client.investors.get(99999)
    except FoliomanAPIError as exc:
        print(f"Status Code: {exc.status_code}")
        print(f"Backend Error: {exc.response_data}")
```
