"""Financial Analytics Package.

Exposes deterministic domain analytics for mutual funds, current portfolios,
and historical portfolio performance trajectories, drawdowns, and cash flows.
"""

from folioman_intelligence.analytics.fund import (
    analyze_fund_comprehensive,
    check_mandate_compliance,
    get_asset_allocation as get_fund_asset_allocation,
    get_cagr_history,
    get_cost_and_tax_profile,
    get_fund_health_audit,
    get_fund_managers_analysis,
    get_fund_overview,
    get_peer_comparison,
    get_portfolio_activity,
    get_portfolio_valuation,
    get_risk_and_volatility,
    get_sector_allocation,
    get_sector_rotation_trends,
    get_top_holdings,
    get_trailing_returns,
    search_stock_in_fund,
)
from folioman_intelligence.analytics.historical import (
    analyze_portfolio_historical,
    get_historical_capital_gains,
    get_historical_cashflows,
    get_historical_drawdown_analysis,
    get_historical_risk_and_returns,
    get_historical_scheme_tenure,
    get_historical_valuation_trajectory,
)
from folioman_intelligence.analytics.portfolio import (
    analyze_portfolio,
    get_asset_allocation,
    get_isin,
    get_portfolio_volatility,
    get_sector_exposure,
    get_top_holdings_by_invested,
    get_top_holdings_by_returns,
    holding_details,
    portfolio_risk_analyse,
)

__all__ = [
    # Fund analytics
    "get_fund_overview",
    "get_trailing_returns",
    "get_cagr_history",
    "get_risk_and_volatility",
    "get_portfolio_valuation",
    "get_top_holdings",
    "get_portfolio_activity",
    "search_stock_in_fund",
    "get_fund_asset_allocation",
    "check_mandate_compliance",
    "get_sector_allocation",
    "get_sector_rotation_trends",
    "get_peer_comparison",
    "get_fund_managers_analysis",
    "get_cost_and_tax_profile",
    "get_fund_health_audit",
    "analyze_fund_comprehensive",
    # Current portfolio analytics
    "analyze_portfolio",
    "holding_details",
    "portfolio_risk_analyse",
    "get_isin",
    "get_top_holdings_by_invested",
    "get_top_holdings_by_returns",
    "get_asset_allocation",
    "get_sector_exposure",
    "get_portfolio_volatility",
    # Historical portfolio analytics
    "get_historical_valuation_trajectory",
    "get_historical_drawdown_analysis",
    "get_historical_risk_and_returns",
    "get_historical_cashflows",
    "get_historical_capital_gains",
    "get_historical_scheme_tenure",
    "analyze_portfolio_historical",
]
