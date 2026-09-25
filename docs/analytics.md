# Financial Analytics Engine

The analytics engine defines domain-specific analytical functions for mutual funds and investor portfolios. All computations are strictly deterministic and reproducible.

---

## Architectural Philosophy

- **Pure Computation**: The analytics functions do not perform network requests if `fund_data` is supplied. When an identifier is provided without pre-fetched data, they resolve it via `MutualFundRepository`.
- **Standardized Serialization**: Analytics functions return clean Python primitive types (`float`, `int`, `str`, `dict`, `list`), ensuring direct JSON serializability.
- **Metric Definitions**: Implements industry-standard Modern Portfolio Theory (MPT) formulas and SEBI regulatory guidelines.

---

## Mutual Fund Analytics (`analytics.fund`)

### 1. Scheme Overview & Profile

#### `get_fund_overview(identifier, fund_data=None)`

Computes baseline scheme profile, current NAV, 1-day percentage change, vintage (fund age in years), AUM, and investment limits.

```python
async def get_fund_overview(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `mf_id: str`: TickerTape fund identifier.
- `name: str`, `full_name: str`, `isin: str`, `slug: str`: Scheme identity.
- `amc: str`: Asset Management Company.
- `plan: str`: Direct or Regular.
- `option: str`: Growth or IDCW.
- `category: str`, `subsector: str`, `benchmark: str`: Category classification and benchmark index.
- `risk_classification: str`: Riskometer level (e.g. `"Very High"`).
- `nav: float`, `nav_1d_change: float`, `nav_1d_change_pct: float`: Current price and 1-day daily fluctuation.
- `fund_age_years: float`: Years since inception (calculated from Unix timestamp).
- `aum_in_cr: float`: Assets Under Management in Crores.
- `min_sip_amount: float`, `min_lumpsum_amount: float`: Investment thresholds.
- `sip_allowed: bool`, `lumpsum_allowed: bool`: Transaction eligibility.
- `objective: str`, `exit_load_remarks: str`: Fund mandate and exit load rules.

---

### 2. Returns & Rolling CAGR Trajectory

#### `get_trailing_returns(identifier, fund_data=None)`

Extracts trailing point-to-point and annualized CAGR returns across standard investment horizons.

```python
async def get_trailing_returns(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `return_1y: float`: 1-Year absolute return percentage.
- `return_3y_cagr: float`: 3-Year annualized CAGR return.
- `return_5y_cagr: float`: 5-Year annualized CAGR return.
- `life_cagr: float`: Since-inception annualized return.
- `all_trailing_returns: list[dict]`: Complete list of durations (1M, 3M, 6M, 1Y, 3Y, 5Y).

#### `get_cagr_history(identifier, fund_data=None)`

Analyzes the historical rolling CAGR series to evaluate long-term compounding consistency and return dispersion across market cycles.

```python
async def get_cagr_history(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `latest_observation_cagr: float`: Most recent multi-year CAGR observation.
- `min_cagr: float`, `max_cagr: float`: Historical range bounds.
- `median_cagr: float`: Median rolling CAGR across all recorded intervals.
- `cagr_spread: float`: Difference between max and min CAGR (`max_cagr - min_cagr`), indicating return volatility.
- `observations: list[dict]`: Recent rolling interval data points.

---

### 3. Risk, Volatility & MPT Ratios

#### `get_risk_and_volatility(identifier, fund_data=None)`

Computes Modern Portfolio Theory (MPT) risk-adjusted metrics.

```python
async def get_risk_and_volatility(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Formulas & Metrics**:

- **Alpha ($\alpha$)**: Excess return generated relative to the benchmark index.
- **Standard Deviation ($\sigma$)**: Annualized volatility of scheme NAV returns.
- **Sharpe Ratio**:
  $$\text{Sharpe} = \frac{R_p - R_f}{\sigma_p}$$
  Measures risk-adjusted excess return per unit of total risk.
- **Sortino Ratio**:
  $$\text{Sortino} = \frac{R_p - R_f}{\sigma_d}$$
  Measures return per unit of downside risk ($\sigma_d$).
- **`category_sharpe_ratio: float`**: Average Sharpe ratio of category peers.
- **`sharpe_outperformance_vs_category: float`**: `sharpe_ratio - category_sharpe_ratio`.
- **`risk_profile: str`**: Qualitative rating based on Sharpe ratio threshold.

#### `get_portfolio_valuation(identifier, fund_data=None)`

Evaluates the underlying weighted Price-to-Earnings (P/E) ratio against the category benchmark.

```python
async def get_portfolio_valuation(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `portfolio_pe: float`: Weighted P/E ratio of the underlying stock holdings.
- `category_pe: float`: Average P/E ratio of the fund category.
- `valuation_premium_pct: float`:
  $$\text{Premium \%} = \frac{\text{Portfolio P/E} - \text{Category P/E}}{\text{Category P/E}} \times 100$$
- `valuation_status: str`: Classification describing whether the fund trades at a premium or discount to its category.

---

### 4. Portfolio Holdings & Activity

#### `get_top_holdings(identifier, top_n=10, fund_data=None)`

Computes portfolio concentration and high-conviction positions.

```python
async def get_top_holdings(
    identifier: str,
    top_n: int = 10,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `total_holdings_count: int`: Total number of individual stocks held.
- `top_5_concentration_pct: float`: Cumulative weight of the top 5 positions.
- `top_10_concentration_pct: float`: Cumulative weight of the top 10 positions.
- `high_conviction_bets_count: int`: Count of stocks with weight $\ge 5.0\%$.
- `high_conviction_bets: list[dict]`: Details of positions with weight $\ge 5.0\%$.
- `top_holdings: list[dict]`: Sorted top holdings with rank, ticker, company name, weight, 3-month change, and analyst rating.

#### `get_portfolio_activity(identifier, fund_data=None)`

Identifies recent portfolio changes made by the fund manager over the trailing 3-month window.

```python
async def get_portfolio_activity(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `accumulated_stocks_count: int`, `trimmed_stocks_count: int`
- `top_accumulated: list[dict]`: Positions with the highest positive weight increase over 3 months (`change_3m_pct > 0`).
- `top_trimmed: list[dict]`: Positions with the largest weight reduction or exit over 3 months (`change_3m_pct < 0`).

#### `search_stock_in_fund(identifier, query, fund_data=None)`

Determines whether a specific stock is held in the fund's portfolio by matching company title, ticker, or symbol ID.

```python
async def search_stock_in_fund(
    identifier: str,
    query: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `query: str`: Search query string.
- `is_held: bool`: True if at least one matching holding exists.
- `matches: list[dict]`: List of matched stocks with title, ticker, portfolio weight %, and 3-month weight change.

---

### 5. Asset Allocation & Mandate Compliance

#### `get_asset_allocation(identifier, fund_data=None)`

Extracts current and historical allocation across asset classes.

```python
async def get_asset_allocation(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `equity_pct: float`: Pure equity exposure percentage.
- `derivatives_fo_pct: float`: Futures & Options derivative exposure (hedging or cash-futures arbitrage).
- `debt_tbills_pct: float`: Treasury bills and fixed income exposure.
- `cash_equivalents_pct: float`: Cash and liquid instruments.
- `reits_invits_pct: float`: Real estate & infrastructure trust holdings.
- `has_active_derivatives: bool`: True if derivative exposure exceeds $1.0\%$.

#### `check_mandate_compliance(identifier, fund_data=None)`

Verifies whether current asset allocation adheres to SEBI / Scheme statutory boundaries (`min` and `max` targets).

```python
async def check_mandate_compliance(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `overall_compliant: bool`: True if all asset classes remain within their statutory min/max limits.
- `breaches_count: int`: Number of asset classes outside allowed thresholds.
- `breaches: list[dict]`: Detailed report of breached limits with min allowed, max allowed, and actual weight.
- `target_limits: list[dict]`: Complete compliance table across all asset classes.

---

### 6. Sector Allocation & Macro Rotation

#### `get_sector_allocation(identifier, fund_data=None)`

Computes sector breakdown and sector concentration.

```python
async def get_sector_allocation(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `sectors_count: int`: Number of distinct sectors invested in.
- `top_3_sectors_concentration_pct: float`: Weight of top 3 sectors.
- `top_5_sectors_concentration_pct: float`: Weight of top 5 sectors.
- `top_sectors: list[dict]`: Sorted list of sectors with weights.

#### `get_sector_rotation_trends(identifier, fund_data=None)`

Analyzes multi-period historical sector weight changes to identify macro allocation shifts.

```python
async def get_sector_rotation_trends(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `expanding_sectors: list[dict]`: Sectors where allocation has systematically increased (`change_pct > 0`).
- `contracting_sectors: list[dict]`: Sectors where allocation has decreased (`change_pct < 0`).

---

### 7. Peer Comparison & Category Ranking

#### `get_peer_comparison(identifier, fund_data=None)`

Builds a comparative peer matrix and calculates the target fund's rank within its category for 1-year returns and 3-year CAGR.

```python
async def get_peer_comparison(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `peer_group_size: int`: Total number of comparable funds.
- `rank_1y_return: str`: Target fund rank for 1-year return (e.g. `"1 of 6"`).
- `rank_3y_cagr: str`: Target fund rank for 3-year CAGR (e.g. `"2 of 6"`).
- `comparison_table: list[dict]`: Matrix containing peer names, 1Y return, 3Y CAGR, Life CAGR, and expense ratios.

---

### 8. Fund Managers & Workload

#### `get_fund_managers_analysis(identifier, fund_data=None)`

Audits fund manager credentials, years of experience, total AUM overseen, and count of other schemes managed.

```python
async def get_fund_managers_analysis(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `fund_managers_count: int`: Number of co-managers.
- `manager_profiles: list[dict]`: For each manager:
    - `name: str`, `qualification: str`, `experience_years: float`, `aum_in_cr: float`
    - `other_funds_managed_count: int`: Capacity indicator.
    - `sample_managed_funds: list[dict]`: Performance of other funds managed by the same individual.

---

### 9. Fees, Exit Load & Taxation

#### `get_cost_and_tax_profile(identifier, fund_data=None)`

Evaluates expense ratio advantage against the category average, exit load redemption penalties, and capital gains tax rules.

```python
async def get_cost_and_tax_profile(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `expense_ratio_pct: float`: Current fund expense ratio.
- `category_expense_ratio_pct: float`: Category average expense ratio.
- `cost_advantage_basis_points: float`:
  $$\text{Advantage (bps)} = (\text{Category Expense Ratio} - \text{Fund Expense Ratio}) \times 100$$
  Positive value indicates a cheaper fund than the category average.
- `exit_load_remarks: str`: Penalty schedule for early redemptions.
- `taxation_rules: list[dict]`: Applicable STCG and LTCG holding periods and tax rates.

---

### 10. Scorecard & Red Flags Health Check

#### `get_fund_health_audit(identifier, fund_data=None)`

Audits the fund across 5 qualitative scorecard pillars and quantifies portfolio red flags.

```python
async def get_fund_health_audit(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:

- `scorecard_pillars: list[dict]`: Tags and evaluations for Performance, Risk, Cost, Composition, and Red flags.
- `total_red_flags: dict`: Breakdown of red flag companies held in the fund.
- `has_red_flags: bool`: True if any underlying holding has governance or accounting red flags.

---

### 11. Master 360° Due Diligence Report

#### `analyze_fund_comprehensive(identifier, fund_data=None)`

Combines all core analytical domains into a single consolidated report.

```python
async def analyze_fund_comprehensive(
    identifier: str,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Aggregated Sections**:

- `overview`: Output from `get_fund_overview`
- `performance`: Output from `get_trailing_returns`
- `risk_and_volatility`: Output from `get_risk_and_volatility`
- `top_holdings_concentration`: Top 5 concentration % and top holdings from `get_top_holdings`
- `top_sectors`: Top 3 sectors from `get_sector_allocation`
- `costs_and_taxes`: Expense ratio, category expense ratio, cost advantage, exit load from `get_cost_and_tax_profile`
- `health_and_red_flags`: Output from `get_fund_health_audit`

---

## Portfolio Analytics (`analytics.portfolio`)

Provides portfolio-level and holding-level calculations for investor accounts.

### 1. Portfolio Analysis

#### `analyze_portfolio(investor_id)`

```python
async def analyze_portfolio(investor_id: int) -> dict[str, Any]
```

Aggregates holdings under an investor to compute:

- `currency: str`: Currency code (`"INR"`).
- `total_value: float`: Total current portfolio market value.
- `total_invested: float`: Total acquisition cost / invested capital across all holdings.
- `absolute_returns: float`: Total unrealized gain (`total_value - total_invested`).
- `navs_as_of: date`: Point-in-time valuation date.
- `xirr: float | None`: Extended Internal Rate of Return (money-weighted return).
- `category_mix: list[dict]`: Allocation breakdown across mutual fund categories (Large Cap, Mid Cap, Hybrid, etc.).
- `period_returns: list[dict]`: Trailing portfolio returns across multi-period windows.
- `holdings: list[dict]`: Detailed holding records including units, market value, invested value, return %, XIRR, and contribution to total portfolio invested capital (`(invested_inr / total_invested) * 100`).
- `top_3_by_invested: dict[int, str]`: Top 3 schemes ranked by capital invested.
- `top_3_by_current_value: dict[int, str]`: Top 3 schemes ranked by current valuation.

### 2. Holding Details Analysis

#### `holding_details(investor_id, security_id)`

```python
async def holding_details(investor_id: int, security_id: int) -> dict[str, Any]
```

Analyzes the ledger transactions of a specific holding:

- `name: str`, `isin: str`, `security_type: str`: Scheme identity.
- `invested: float`, `current_value: float`: Capital deployed and current market value.
- `returns%: float`: Unrealized return percentage (`return_pct * 100`).
- `current_units: float`: Units held.
- `avg_buy_transaction: float`: Average buy transaction amount across buy transactions.
- `count_buy_transaction: int`: Total number of buy transactions recorded.

---

## Historical Portfolio Analytics (`analytics.historical`)

Provides multi-horizon historical performance trajectory, capital preservation analysis, Modern Portfolio Theory (MPT) risk-adjusted metrics, cash flow discipline, and financial year capital gains auditing using `folioman-client`.

### 1. Valuation Trajectory & Wealth Creation

#### `get_historical_valuation_trajectory(investor_id, from_date=None, to_date=None, granularity="monthly", value_series=None)`

Reconstructs the point-by-point growth of portfolio net worth against cumulative capital invested over time.

```python
async def get_historical_valuation_trajectory(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    value_series: ValueSeries | dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:
- `initial_value_inr: float`, `latest_value_inr: float`: Beginning and ending portfolio valuation.
- `initial_invested_inr: float`, `latest_invested_inr: float`: Beginning and ending cost basis.
- `net_invested_change_inr: float`: Total fresh capital deployed ($I_{\text{end}} - I_{\text{start}}$).
- `net_wealth_generated_inr: float`: Total net unrealized wealth created ($V_{\text{end}} - I_{\text{end}}$).
- `absolute_growth_pct: float`: Portfolio value expansion percentage ($((V_{\text{end}} - V_{\text{start}}) / V_{\text{start}}) \times 100$).
- `peak_valuation_inr: float`, `peak_valuation_date: str`: All-time high valuation milestone and date.
- `trough_valuation_inr: float`, `trough_valuation_date: str`: Lowest recorded valuation point and date.
- `trajectory: list[dict]`: Date-by-date series containing `value_inr`, `invested_inr`, `unrealized_gain_inr`, `unrealized_gain_pct`, `period_change_inr`, `period_return_pct`, and `net_inflow_inr`.

---

### 2. Drawdown & Capital Preservation

#### `get_historical_drawdown_analysis(investor_id, from_date=None, to_date=None, granularity="monthly", value_series=None)`

Measures capital preservation, maximum peak-to-trough decline (MDD), recovery duration, and historical drawdown episodes.

```python
async def get_historical_drawdown_analysis(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    value_series: ValueSeries | dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:
- `max_drawdown_pct: float`: Deepest percentage loss from prior peak (e.g. `-13.64%`).
- `max_drawdown_inr: float`: Peak-to-trough monetary decline in INR.
- `peak_date: str`, `peak_value_inr: float`: High watermark establishing the MDD.
- `trough_date: str`, `trough_value_inr: float`: Bottom of the drawdown cycle.
- `recovery_date: str | None`: Date on which portfolio returned to or exceeded previous peak (or `None` if unrecovered).
- `is_recovered: bool`: True if the portfolio has completely recovered from the maximum drawdown.
- `recovery_duration_days: int | None`: Calendar days taken to recover from trough to peak.
- `current_drawdown_pct: float`: Current drawdown percentage relative to all-time peak.
- `is_at_all_time_high: bool`: True if current portfolio valuation represents an all-time high.
- `average_drawdown_pct: float`: Average depth across all negative drawdown periods.
- `drawdown_episodes: list[dict]`: Top drawdown periods with peak, trough, recovery, and percentage depth.
- `drawdown_series: list[dict]`: Date-by-date series with running peak and instantaneous drawdown.

---

### 3. Risk-Adjusted Returns & Volatility

#### `get_historical_risk_and_returns(investor_id, from_date=None, to_date=None, granularity="monthly", risk_free_rate=0.065, value_series=None)`

Computes cashflow-adjusted periodic return series, annualized volatility ($\sigma$), downside deviation, CAGR, Sharpe ratio, Sortino ratio, and Calmar ratio.

```python
async def get_historical_risk_and_returns(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    risk_free_rate: float = 0.065,
    value_series: ValueSeries | dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Formulas & Metrics**:
- **Periodic Return ($R_t$)**:
  $$R_t = \frac{V_t - V_{t-1} - \Delta I_t}{V_{t-1}}$$
- **Annualized Volatility ($\sigma_{\text{ann}}$)**:
  $$\sigma_{\text{ann}} = \text{std}(R) \times \sqrt{N} \times 100 \quad (N = 12 \text{ for monthly, } 252 \text{ for daily})$$
- **Downside Deviation ($\sigma_d$)**:
  $$\sigma_{d} = \sqrt{\frac{1}{M}\sum_{R_t < R_f/N} (R_t - R_f/N)^2} \times \sqrt{N} \times 100$$
- **Sharpe Ratio**:
  $$\text{Sharpe} = \frac{\text{CAGR} - R_f}{\sigma_{\text{ann}} / 100}$$
- **Sortino Ratio**:
  $$\text{Sortino} = \frac{\text{CAGR} - R_f}{\sigma_d / 100}$$
- **Calmar Ratio**:
  $$\text{Calmar} = \frac{\text{CAGR}}{|\text{Max Drawdown}| / 100}$$
- `best_period: dict`, `worst_period: dict`: Date and return percentage for highest and lowest periods.
- `win_rate_pct: float`: Percentage of periods generating positive net returns.

---

### 4. Cash Flow Dynamics & SIP Discipline

#### `get_historical_cashflows(investor_id, transactions=None)`

Audits the investor's transaction ledger history, gross capital inflows vs outflows, SIP investment consistency, and vintage.

```python
async def get_historical_cashflows(
    investor_id: int,
    transactions: list[Transaction] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]
```

**Output Fields**:
- `total_transactions_count: int`: Lifetime transaction count.
- `first_transaction_date: str`, `latest_transaction_date: str`: Timeline boundaries.
- `portfolio_vintage_years: float`: Years elapsed between the first investment and latest transaction.
- `total_gross_inflows_inr: float`: Total gross capital deployed (buys, SIPs, switch-ins).
- `total_gross_outflows_inr: float`: Total redemptions and withdrawals.
- `net_cash_invested_inr: float`: Inflows minus outflows.
- `sip_metrics: dict`:
  - `total_sip_amount_inr: float`, `total_sip_count: int`
  - `average_sip_amount_inr: float`
  - `sip_share_of_inflows_pct: float`: Percentage of total inflows deployed via systematic plans.
  - `lumpsum_amount_inr: float`, `lumpsum_count: int`
- `yearly_summary: list[dict]`: Calendar-year breakdown of inflows, outflows, net inflows, and SIP volumes.
- `breakdown_by_type: dict`: Volume and count partitioned by transaction category.

---

### 5. Realized Capital Gains & Tax Efficiency

#### `get_historical_capital_gains(investor_id, fy_points=None, include_unreconciled=False)`

Aggregates realized capital gains (STCG vs LTCG) across all financial years with disposals.

```python
async def get_historical_capital_gains(
    investor_id: int,
    fy_points: list[CapitalGainsFyPoint] | list[dict[str, Any]] | None = None,
    include_unreconciled: bool = False,
) -> dict[str, Any]
```

**Output Fields**:
- `financial_years_count: int`: Number of financial years recorded with disposals.
- `cumulative_stcg_inr: float`: Total realized Short-Term Capital Gains.
- `cumulative_ltcg_inr: float`: Total realized Long-Term Capital Gains.
- `cumulative_realized_gain_inr: float`: Cumulative taxable gain across all financial years.
- `profitable_financial_years: int`, `loss_making_financial_years: int`
- `fy_breakdown: list[dict]`: Detailed year-by-year summary of STCG, LTCG, total gain, and Gain/Loss status.

---

### 6. Scheme Historical Tenure & Holding Analysis

#### `get_historical_scheme_tenure(investor_id, security_id, scheme_detail=None)`

Evaluates scheme holding vintage, transactions count, average purchase price, current NAV, and NAV multiple.

```python
async def get_historical_scheme_tenure(
    investor_id: int,
    security_id: int,
    scheme_detail: SchemeDetail | dict[str, Any] | None = None,
) -> dict[str, Any]
```

**Output Fields**:
- `security_id: int`, `name: str`, `isin: str`, `category: str`
- `first_transaction_date: str`, `latest_transaction_date: str`
- `tenure_days: int`, `tenure_years: float`: Exact holding period duration.
- `total_units: float`, `current_value_inr: float`, `invested_inr: float`
- `buy_transactions_count: int`, `avg_buy_nav: float`: Weighted average acquisition price.
- `latest_nav: float`, `nav_multiple: float`: Valuation multiple ($\text{latest\_nav} / \text{avg\_buy\_nav}$).
- `return_pct: float`, `xirr: float`: Scheme return and money-weighted IRR.
- `nav_history_points_count: int`: Number of NAV curve points available.

---

### 7. Master 360° Historical Portfolio Report

#### `analyze_portfolio_historical(investor_id, from_date=None, to_date=None, granularity="monthly", risk_free_rate=0.065)`

Consolidates all historical performance layers into a unified intelligence report:

```python
async def analyze_portfolio_historical(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    risk_free_rate: float = 0.065,
) -> dict[str, Any]
```

**Aggregated Sections**:
- `valuation_status`: Calculation readiness, provisional status, and finalization date.
- `trajectory_summary`: Initial vs latest net worth, capital deployed, wealth created, and peak valuation.
- `drawdown_summary`: Maximum drawdown percentage, peak date, trough date, recovery date, and current drawdown.
- `risk_adjusted_performance`: Annualized CAGR, annualized volatility, Sharpe, Sortino, and Calmar ratios.
- `cashflow_discipline`: Cumulative gross inflows, net capital deployed, SIP percentage, and vintage.
- `realized_tax_summary`: Cumulative STCG, LTCG, and realized capital gain totals across FYs.
- `key_insights`: Synthesized list of concise, deterministic factual observations grounded strictly in the data.

