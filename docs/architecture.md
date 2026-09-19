# Architecture & System Design

This document describes the architectural philosophy, system layers, data flow pipelines, and concurrency/security principles of `folioman-intelligence`.

---

## Architectural Principles

1. **Separation of Concerns**:
    - **Transport & Raw Protocols**: Encapsulated within dedicated client libraries (`httpx`, JWT auth, web scraping).
    - **Data Normalization**: Handled by the Repository Layer, isolating upstream schema variations from domain logic.
    - **Deterministic Financial Computation**: Executed in a pure, reproducible Analytics Layer—never delegated to probabilistic LLM inference.
    - **Reasoning & Synthesis**: Delegated to AI Agents equipped with structured, strongly-typed tool interfaces.

2. **Defense Against Hallucinations**:
    - AI models are strictly prohibited from inventing portfolio metrics or calculating financial numbers on their own.
    - All financial figures (NAV, returns, Sharpe, Alpha, XIRR, expense ratio advantage) originate from deterministic analytics functions.

3. **Resilience & Caching**:
    - Two-tier caching strategy:
        - In-memory token management with skew absorption for Folioman API.
        - Disk-persisted sitemaps (`.cache/tickertape/sitemaps/*.json`) and persistent SQLite database (`.cache/tickertape/isin_lookup.db`) for market metadata.

---

## Layered Hierarchy

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Autonomous AI Agents                          │
│        (ask_fund_agent, ask_portfolio_agent, DeepAgents + OpenAI)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Tool Invocations
┌───────────────────────────────────▼────────────────────────────────────┐
│                           LangChain Tools                              │
│         (fund_tools: 17 tools, portfolio_tools: 2 tools)               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Pure Python Calls
┌───────────────────────────────────▼────────────────────────────────────┐
│                       Financial Analytics Engine                       │
│     (MPT Ratios, Rolling CAGR, Sector Rotation, Mandate Compliance)    │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
                   │ Standardized Data Dicts         │ Typed Pydantic Models
┌──────────────────▼─────────────┐ ┌─────────────────▼───────────────────┐
│     MutualFundRepository       │ │        PortfolioRepository          │
│ (Next.js Hydration Normalizer) │ │   (Investor & Holdings Access)      │
└──────────────────┬─────────────┘ └─────────────────┬───────────────────┘
                   │                                 │
┌──────────────────▼─────────────┐ ┌─────────────────▼───────────────────┐
│       TickerTapeClient         │ │           FoliomanClient            │
│  - Sitemaps & Parsers          │ │  - Async HTTP (httpx)               │
│  - SQLite ISIN Lookup DB       │ │  - JWT Auth Lifecycle & 401 Retry   │
│  - On-Demand ISIN Resolver     │ │  - Single-Flight Concurrency Lock   │
└──────────────────┬─────────────┘ └─────────────────┬───────────────────┘
                   │                                 │
                   ▼                                 ▼
         [ TickerTape.in ]                  [ Folioman REST API ]
       (Public Web Platform)                (Core Advisory Backend)
```

---

## Detailed Layer Breakdown

### 1. Configuration Layer (`config.py`)

- Centralized configuration using `pydantic_settings.BaseSettings`.
- Loads environment variables prefixed with `FOLIOMAN_` for Folioman API and `LLM_` for LLM agents.
- Automatically reads `.env` files from project root.

### 2. Clients Layer (`clients/`)

- **`clients.folioman`**:
    - `FoliomanClient`: Asynchronous HTTP client communicating with Folioman REST API.
    - `JWTAuthManager`: Manages token acquisition (`/api/auth/token/pair`), periodic refresh (`/api/auth/token/refresh`), and 401 recovery.
    - Resource sub-clients: `investors`, `portfolio`, `holdings`, `transactions`, `valuations`, `capital_gains`.
    - Pydantic models for strict type validation and serialization.
- **`clients.tickertape`**:
    - `TickerTapeClient`: Scrapes public pages and sitemaps.
    - `SitemapCacheManager`: Stores parsed sitemaps on disk to eliminate redundant web traffic.
    - `ISINLookupTable`: Embedded SQLite database (`isin_lookup.db`) indexed on ISIN, sector, subsector, AMC, and benchmark.
    - `ISINResolver`: Dynamically matches ISINs against sitemap slugs using tokenization and page verification.
    - `ISINIndexer`: Bulk crawler for populating the SQLite table concurrently.

### 3. Repositories Layer (`repository/`)

- **`MutualFundRepository`**:
    - Encapsulates resolution strategy:
        1. Try exact ISIN lookup in SQLite database.
        2. Try direct fetch if input is a valid slug or MFID.
        3. Fallback to sitemap token scoring.
    - Strips Next.js frontend plumbing (`__NEXT_DATA__`, `pageProps`) and outputs a clean, normalized dictionary via `standardize_mutual_fund_payload`.
- **`PortfolioRepository`**:
    - Retrieves raw portfolio summaries and holding transaction histories from Folioman API.

### 4. Financial Analytics Engine (`analytics/`)

- **`analytics.fund`**:
    - Independent, deterministic computational functions operating on clean data dictionaries.
    - Calculates MPT metrics (Alpha, Beta, Sharpe, Sortino, Category outperformance).
    - Evaluates rolling CAGR distributions and spread across cycles.
    - Computes top 5/10 stock concentrations, high-conviction holdings (>5% weight), and 3-month net manager activity (accumulated vs trimmed).
    - Verifies asset allocation compliance against statutory SEBI and scheme boundaries.
    - Computes sector allocations and identifies macro sector rotation patterns.
    - Builds peer comparison matrices and calculates quartile/category ranks.
    - Audits fund health across 5 scorecard pillars and evaluates portfolio red flags.
- **`analytics.portfolio`**:
    - Aggregates investor-level metrics: total invested value, current market value, absolute returns, XIRR, asset class mix, and top holdings by value/invested capital.
    - Analyzes individual holding transactions: average purchase price, total buy transactions, and returns percentage.

### 5. Tools Layer (`tools/`)

- Wraps analytics functions into LangChain `@tool` decorated functions.
- Provides comprehensive docstrings, typed input schemas, and JSON serialization (`_serialize`), guaranteeing safety for LLM consumption.
- Includes `fund_tools` (17 specialized tools) and `portfolio_tools` (2 portfolio-level tools).

### 6. Autonomous Agents Layer (`agents/`)

- Built on `deepagents.create_deep_agent` and `langchain_openai.ChatOpenAI`.
- Specialized system prompts enforce:
    - Mandatory use of deterministic tools for all numeric claims.
    - Clear distinction between factual data and analytical commentary.
    - Prohibition against fabricating portfolio holdings or executing real-world trades.
- Asynchronous event streaming (`astream_events`) intercepts:
    - `on_tool_start`: Formatted tool name and JSON arguments printed to console.
    - `on_tool_end`: Formatted output payload recorded and displayed.
    - `on_chat_model_stream`: Real-time token streaming directly to stdout.

---

## Data Flow Pipelines

### Flow A: Due Diligence on a Mutual Fund Scheme

```
User Query: "Analyze Sharpe and top holdings of Quant Infrastructure Fund"
                           │
                           ▼
                 [ ask_fund_agent ]
                           │
            Decides to invoke get_fund_risk_metrics_tool
            and get_fund_top_holdings_tool
                           │
                           ▼
                 [ LangChain Tools ]
                           │
                           ▼
             [ MutualFundRepository.get_fund_data ]
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
 [ ISIN in SQLite? ] ─── No ───► [ Query TickerTape HTML ]
        │                                     │
   Yes (Cache hit)                  Extract __NEXT_DATA__
        │                                     │
        └──────────────────┬──────────────────┘
                           ▼
          standardize_mutual_fund_payload()
                           │
                           ▼
            [ Pure Analytics Calculations ]
         (Alpha, Sharpe, Top 5 Concentration)
                           │
                           ▼
             JSON Output returned to Agent
                           │
                           ▼
         LLM Streams Grounded Response to User
```

---

## Concurrency, Resilience & Thread Safety

### 1. Single-Flight Token Refresh

In high-concurrency environments, multiple concurrent requests might encounter an expired JWT token simultaneously. To prevent race conditions or duplicate token minting requests:

- `JWTAuthManager` utilizes an `asyncio.Lock`.
- When an expired token is detected, exactly one coroutine executes the refresh request (`/api/auth/token/refresh`) while all other waiting coroutines wait and reuse the freshly minted token.

```python
async def get_valid_token(self, client: httpx.AsyncClient) -> str:
    if self._access_token and not _is_expired(self._access_token):
        return self._access_token

    async with self._lock:
        # Re-check under lock in case another coroutine refreshed it
        if self._access_token and not _is_expired(self._access_token):
            return self._access_token
        ...
```

### 2. Proactive Clock Skew Absorption

Tokens are refreshed **30 seconds** prior to actual expiration (`EXP_SKEW_SECONDS = 30`), eliminating intermittent 401 errors caused by network latency or slight server-client clock drift.

### 3. Rate-Limited Crawling

`ISINIndexer` utilizes an `asyncio.Semaphore(concurrency)` alongside a configurable inter-request delay (`delay=0.5`) to prevent IP throttling or denial-of-service when crawling TickerTape pages.

### 4. Thread-Safe SQLite Operations

`ISINLookupTable` uses connection timeouts (`timeout=30.0`), WAL-compatible schemas, indexed lookups, and atomic batch insertions (`conn.executemany(...)` inside a transaction block).

---

## Security Model

1. **Token Encapsulation**:
    - JWT tokens (access and refresh) are strictly private to `JWTAuthManager`.
    - Neither tokens nor raw Authorization headers are ever leaked to repository layers, analytics logic, or LLM agent prompts.

2. **Investor Privacy & Masked PAN**:
    - `InvestorDetail` exposes only masked PAN (`pan_masked`, e.g., `ABCDE****F`), preserving compliance with financial privacy standards.

3. **Read-Only Intelligence**:
    - The intelligence service does not implement transactional buy/sell execution endpoints, eliminating risk of unauthorized financial actions.
