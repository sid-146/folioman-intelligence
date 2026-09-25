import asyncio
import heapq
import logging

from copy import deepcopy
from typing import List, Dict, Any
from datetime import datetime, timedelta

from folioman_intelligence.repository.portfolio import PortfolioRepository
from tickertape import TickerTapeClient
from folioman_client import FoliomanClient, FoliomanNotFoundError

# TODO: Need optimization (too many db calls)
# TODO: Add diversification


logger = logging.getLogger(__name__)


# TODO: Write test for this
async def get_isin(investor_id: int, security_id: int):
    repo = PortfolioRepository()
    scheme = await repo.get_holding(investor_id, security_id)
    if not scheme:
        raise FoliomanNotFoundError("Scheme not found.")
    return scheme.security.isin


# TODO: Write test for this
async def get_top_holdings_by_invested(investor_id: int, k: int = 3):
    repo = PortfolioRepository()
    portfolio = await repo.get_portfolio(investor_id)
    holdings = [h for h in portfolio.holdings if h.invested_inr is not None]
    holdings = sorted(holdings, key=lambda h: (h.invested_inr or 0), reverse=True)[:k]
    selected: List[Dict[str, Any]] = []
    for i in holdings:
        isin = await get_isin(investor_id, i.security_id)
        selected.append(
            {
                "name": i.name,
                "isin": isin,
                "security_id": i.security_id,
                "xirr": i.xirr,
                "invested_amount": i.invested_inr,
                "return_percent": (i.return_pct if i.return_pct else 0) * 100,
            }
        )
    return selected


# TODO: Write test for this
async def get_top_holdings_by_returns(investor_id: int, k: int = 3):
    repo = PortfolioRepository()
    portfolio = await repo.get_portfolio(investor_id)
    holdings = [h for h in portfolio.holdings if h.value_inr is not None]
    top_holdings = sorted(holdings, key=lambda h: (h.value_inr or 0), reverse=True)[:k]

    selected = []
    for h in top_holdings:
        isin = await get_isin(investor_id, h.security_id)
        selected.append(
            {
                "name": h.name,
                "isin": isin,
                "security_id": h.security_id,
                "xirr": h.xirr,
                "current_value": h.value_inr,
                "return_percent": (h.return_pct or 0) * 100,
            }
        )

    return selected


# TODO: Write test for this
async def get_asset_allocation(investor_id: int):
    repo = PortfolioRepository()
    ticker = TickerTapeClient()
    portfolio = await repo.get_portfolio(investor_id)
    holdings = portfolio.holdings
    tasks = [get_isin(investor_id, h.security_id) for h in holdings]
    isins = await asyncio.gather(*tasks)
    mappings = await ticker.mf.get_cached_by_isin_batch(isins)

    asset_categories = {}
    for _, cache in mappings.items():
        if cache.fund_type:
            current = asset_categories.get(cache.fund_type, 0)
            asset_categories[cache.fund_type] = current + 1

    total = sum(list(asset_categories.values()))
    for cat, cat_total in asset_categories.items():
        asset_categories[cat] = (cat_total / total) * 100
    return asset_categories


# TODO: Write test for this
async def get_sector_exposure(investor_id: int):
    repo = PortfolioRepository()
    ticker = TickerTapeClient()
    portfolio = await repo.get_portfolio(investor_id)
    holdings = portfolio.holdings
    tasks = [get_isin(investor_id, h.security_id) for h in holdings]
    isins = await asyncio.gather(*tasks)
    mappings = await ticker.mf.get_cached_by_isin_batch(isins)

    exposure_cats = {}
    for _, cache in mappings.items():
        if cache.sector:
            current = exposure_cats.get(cache.sector, 0)
            exposure_cats[cache.sector] = current + 1

    total = sum(list(exposure_cats.values()))
    for cat, cat_total in exposure_cats.items():
        exposure_cats[cat] = (cat_total / total) * 100

    return exposure_cats


# TODO: Write test for this
async def get_portfolio_volatility(investor_id: int, days=90):
    folioman = FoliomanClient()

    to_date = datetime.today().date()
    from_date = to_date - timedelta(days=days)

    print(from_date, to_date)

    monthly_volatility = await folioman.valuations.list(
        investor_id, from_date=from_date, to_date=to_date
    )
    points = [i.model_dump() for i in monthly_volatility.points]
    return points


# TODO: Write test for this
async def analyze_portfolio(investor_id: int):
    repo = PortfolioRepository()
    portfolio = await repo.get_portfolio(investor_id)
    if isinstance(portfolio, dict):
        analysis = deepcopy(portfolio)
        top_3_holding = sorted(
            analysis.get("holdings", []),
            key=lambda x: (
                (x.get("invested_inr") or 0)
                if isinstance(x, dict)
                else (getattr(x, "invested_inr", 0) or 0)
            ),
            reverse=True,
        )[:3]
        analysis["top_3_holdings"] = [
            t["name"] if isinstance(t, dict) else t.name for t in top_3_holding
        ]
        return analysis

    total_invested = sum(
        [holding.invested_inr for holding in portfolio.holdings if holding.invested_inr]
    )
    period_returns = [
        {
            "period": pr.period,
            "absolute_return": pr.absolute,
        }
        for pr in portfolio.period_returns
    ]
    holdings = [
        {
            "security_id": holding.security_id,
            "name": holding.name,
            "category": holding.category,
            "units": holding.units,
            "value_inr": holding.value_inr,
            "invested_inr": holding.invested_inr,
            "return_pct": holding.return_pct * 100 if holding.return_pct else None,
            "contribution_to_portfolio (invested_inr / total_invested)": (
                holding.invested_inr / total_invested
                if holding.invested_inr and total_invested
                else 0
            )
            * 100,
            "xirr": holding.xirr * 100 if holding.xirr else 0,
        }
        for holding in portfolio.holdings
    ]

    top_3_holding = sorted(
        portfolio.holdings, key=lambda x: x.invested_inr or 0, reverse=True
    )[:3]
    top_3_by_current = sorted(
        portfolio.holdings, key=lambda x: x.value_inr or 0, reverse=True
    )[:3]
    allocation = await get_asset_allocation(investor_id)
    analysis = {
        "currency": "INR",
        "total_value": portfolio.total_inr,
        "total_invested": total_invested,
        "absolute_returns": portfolio.total_inr - total_invested,
        "navs_as_of": portfolio.navs_as_of,
        "category_mix": [
            category.model_dump(mode="json") for category in portfolio.category_mix
        ],
        "all_holdings": holdings,
        "xirr": portfolio.xirr,
        "period_returns": period_returns,
        "allocation": allocation,
        "top_3_by_invested": {i: t.name for i, t in enumerate(top_3_holding, start=1)},
        "top_3_by_current_value": {
            i: t.name for i, t in enumerate(top_3_by_current, start=1)
        },
    }

    return analysis


# Todo: Figure out this should be moved inside the analyze_portfolio?
# This should be called before the fund tools call
async def holding_details(investor_id: int, security_id: int):
    repo = PortfolioRepository()
    holding = await repo.get_holding(investor_id, security_id)
    buy_transactions = [
        transaction
        for transaction in holding.transactions
        if transaction.transaction_type == "buy"
    ]
    buy_transaction_amounts = [
        t.amount for t in buy_transactions if t.amount is not None
    ]
    avg_buy_transaction = sum(buy_transaction_amounts) / len(buy_transaction_amounts)

    analytics = {
        "currency": "INR",
        "name": holding.security.name,
        "isin": holding.security.isin,
        "security_type": holding.security.security_type,
        "invested": (
            float(holding.invested_inr)
            if holding.invested_inr is not None
            else "Not Found"
        ),
        "current_value": (
            float(holding.value_inr) if holding.value_inr is not None else "Not Found"
        ),
        "returns%": (
            holding.return_pct * 100
            if holding.return_pct
            else "returns percent not present" ""
        ),
        "current_units": float(holding.units),
        "avg_buy_transaction": float(avg_buy_transaction),
        "count_buy_transaction": len(buy_transactions),
    }
    return analytics


# TODO: Write test for this
async def portfolio_risk_analyse(investor_id: int):
    ticker = TickerTapeClient()

    # Top 3 holdings by invested amount
    top_3_by_invested = await get_top_holdings_by_invested(investor_id, k=3)
    for holding in top_3_by_invested:
        mapping = await ticker.mf.get_cached_by_isin(holding["isin"])
        if mapping:
            holding["sector"] = (
                mapping.sector if mapping.sector is None else "Not Available"
            )
            holding["subsector"] = (
                mapping.subsector if mapping.subsector else "Not Available"
            )
            holding["risk_level"] = mapping.risk_level
            holding["fund_type"] = mapping.fund_type

    # Asset Allocation
    asset_allocation = await get_asset_allocation(investor_id)

    # Sector exposure
    sector_exposure = await get_sector_exposure(investor_id)

    # Portfolio Volatility from 90 days
    monthly_volatility = await get_portfolio_volatility(investor_id, days=90)

    obj = {
        "investor_id": investor_id,
        "top_3_holding_by_invested": top_3_by_invested,
        "asset_allocation": asset_allocation,
        "three_months_volatility": monthly_volatility,
        "sector_exposure": sector_exposure,
    }
    return obj
