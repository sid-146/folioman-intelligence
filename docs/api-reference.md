# API Reference

Complete technical reference for all public classes, methods, models, functions, attributes, and exceptions in `folioman-intelligence`.

---

## 1. Configuration (`folioman_intelligence.config`)

### `FoliomanSettings`

Configuration model for the Folioman client, backed by environment variables with the `FOLIOMAN_` prefix.

- **Attributes**:
    - `base_url` (_str_): Folioman REST API base URL. Default: `"http://localhost:8000"`.
    - `username` (_str_): Username for authentication. Default: `""`.
    - `password` (_str_): Password for authentication. Default: `""`.
    - `timeout` (_float_): Request timeout in seconds. Default: `30.0`.
- **Properties**:
    - `folioman_url` (_str_): Alias for `base_url`.
    - `folioman_username` (_str_): Alias for `username`.
    - `folioman_password` (_str_): Alias for `password`.

### `LLMSettings`

Configuration model for AI agents, backed by environment variables with the `LLM_` prefix.

- **Attributes**:
    - `MODEL_NAME` (_str_): LLM model identifier. Default: `"gpt-4"`.
    - `temperature` (_float_): Sampling temperature. Default: `0.7`.
    - `max_tokens` (_int_): Maximum generation token length. Default: `2048`.
    - `api_key` (_SecretStr | None_): API key for OpenAI or OpenAI-compatible endpoint.

### Global Instances

- `settings`: Default pre-instantiated `FoliomanSettings()` instance.
- `llm_settings`: Default pre-instantiated `LLMSettings()` instance.

---

## 2. Folioman Client (`folioman_client`)

### `FoliomanClient`

Primary async client for the Folioman REST API.

#### Constructor

```python
FoliomanClient(
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    timeout: float = 30.0,
    http_client: httpx.AsyncClient | None = None,
)
```

#### Class Methods

- `from_settings(settings: FoliomanSettings) -> FoliomanClient`: Creates client from a settings object.
- `from_env() -> FoliomanClient`: Creates client using environment variables.

#### Core Methods

- `async request(method: str, path: str, *, params=None, json=None, headers=None, **kwargs) -> Any`: Executes authenticated request with auto-refresh and 401 retry.
- `async close() -> None`: Closes the underlying HTTP client transport.

#### Resource Attributes

- `investors: InvestorsResource`
- `portfolio: PortfolioResource`
- `holdings: HoldingsResource`
- `transactions: TransactionsResource`
- `valuations: ValuationsResource`
- `capital_gains: CapitalGainsResource`

---

### Resource Classes

#### `InvestorsResource`

- `async list(*, family_id: int | None = None, unaffiliated: bool = False) -> list[Investor]`
- `async get(investor_id: int) -> InvestorDetail`

#### `PortfolioResource`

- `async get(investor_id: int, *, as_of: date | str | None = None) -> PortfolioSummary`

#### `HoldingsResource`

- `async list(investor_id: int, *, as_of: date | str | None = None) -> list[Holding]`
- `async get(investor_id: int, security_id: int, *, as_of: date | str | None = None) -> SchemeDetail`

#### `TransactionsResource`

- `async list(investor_id: int) -> list[Transaction]`

#### `ValuationsResource`

- `async list(investor_id: int, *, from_date: date | str | None = None, to_date: date | str | None = None, granularity: Literal["daily", "weekly", "monthly"] = "monthly") -> ValueSeries`
- `async status(investor_id: int) -> ValuationStatus`

#### `CapitalGainsResource`

- `async list(investor_id: int, *, include_unreconciled: bool = False) -> list[CapitalGainsFyPoint]`
- `async get(investor_id: int, *, fy: str, include_unreconciled: bool = False) -> CapitalGainsReport`

---

### Authentication Manager (`JWTAuthManager`)

- `has_tokens: bool`: True if manager holds access or refresh tokens.
- `clear() -> None`: Clears cached tokens.
- `async get_valid_token(client: httpx.AsyncClient) -> str`: Returns valid token, refreshing proactively if within skew seconds.
- `async force_refresh(client: httpx.AsyncClient) -> str`: Forces token refresh or re-authentication after receiving 401.

---

### Folioman Data Models

- `Investor`: `id`, `name`, `email`, `is_huf`, `relation`, `family_id`, `has_pan`, `pan_locked`, `created_at`, `updated_at`.
- `InvestorDetail`: Inherits `Investor`; adds `pan_masked`.
- `Holding`: `security_id`, `name`, `security_type`, `symbol`, `amc`, `category`, `units`, `value_inr`, `invested_inr`, `latest_nav`, `return_pct`, `xirr`, `day_change_inr`, `day_change_pct`.
- `SchemeRef`: `id`, `name`, `isin`, `symbol`, `security_type`, `amfi_code`, `amc`, `category`.
- `NavPoint`: `date`, `nav`.
- `FolioBalance`: `number`, `broker`, `folio_type`, `units`, `value_inr`.
- `Transaction`: `id`, `investor_id`, `security_id`, `folio_id`, `date`, `transaction_type`, `units`, `nav_or_price`, `amount`, `fees`, `stamp_duty`, `brokerage`, `currency`, `source`, `narration`, `cost_basis_complete`.
- `SchemeDetail`: `security`, `as_of`, `units`, `value_inr`, `invested_inr`, `return_pct`, `xirr`, `xirr_status`, `day_change_inr`, `day_change_pct`, `latest_nav`, `latest_nav_date`, `folios`, `nav_history`, `transactions`.
- `AssetMixRow`: `security_type`, `value_inr`.
- `AllocationBucket`: `label`, `value_inr`.
- `PeriodReturn`: `period`, `annualized`, `absolute`, `days`.
- `PortfolioSummary`: `investor_id`, `as_of`, `total_inr`, `is_provisional`, `navs_as_of`, `holdings_count`, `xirr`, `period_returns`, `asset_mix`, `amc_mix`, `category_mix`, `holdings`.
- `ValueSeriesPoint`: `date`, `value_inr`, `invested_inr`, `stale`.
- `ValueSeries`: `investor_id`, `family_id`, `start`, `end`, `granularity`, `points`.
- `ValuationStatus`: `investor_id`, `status`, `computed_through`, `recompute_from`, `is_provisional`.
- `CapitalGainRow`: `security_id`, `name`, `isin`, `units`, `sale_value`, `cost`, `gain`, `term`, `acquired_on`, `sold_on`.
- `CapitalGainsReport`: `fy`, `stcg_total`, `ltcg_total`, `rows`, `disclaimer`.
- `CapitalGainsFyPoint`: `fy`, `stcg`, `ltcg`.

---

### Folioman Exceptions

- `FoliomanError`: Base exception for all client errors.
- `FoliomanAuthError`: Authentication or token refresh failure.
- `FoliomanNotFoundError`: Resource not found (HTTP 404).
- `FoliomanAPIError`: HTTP 4xx/5xx API error. Contains `status_code` and `response_data`.

---

## 3. TickerTape Client (`tickertape`)

### `TickerTapeClient`

Primary async client for TickerTape web scraping, sitemaps, and mutual fund data.

#### Constructor

```python
TickerTapeClient(
    base_url: str = "https://www.tickertape.in",
    timeout: float = 30.0,
    cache_dir: Path | str = ".cache/tickertape",
    http_client: httpx.AsyncClient | None = None,
    headers: dict[str, str] | None = None,
    sitemap_urls: dict[str, str] | None = None,
)
```

#### Core Methods

- `async request(method: str, url_or_path: str, *, params=None, headers=None, **kwargs) -> str`: Executes HTTP request and returns HTML text response.
- `async close() -> None`: Closes the HTTP client transport.

#### Resource Attributes

- `sitemap: SitemapResource`
- `mf: MutualFundsResource`
- `cache_manager: SitemapCacheManager`

---

### Resource Classes

#### `SitemapResource`

- `async get(category: str = "mf", *, force_refresh: bool = False) -> list[SitemapURL]`
- `async refresh(category: str = "mf") -> list[SitemapURL]`
- `is_cached(category: str = "mf") -> bool`
- `clear_cache(category: str | None = None) -> None`

#### `MutualFundsResource`

- `async get(slug_or_mfid: str) -> MutualFundDetail`
- `async get_by_isin(isin: str, hint_name: str | None = None) -> MutualFundDetail | None`
- `async get_isin(slug_or_mfid: str) -> str | None`
- `async get_raw(slug_or_mfid: str) -> dict[str, Any]`
- `get_peers(isin: str, match_plan: bool = True, match_option: bool = True, limit: int = 20) -> list[ISINMapping]`
- `find_funds(*, sector=None, subsector=None, fund_type=None, plan=None, option=None, risk_level=None, benchmark=None, amc=None, limit=100) -> list[ISINMapping]`
- `async build_isin_index(*, force_refresh: bool = False, concurrency: int = 5, delay: float = 0.5, limit: int | None = None, progress_callback=None) -> int`
- Attributes: `lookup: ISINLookupTable`

---

### Lookup & Storage Classes

#### `ISINLookupTable`

SQLite-backed persistent lookup table for mutual funds (`isin_lookup.db`).

- `get(isin: str) -> ISINMapping | None`
- `get_batch(isins: list[str]) -> dict[str, ISINMapping]`
- `get_by_record_id(record_id: str) -> ISINMapping | None`
- `find_funds(...) -> list[ISINMapping]`
- `get_peers(isin: str, match_plan=True, match_option=True, limit=20) -> list[ISINMapping]`
- `get_all_record_ids() -> set[str]`
- `get_all_isins() -> set[str]`
- `upsert(mapping: ISINMapping) -> None`
- `upsert_batch(mappings: list[ISINMapping]) -> None`
- `count() -> int`
- `all() -> list[ISINMapping]`
- `clear() -> None`
- `export_json(filepath: Path | str) -> Path`
- `export_csv(filepath: Path | str) -> Path`

#### `ISINResolver`

- `async resolve(isin: str, hint_name: str | None = None, max_candidates: int = 3) -> ISINMapping | None`

#### `ISINIndexer`

- `async build_index(*, force_refresh=False, concurrency=5, delay=0.5, limit=None, progress_callback=None) -> int`

---

### TickerTape Data Models

- `SitemapURL`: `record_id`, `url`, `last_modified`, `change_frequency`, `priority`.
- `MFScorecardItem`: `name`, `tag`, `colour`, `description`.
- `MFSecurityInfo`: `mf_id`, `name`, `type`, `slug`, `amc`, `amc_code`, `nav_close`, `nav_ch_1d`, `option`, `sector`, `subsector`.
- `MFMeta`: `name`, `isin`, `amc`, `plan`, `option`, `type`, `sector`, `subsector`, `benchmark_index`, `fund_type`, `full_name`, `risk_classification`, `cams_code`, `rta_scheme_code`, `expense_ratio`, `aum`.
- `MutualFundDetail`: `mf_id`, `name`, `isin`, `slug`, `nav`, `security_info`, `meta`, `scorecard`, `raw_props`.
- `ISINMapping`: `isin`, `record_id`, `slug`, `name`, `amc`, `amc_code`, `sector`, `subsector`, `fund_type`, `fund_class`, `plan`, `option`, `risk_level`, `benchmark`, `url`, `nav`, `updated_at`.

---

### TickerTape Exceptions

- `TickerTapeError`: Base exception for all TickerTape client errors.
- `TickerTapeHTTPError`: HTTP request error. Contains `status_code` and `response_data`.
- `TickerTapeNotFoundError`: Resource not found (HTTP 404).
- `TickerTapeParseError`: Error extracting or decoding Next.js hydration data or XML.

---

## 4. Repositories (`folioman_intelligence.repository`)

### `MutualFundRepository`

- `async get_fund_data(identifier: str, hint_name: str | None = None) -> dict[str, Any]`
- `standardize_mutual_fund_payload(raw_props: dict[str, Any]) -> dict[str, Any]`

### `PortfolioRepository`

- `async get_portfolio(investor_id: int) -> PortfolioSummary`
- `async get_holding(investor_id: int, security_id: int) -> SchemeDetail`

---

## 5. Analytics Functions (`folioman_intelligence.analytics`)

### Fund Analytics (`analytics.fund`)

- `async get_fund_overview(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_trailing_returns(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_cagr_history(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_risk_and_volatility(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_portfolio_valuation(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_top_holdings(identifier: str, top_n: int = 10, fund_data=None) -> dict[str, Any]`
- `async get_portfolio_activity(identifier: str, fund_data=None) -> dict[str, Any]`
- `async search_stock_in_fund(identifier: str, query: str, fund_data=None) -> dict[str, Any]`
- `async get_asset_allocation(identifier: str, fund_data=None) -> dict[str, Any]`
- `async check_mandate_compliance(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_sector_allocation(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_sector_rotation_trends(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_peer_comparison(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_fund_managers_analysis(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_cost_and_tax_profile(identifier: str, fund_data=None) -> dict[str, Any]`
- `async get_fund_health_audit(identifier: str, fund_data=None) -> dict[str, Any]`
- `async analyze_fund_comprehensive(identifier: str, fund_data=None) -> dict[str, Any]`

### Portfolio Analytics (`analytics.portfolio`)

- `async analyze_portfolio(investor_id: int) -> dict[str, Any]`
- `async holding_details(investor_id: int, security_id: int) -> dict[str, Any]`
- `async portfolio_risk_analyse(investor_id: int) -> dict[str, Any]`

---

## 6. LangChain Tools (`folioman_intelligence.tools`)

### Fund Tools (`tools.fund`)

Exported list: `fund_tools` (17 tools)

- `analyze_fund_tool`
- `get_fund_overview_tool`
- `get_fund_trailing_returns_tool`
- `get_fund_cagr_history_tool`
- `get_fund_risk_metrics_tool`
- `get_fund_valuation_tool`
- `get_fund_top_holdings_tool`
- `get_fund_portfolio_activity_tool`
- `search_stock_in_fund_tool`
- `get_fund_asset_allocation_tool`
- `check_fund_mandate_compliance_tool`
- `get_fund_sector_allocation_tool`
- `get_sector_rotation_trends_tool`
- `get_fund_peer_comparison_tool`
- `get_fund_managers_info_tool`
- `get_fund_cost_and_tax_tool`
- `get_fund_health_audit_tool`

### Portfolio Tools (`tools.portfolio`)

Exported list: `portfolio_tools` (3 tools)

- `get_portfolio_analysis`
- `get_holding_details`
- `get_portfolio_risk_analyse`

---

## 7. Autonomous AI Agents (`folioman_intelligence.agents`)

### Funds Analyst Agent (`agents.fund`)

- `async ask_fund_agent(question: str) -> FundAgentResponse`
- Class `FundAgentResponse`:
    - Property `.content`: Final synthesized answer string.
    - Property `.tool_calls`: List of recorded tool call dictionaries (`name`, `input`, `output`).

### Portfolio Advisor Agent (`agents.portfolio`)

- `async ask_portfolio_agent(question: str) -> PortfolioAgentResponse`
- Class `PortfolioAgentResponse`:
    - Property `.content`: Final synthesized advice string.
    - Property `.tool_calls`: List of recorded tool call dictionaries (`name`, `input`, `output`).
