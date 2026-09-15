from src.folioman_intelligence.repository.portfolio import PortfolioRepository


async def analyze_portfolio(investor_id: int):
    repo = PortfolioRepository()
    portfolio = await repo.get_portfolio(investor_id)
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
    analysis = {
        "currency": "INR",
        "total_value": portfolio.total_inr,
        "total_invested": total_invested,
        "absolute_returns": portfolio.total_inr - total_invested,
        "navs_as_of": portfolio.navs_as_of,
        "category_mix": [
            category.model_dump(mode="json") for category in portfolio.category_mix
        ],
        "xirr": portfolio.xirr,
        "period_returns": period_returns,
        "holdings": holdings,
        "top_3_by_invested": {i: t.name for i, t in enumerate(top_3_holding, start=1)},
        "top_3_by_current_value": {
            i: t.name for i, t in enumerate(top_3_by_current, start=1)
        },
    }

    return analysis


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
