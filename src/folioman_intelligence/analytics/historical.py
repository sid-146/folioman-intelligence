"""Historical Portfolio Analytics Layer.

Defines domain-specific analytical functions for historical portfolio performance,
net worth valuation trajectories, peak-to-trough drawdowns, risk-adjusted returns,
cash flow dynamics, and realized capital gains over time using FoliomanClient.
"""

from __future__ import annotations

from datetime import date, datetime
import math
import statistics
from typing import Any, Literal, Optional

from folioman_client.models import (
    CapitalGainsFyPoint,
    SchemeDetail,
    Transaction,
    ValueSeries,
)
from folioman_intelligence.repository.portfolio import PortfolioRepository


# ===========================================================================
# Helpers & Data Normalization
# ===========================================================================

def _parse_date(d: Any) -> Optional[date]:
    """Parse date or string into datetime.date."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return date.fromisoformat(d.split("T")[0])
        except Exception:
            return None
    return None


def _to_float(val: Any) -> Optional[float]:
    """Safely convert value to float, handling Decimals and None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return None


async def _resolve_value_series(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    value_series: ValueSeries | dict[str, Any] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> list[dict[str, Any]]:
    """Helper to fetch and normalize valuation series points sorted by date."""
    if value_series is None:
        active_repo = repo or PortfolioRepository()
        raw_series = await active_repo.get_value_series(
            investor_id,
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
        )
    else:
        raw_series = value_series

    # Extract points
    if hasattr(raw_series, "points"):
        raw_points = raw_series.points
    elif isinstance(raw_series, dict):
        raw_points = raw_series.get("points", [])
    elif isinstance(raw_series, list):
        raw_points = raw_series
    else:
        raw_points = []

    normalized: list[dict[str, Any]] = []
    for p in raw_points:
        if hasattr(p, "model_dump"):
            dumped = p.model_dump()
            d_obj = _parse_date(dumped.get("date"))
            val = _to_float(dumped.get("value_inr"))
            inv = _to_float(dumped.get("invested_inr"))
            stale = bool(dumped.get("stale", False))
        elif isinstance(p, dict):
            d_obj = _parse_date(p.get("date"))
            val = _to_float(p.get("value_inr"))
            inv = _to_float(p.get("invested_inr"))
            stale = bool(p.get("stale", False))
        else:
            continue

        if d_obj is not None and val is not None:
            normalized.append(
                {
                    "date": d_obj.isoformat(),
                    "_date_obj": d_obj,
                    "value_inr": round(val, 2),
                    "invested_inr": round(inv if inv is not None else 0.0, 2),
                    "stale": stale,
                }
            )

    normalized.sort(key=lambda x: x["_date_obj"])
    return normalized


async def _resolve_transactions(
    investor_id: int,
    transactions: list[Transaction] | list[dict[str, Any]] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> list[dict[str, Any]]:
    """Helper to fetch and normalize transactions sorted by date."""
    if transactions is None:
        active_repo = repo or PortfolioRepository()
        raw_txns = await active_repo.get_transactions(investor_id)
    else:
        raw_txns = transactions

    normalized: list[dict[str, Any]] = []
    for t in raw_txns:
        if hasattr(t, "model_dump"):
            data = t.model_dump()
        elif isinstance(t, dict):
            data = t
        else:
            continue

        d_obj = _parse_date(data.get("date"))
        amount = _to_float(data.get("amount"))
        units = _to_float(data.get("units"))
        nav = _to_float(data.get("nav_or_price"))
        fees = _to_float(data.get("fees")) or 0.0
        stamp = _to_float(data.get("stamp_duty")) or 0.0
        brokerage = _to_float(data.get("brokerage")) or 0.0

        if d_obj is not None:
            normalized.append(
                {
                    "id": data.get("id"),
                    "security_id": data.get("security_id"),
                    "date": d_obj.isoformat(),
                    "_date_obj": d_obj,
                    "transaction_type": str(data.get("transaction_type", "")).upper(),
                    "units": round(units, 4) if units is not None else 0.0,
                    "nav_or_price": round(nav, 4) if nav is not None else 0.0,
                    "amount": round(amount, 2) if amount is not None else 0.0,
                    "fees": round(fees, 2),
                    "stamp_duty": round(stamp, 2),
                    "brokerage": round(brokerage, 2),
                    "source": str(data.get("source", "")),
                    "narration": str(data.get("narration", "")),
                }
            )

    normalized.sort(key=lambda x: x["_date_obj"])
    return normalized


async def _resolve_capital_gains(
    investor_id: int,
    fy_points: list[CapitalGainsFyPoint] | list[dict[str, Any]] | None = None,
    include_unreconciled: bool = False,
    repo: Optional[PortfolioRepository] = None,
) -> list[dict[str, Any]]:
    """Helper to fetch and normalize capital gains summary by financial year."""
    if fy_points is None:
        active_repo = repo or PortfolioRepository()
        raw_gains = await active_repo.get_capital_gains_summary(
            investor_id, include_unreconciled=include_unreconciled
        )
    else:
        raw_gains = fy_points

    normalized: list[dict[str, Any]] = []
    for g in raw_gains:
        if hasattr(g, "model_dump"):
            data = g.model_dump()
        elif isinstance(g, dict):
            data = g
        else:
            continue

        fy = str(data.get("fy", ""))
        stcg = _to_float(data.get("stcg")) or 0.0
        ltcg = _to_float(data.get("ltcg")) or 0.0
        total = round(stcg + ltcg, 2)

        normalized.append(
            {
                "fy": fy,
                "stcg_inr": round(stcg, 2),
                "ltcg_inr": round(ltcg, 2),
                "total_gain_inr": total,
                "status": "Gain" if total > 0 else ("Loss" if total < 0 else "Break-even"),
            }
        )

    return normalized


# ===========================================================================
# 1. Historical Valuation Trajectory
# ===========================================================================

async def get_historical_valuation_trajectory(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    value_series: ValueSeries | dict[str, Any] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Calculate historical net worth growth, capital deployed, and point-by-point trajectory.

    Args:
        investor_id: Unique investor ID.
        from_date: Start date of valuation series.
        to_date: End date of valuation series.
        granularity: 'daily', 'weekly', or 'monthly'.
        value_series: Pre-fetched ValueSeries model or dict.
        repo: Optional PortfolioRepository instance.

    Returns:
        Structured dictionary containing growth metrics and historical trajectory points.
    """
    points = await _resolve_value_series(
        investor_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        value_series=value_series,
        repo=repo,
    )

    if not points:
        return {
            "investor_id": investor_id,
            "granularity": granularity,
            "start_date": None,
            "end_date": None,
            "data_points_count": 0,
            "initial_value_inr": 0.0,
            "latest_value_inr": 0.0,
            "initial_invested_inr": 0.0,
            "latest_invested_inr": 0.0,
            "net_invested_change_inr": 0.0,
            "net_wealth_generated_inr": 0.0,
            "absolute_growth_pct": None,
            "peak_valuation_inr": 0.0,
            "peak_valuation_date": None,
            "trough_valuation_inr": 0.0,
            "trough_valuation_date": None,
            "trajectory": [],
        }

    initial_pt = points[0]
    latest_pt = points[-1]

    initial_val = initial_pt["value_inr"]
    latest_val = latest_pt["value_inr"]
    initial_inv = initial_pt["invested_inr"]
    latest_inv = latest_pt["invested_inr"]

    net_invested_change = round(latest_inv - initial_inv, 2)
    net_wealth_generated = round(latest_val - latest_inv, 2)
    absolute_growth_pct = (
        round(((latest_val - initial_val) / initial_val) * 100, 2)
        if initial_val > 0
        else None
    )

    peak_pt = max(points, key=lambda p: p["value_inr"])
    trough_pt = min(points, key=lambda p: p["value_inr"])

    trajectory: list[dict[str, Any]] = []
    prev_val: Optional[float] = None
    prev_inv: Optional[float] = None

    for p in points:
        val = p["value_inr"]
        inv = p["invested_inr"]
        unrealized_gain = round(val - inv, 2)
        unrealized_gain_pct = round((unrealized_gain / inv) * 100, 2) if inv > 0 else None

        period_change = round(val - prev_val, 2) if prev_val is not None else 0.0
        period_return_pct = (
            round((period_change / prev_val) * 100, 2)
            if prev_val is not None and prev_val > 0
            else None
        )
        net_inflow = round(inv - prev_inv, 2) if prev_inv is not None else 0.0

        trajectory.append(
            {
                "date": p["date"],
                "value_inr": val,
                "invested_inr": inv,
                "unrealized_gain_inr": unrealized_gain,
                "unrealized_gain_pct": unrealized_gain_pct,
                "period_change_inr": period_change,
                "period_return_pct": period_return_pct,
                "net_inflow_inr": net_inflow,
                "stale": p["stale"],
            }
        )
        prev_val = val
        prev_inv = inv

    return {
        "investor_id": investor_id,
        "granularity": granularity,
        "start_date": initial_pt["date"],
        "end_date": latest_pt["date"],
        "data_points_count": len(points),
        "initial_value_inr": initial_val,
        "latest_value_inr": latest_val,
        "initial_invested_inr": initial_inv,
        "latest_invested_inr": latest_inv,
        "net_invested_change_inr": net_invested_change,
        "net_wealth_generated_inr": net_wealth_generated,
        "absolute_growth_pct": absolute_growth_pct,
        "peak_valuation_inr": peak_pt["value_inr"],
        "peak_valuation_date": peak_pt["date"],
        "trough_valuation_inr": trough_pt["value_inr"],
        "trough_valuation_date": trough_pt["date"],
        "trajectory": trajectory,
    }


# ===========================================================================
# 2. Historical Drawdown Analysis
# ===========================================================================

async def get_historical_drawdown_analysis(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    value_series: ValueSeries | dict[str, Any] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Compute peak-to-trough drawdowns, maximum drawdown (MDD), recovery, and episodes.

    Args:
        investor_id: Unique investor ID.
        from_date: Start date.
        to_date: End date.
        granularity: Sampling frequency.
        value_series: Pre-fetched ValueSeries model or dict.
        repo: Optional PortfolioRepository instance.

    Returns:
        Structured drawdown analysis metrics and series.
    """
    points = await _resolve_value_series(
        investor_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        value_series=value_series,
        repo=repo,
    )

    if not points:
        return {
            "investor_id": investor_id,
            "max_drawdown_pct": 0.0,
            "max_drawdown_inr": 0.0,
            "peak_date": None,
            "peak_value_inr": 0.0,
            "trough_date": None,
            "trough_value_inr": 0.0,
            "recovery_date": None,
            "is_recovered": True,
            "recovery_duration_days": None,
            "current_drawdown_pct": 0.0,
            "current_drawdown_inr": 0.0,
            "is_at_all_time_high": True,
            "average_drawdown_pct": 0.0,
            "drawdown_episodes": [],
            "drawdown_series": [],
        }

    running_peak = points[0]["value_inr"]
    running_peak_date = points[0]["date"]

    drawdown_series: list[dict[str, Any]] = []
    max_dd_pct = 0.0
    max_dd_inr = 0.0
    mdd_peak_val = running_peak
    mdd_peak_date = running_peak_date
    mdd_trough_val = running_peak
    mdd_trough_date = running_peak_date
    mdd_trough_idx = 0

    peaks_history: list[tuple[float, str]] = []

    for idx, p in enumerate(points):
        val = p["value_inr"]
        d_str = p["date"]

        if val >= running_peak:
            running_peak = val
            running_peak_date = d_str

        peaks_history.append((running_peak, running_peak_date))

        dd_inr = round(val - running_peak, 2)
        dd_pct = (
            round(((val - running_peak) / running_peak) * 100, 2)
            if running_peak > 0
            else 0.0
        )

        drawdown_series.append(
            {
                "date": d_str,
                "value_inr": val,
                "peak_value_inr": running_peak,
                "drawdown_inr": dd_inr,
                "drawdown_pct": dd_pct,
            }
        )

        if dd_pct < max_dd_pct:
            max_dd_pct = dd_pct
            max_dd_inr = dd_inr
            mdd_peak_val = running_peak
            mdd_peak_date = running_peak_date
            mdd_trough_val = val
            mdd_trough_date = d_str
            mdd_trough_idx = idx

    # Determine recovery date for MDD
    recovery_date: Optional[str] = None
    is_recovered = True
    recovery_duration_days: Optional[int] = None

    if max_dd_pct < 0:
        is_recovered = False
        for p in points[mdd_trough_idx + 1:]:
            if p["value_inr"] >= mdd_peak_val:
                recovery_date = p["date"]
                is_recovered = True
                trough_d = _parse_date(mdd_trough_date)
                rec_d = _parse_date(recovery_date)
                if trough_d and rec_d:
                    recovery_duration_days = (rec_d - trough_d).days
                break

    # Current drawdown
    latest_pt = drawdown_series[-1]
    current_dd_pct = latest_pt["drawdown_pct"]
    current_dd_inr = latest_pt["drawdown_inr"]
    is_at_ath = current_dd_pct >= 0.0

    # Average non-zero drawdown
    negative_dds = [pt["drawdown_pct"] for pt in drawdown_series if pt["drawdown_pct"] < 0]
    avg_dd_pct = (
        round(sum(negative_dds) / len(negative_dds), 2) if negative_dds else 0.0
    )

    # Detect major drawdown episodes (drawdown deeper than 1%)
    episodes: list[dict[str, Any]] = []
    in_episode = False
    current_ep_peak = points[0]["value_inr"]
    current_ep_peak_date = points[0]["date"]
    current_ep_min_val = points[0]["value_inr"]
    current_ep_min_date = points[0]["date"]
    current_ep_min_pct = 0.0

    for idx, pt in enumerate(drawdown_series):
        dd_pct = pt["drawdown_pct"]
        if dd_pct < 0:
            if not in_episode:
                in_episode = True
                current_ep_peak = pt["peak_value_inr"]
                current_ep_peak_date = peaks_history[idx][1]
                current_ep_min_val = pt["value_inr"]
                current_ep_min_date = pt["date"]
                current_ep_min_pct = dd_pct
            else:
                if dd_pct < current_ep_min_pct:
                    current_ep_min_pct = dd_pct
                    current_ep_min_val = pt["value_inr"]
                    current_ep_min_date = pt["date"]
        else:
            if in_episode:
                # Episode recovered
                if abs(current_ep_min_pct) >= 1.0:
                    episodes.append(
                        {
                            "peak_date": current_ep_peak_date,
                            "peak_value_inr": current_ep_peak,
                            "trough_date": current_ep_min_date,
                            "trough_value_inr": current_ep_min_val,
                            "recovery_date": pt["date"],
                            "max_drawdown_pct": current_ep_min_pct,
                            "is_recovered": True,
                        }
                    )
                in_episode = False

    # If currently in an unrecovered episode
    if in_episode and abs(current_ep_min_pct) >= 1.0:
        episodes.append(
            {
                "peak_date": current_ep_peak_date,
                "peak_value_inr": current_ep_peak,
                "trough_date": current_ep_min_date,
                "trough_value_inr": current_ep_min_val,
                "recovery_date": None,
                "max_drawdown_pct": current_ep_min_pct,
                "is_recovered": False,
            }
        )

    # Sort episodes by severity
    episodes.sort(key=lambda ep: ep["max_drawdown_pct"])

    return {
        "investor_id": investor_id,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_inr": max_dd_inr,
        "peak_date": mdd_peak_date,
        "peak_value_inr": mdd_peak_val,
        "trough_date": mdd_trough_date,
        "trough_value_inr": mdd_trough_val,
        "recovery_date": recovery_date,
        "is_recovered": is_recovered,
        "recovery_duration_days": recovery_duration_days,
        "current_drawdown_pct": current_dd_pct,
        "current_drawdown_inr": current_dd_inr,
        "is_at_all_time_high": is_at_ath,
        "average_drawdown_pct": avg_dd_pct,
        "drawdown_episodes": episodes[:5],
        "drawdown_series": drawdown_series,
    }


# ===========================================================================
# 3. Risk-Adjusted Returns & Volatility Analytics
# ===========================================================================

async def get_historical_risk_and_returns(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    risk_free_rate: float = 0.065,
    value_series: ValueSeries | dict[str, Any] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Calculate annualized volatility, downside risk, CAGR, Sharpe, Sortino, and Calmar ratios.

    Args:
        investor_id: Unique investor ID.
        from_date: Start date.
        to_date: End date.
        granularity: 'daily', 'weekly', or 'monthly'.
        risk_free_rate: Annualized risk-free benchmark rate (default: 0.065 = 6.5%).
        value_series: Pre-fetched ValueSeries model or dict.
        repo: Optional PortfolioRepository instance.

    Returns:
        Structured risk-adjusted return and volatility dictionary.
    """
    points = await _resolve_value_series(
        investor_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        value_series=value_series,
        repo=repo,
    )

    ann_factor = 12 if granularity == "monthly" else (52 if granularity == "weekly" else 252)

    if len(points) < 2:
        return {
            "investor_id": investor_id,
            "granularity": granularity,
            "periods_evaluated": 0,
            "annualized_return_cagr": None,
            "mean_period_return_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "downside_deviation_pct": 0.0,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "calmar_ratio": None,
            "best_period": None,
            "worst_period": None,
            "positive_periods_count": 0,
            "negative_periods_count": 0,
            "win_rate_pct": 0.0,
            "returns_distribution": {
                "min_return_pct": 0.0,
                "max_return_pct": 0.0,
                "median_return_pct": 0.0,
                "std_deviation_pct": 0.0,
            },
        }

    # Calculate periodic cash-flow adjusted returns
    returns: list[float] = []
    return_dates: list[str] = []

    for i in range(1, len(points)):
        prev_p = points[i - 1]
        curr_p = points[i]

        prev_val = prev_p["value_inr"]
        curr_val = curr_p["value_inr"]
        net_inflow = curr_p["invested_inr"] - prev_p["invested_inr"]

        if prev_val > 0:
            # Modified Dietz periodic return adjusting for capital additions
            period_ret = (curr_val - prev_val - net_inflow) / prev_val
        else:
            period_ret = 0.0

        returns.append(period_ret)
        return_dates.append(curr_p["date"])

    # Mean and Volatility
    mean_ret = statistics.mean(returns) if returns else 0.0
    stdev_ret = statistics.stdev(returns) if len(returns) > 1 else 0.0
    ann_volatility = stdev_ret * math.sqrt(ann_factor) * 100

    # Downside deviation relative to risk-free rate per period
    periodic_rf = risk_free_rate / ann_factor
    underperformances = [(r - periodic_rf) ** 2 for r in returns if r < periodic_rf]
    downside_var = (
        sum(underperformances) / len(returns) if underperformances else 0.0
    )
    downside_deviation = math.sqrt(downside_var) * math.sqrt(ann_factor) * 100

    # CAGR calculation across total days
    start_d = points[0]["_date_obj"]
    end_d = points[-1]["_date_obj"]
    total_days = (end_d - start_d).days
    initial_val = points[0]["value_inr"]
    latest_val = points[-1]["value_inr"]

    cagr: Optional[float] = None
    if total_days > 0 and initial_val > 0 and latest_val > 0:
        years = total_days / 365.25
        try:
            cagr = ((latest_val / initial_val) ** (1.0 / years)) - 1.0
        except Exception:
            cagr = None

    cagr_pct = round(cagr * 100, 2) if cagr is not None else None

    # Sharpe Ratio: (CAGR - Rf) / Annualized Volatility
    sharpe: Optional[float] = None
    if cagr is not None and ann_volatility > 0:
        sharpe = round((cagr - risk_free_rate) / (ann_volatility / 100), 2)

    # Sortino Ratio: (CAGR - Rf) / Downside Deviation
    sortino: Optional[float] = None
    if cagr is not None and downside_deviation > 0:
        sortino = round((cagr - risk_free_rate) / (downside_deviation / 100), 2)

    # Calmar Ratio: CAGR / |MDD|
    calmar: Optional[float] = None
    dd_analysis = await get_historical_drawdown_analysis(
        investor_id,
        value_series={"points": points},
    )
    mdd_pct = dd_analysis.get("max_drawdown_pct", 0.0)
    if cagr is not None and mdd_pct < 0:
        calmar = round(cagr / (abs(mdd_pct) / 100), 2)

    # Period Extremes
    returns_pct = [r * 100 for r in returns]
    best_idx = returns.index(max(returns)) if returns else 0
    worst_idx = returns.index(min(returns)) if returns else 0

    best_period = {
        "date": return_dates[best_idx],
        "return_pct": round(returns_pct[best_idx], 2),
    } if returns else None

    worst_period = {
        "date": return_dates[worst_idx],
        "return_pct": round(returns_pct[worst_idx], 2),
    } if returns else None

    pos_count = sum(1 for r in returns if r > 0)
    neg_count = sum(1 for r in returns if r < 0)
    win_rate = round((pos_count / len(returns)) * 100, 2) if returns else 0.0

    return {
        "investor_id": investor_id,
        "granularity": granularity,
        "periods_evaluated": len(returns),
        "annualized_return_cagr": cagr_pct,
        "mean_period_return_pct": round(mean_ret * 100, 2),
        "annualized_volatility_pct": round(ann_volatility, 2),
        "downside_deviation_pct": round(downside_deviation, 2),
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "best_period": best_period,
        "worst_period": worst_period,
        "positive_periods_count": pos_count,
        "negative_periods_count": neg_count,
        "win_rate_pct": win_rate,
        "returns_distribution": {
            "min_return_pct": round(min(returns_pct), 2) if returns_pct else 0.0,
            "max_return_pct": round(max(returns_pct), 2) if returns_pct else 0.0,
            "median_return_pct": round(statistics.median(returns_pct), 2) if returns_pct else 0.0,
            "std_deviation_pct": round(stdev_ret * 100, 2),
        },
    }


# ===========================================================================
# 4. Historical Cash Flows & Discipline Analytics
# ===========================================================================

async def get_historical_cashflows(
    investor_id: int,
    transactions: list[Transaction] | list[dict[str, Any]] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Analyze transaction ledgers, capital inflows/outflows, SIP discipline, and velocity.

    Args:
        investor_id: Unique investor ID.
        transactions: Pre-fetched transaction list.
        repo: Optional PortfolioRepository instance.

    Returns:
        Structured cash flow intelligence dictionary.
    """
    txns = await _resolve_transactions(investor_id, transactions=transactions, repo=repo)

    if not txns:
        return {
            "investor_id": investor_id,
            "total_transactions_count": 0,
            "first_transaction_date": None,
            "latest_transaction_date": None,
            "portfolio_vintage_years": 0.0,
            "total_gross_inflows_inr": 0.0,
            "total_gross_outflows_inr": 0.0,
            "net_cash_invested_inr": 0.0,
            "total_fees_inr": 0.0,
            "total_stamp_duty_inr": 0.0,
            "total_brokerage_inr": 0.0,
            "sip_metrics": {
                "total_sip_amount_inr": 0.0,
                "total_sip_count": 0,
                "average_sip_amount_inr": 0.0,
                "sip_share_of_inflows_pct": 0.0,
                "lumpsum_amount_inr": 0.0,
                "lumpsum_count": 0,
            },
            "yearly_summary": [],
            "breakdown_by_type": {},
        }

    first_date = txns[0]["date"]
    latest_date = txns[-1]["date"]
    vintage_days = (txns[-1]["_date_obj"] - txns[0]["_date_obj"]).days
    vintage_years = round(vintage_days / 365.25, 1)

    inflow_types = {
        "PURCHASE",
        "BUY",
        "SIP",
        "SIP PURCHASE",
        "SWITCH_IN",
        "SWITCH IN",
        "ADDITIONAL PURCHASE",
        "DIVIDEND REINVESTMENT",
        "DIVIDEND_REINVESTMENT",
    }
    outflow_types = {
        "REDEMPTION",
        "SELL",
        "SWITCH_OUT",
        "SWITCH OUT",
        "SWP",
        "DIVIDEND PAYOUT",
        "DIVIDEND_PAYOUT",
    }

    total_inflows = 0.0
    total_outflows = 0.0
    total_fees = 0.0
    total_stamp = 0.0
    total_brokerage = 0.0

    sip_amount = 0.0
    sip_count = 0
    lump_amount = 0.0
    lump_count = 0

    yearly_buckets: dict[int, dict[str, Any]] = {}
    type_buckets: dict[str, dict[str, Any]] = {}

    for t in txns:
        amount = t["amount"]
        ttype = t["transaction_type"]
        narration = t["narration"].upper()
        year = t["_date_obj"].year

        total_fees += t["fees"]
        total_stamp += t["stamp_duty"]
        total_brokerage += t["brokerage"]

        # Track type breakdown
        if ttype not in type_buckets:
            type_buckets[ttype] = {"count": 0, "total_amount_inr": 0.0}
        type_buckets[ttype]["count"] += 1
        type_buckets[ttype]["total_amount_inr"] = round(
            type_buckets[ttype]["total_amount_inr"] + amount, 2
        )

        # Track yearly summary
        if year not in yearly_buckets:
            yearly_buckets[year] = {
                "year": year,
                "inflows_inr": 0.0,
                "outflows_inr": 0.0,
                "net_inflow_inr": 0.0,
                "sip_amount_inr": 0.0,
                "transactions_count": 0,
            }
        yearly_buckets[year]["transactions_count"] += 1

        is_sip = "SIP" in ttype or "SYSTEMATIC" in narration or "SIP" in narration

        if ttype in inflow_types or not (ttype in outflow_types):
            total_inflows += amount
            yearly_buckets[year]["inflows_inr"] = round(
                yearly_buckets[year]["inflows_inr"] + amount, 2
            )
            if is_sip:
                sip_amount += amount
                sip_count += 1
                yearly_buckets[year]["sip_amount_inr"] = round(
                    yearly_buckets[year]["sip_amount_inr"] + amount, 2
                )
            else:
                lump_amount += amount
                lump_count += 1
        elif ttype in outflow_types:
            total_outflows += amount
            yearly_buckets[year]["outflows_inr"] = round(
                yearly_buckets[year]["outflows_inr"] + amount, 2
            )

    for yb in yearly_buckets.values():
        yb["net_inflow_inr"] = round(yb["inflows_inr"] - yb["outflows_inr"], 2)

    yearly_summary = sorted(yearly_buckets.values(), key=lambda x: x["year"])
    sip_share_pct = (
        round((sip_amount / total_inflows) * 100, 2) if total_inflows > 0 else 0.0
    )
    avg_sip = round(sip_amount / sip_count, 2) if sip_count > 0 else 0.0

    return {
        "investor_id": investor_id,
        "total_transactions_count": len(txns),
        "first_transaction_date": first_date,
        "latest_transaction_date": latest_date,
        "portfolio_vintage_years": vintage_years,
        "total_gross_inflows_inr": round(total_inflows, 2),
        "total_gross_outflows_inr": round(total_outflows, 2),
        "net_cash_invested_inr": round(total_inflows - total_outflows, 2),
        "total_fees_inr": round(total_fees, 2),
        "total_stamp_duty_inr": round(total_stamp, 2),
        "total_brokerage_inr": round(total_brokerage, 2),
        "sip_metrics": {
            "total_sip_amount_inr": round(sip_amount, 2),
            "total_sip_count": sip_count,
            "average_sip_amount_inr": avg_sip,
            "sip_share_of_inflows_pct": sip_share_pct,
            "lumpsum_amount_inr": round(lump_amount, 2),
            "lumpsum_count": lump_count,
        },
        "yearly_summary": yearly_summary,
        "breakdown_by_type": type_buckets,
    }


# ===========================================================================
# 5. Historical Realized Capital Gains & Tax Efficiency
# ===========================================================================

async def get_historical_capital_gains(
    investor_id: int,
    fy_points: list[CapitalGainsFyPoint] | list[dict[str, Any]] | None = None,
    include_unreconciled: bool = False,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Calculate realized capital gains history, STCG vs LTCG totals, and annual tax trajectory.

    Args:
        investor_id: Unique investor ID.
        fy_points: Pre-fetched CapitalGainsFyPoint list or dict.
        include_unreconciled: Whether to include unreconciled lots.
        repo: Optional PortfolioRepository instance.

    Returns:
        Structured historical capital gains analysis.
    """
    gains = await _resolve_capital_gains(
        investor_id,
        fy_points=fy_points,
        include_unreconciled=include_unreconciled,
        repo=repo,
    )

    if not gains:
        return {
            "investor_id": investor_id,
            "financial_years_count": 0,
            "cumulative_stcg_inr": 0.0,
            "cumulative_ltcg_inr": 0.0,
            "cumulative_realized_gain_inr": 0.0,
            "profitable_financial_years": 0,
            "loss_making_financial_years": 0,
            "fy_breakdown": [],
        }

    total_stcg = round(sum(g["stcg_inr"] for g in gains), 2)
    total_ltcg = round(sum(g["ltcg_inr"] for g in gains), 2)
    cum_gain = round(total_stcg + total_ltcg, 2)

    profitable_fys = sum(1 for g in gains if g["total_gain_inr"] > 0)
    loss_fys = sum(1 for g in gains if g["total_gain_inr"] < 0)

    return {
        "investor_id": investor_id,
        "financial_years_count": len(gains),
        "cumulative_stcg_inr": total_stcg,
        "cumulative_ltcg_inr": total_ltcg,
        "cumulative_realized_gain_inr": cum_gain,
        "profitable_financial_years": profitable_fys,
        "loss_making_financial_years": loss_fys,
        "fy_breakdown": gains,
    }


# ===========================================================================
# 6. Scheme Historical Tenure & Holding Analysis
# ===========================================================================

async def get_historical_scheme_tenure(
    investor_id: int,
    security_id: int,
    scheme_detail: SchemeDetail | dict[str, Any] | None = None,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Calculate scheme-level holding vintage, transactions count, and average purchase price.

    Args:
        investor_id: Unique investor ID.
        security_id: Security / Scheme ID.
        scheme_detail: Pre-fetched SchemeDetail model or dict.
        repo: Optional PortfolioRepository instance.

    Returns:
        Structured scheme tenure and acquisition intelligence.
    """
    if scheme_detail is None:
        active_repo = repo or PortfolioRepository()
        detail = await active_repo.get_holding(investor_id, security_id)
    else:
        detail = scheme_detail

    if hasattr(detail, "model_dump"):
        data = detail.model_dump()
    elif isinstance(detail, dict):
        data = detail
    else:
        data = {}

    sec = data.get("security", {})
    sec_name = sec.get("name", "")
    isin = sec.get("isin", "")
    category = sec.get("category", "")

    txns = data.get("transactions", [])
    buy_txns = [
        t for t in txns
        if str(t.get("transaction_type", "")).upper() in {"BUY", "PURCHASE", "SIP"}
    ]

    buy_amounts = [_to_float(t.get("amount")) for t in buy_txns if t.get("amount") is not None]
    buy_units = [_to_float(t.get("units")) for t in buy_txns if t.get("units") is not None]

    valid_amounts = [a for a in buy_amounts if a is not None]
    valid_units = [u for u in buy_units if u is not None and u > 0]

    tot_buy_amt = sum(valid_amounts)
    tot_buy_units = sum(valid_units)
    avg_buy_nav = (
        round(tot_buy_amt / tot_buy_units, 4) if tot_buy_units > 0 else None
    )

    first_d: Optional[str] = None
    latest_d: Optional[str] = None
    tenure_days: Optional[int] = None
    tenure_years: Optional[float] = None

    parsed_dates = [
        _parse_date(t.get("date")) for t in txns if t.get("date") is not None
    ]
    valid_dates = [d for d in parsed_dates if d is not None]
    if valid_dates:
        valid_dates.sort()
        first_d = valid_dates[0].isoformat()
        latest_d = valid_dates[-1].isoformat()
        tenure_days = (valid_dates[-1] - valid_dates[0]).days
        tenure_years = round(tenure_days / 365.25, 2)

    latest_nav = _to_float(data.get("latest_nav"))
    nav_multiple = (
        round(latest_nav / avg_buy_nav, 2)
        if latest_nav is not None and avg_buy_nav is not None and avg_buy_nav > 0
        else None
    )

    return {
        "security_id": security_id,
        "name": sec_name,
        "isin": isin,
        "category": category,
        "first_transaction_date": first_d,
        "latest_transaction_date": latest_d,
        "tenure_days": tenure_days,
        "tenure_years": tenure_years,
        "total_units": _to_float(data.get("units")),
        "current_value_inr": _to_float(data.get("value_inr")),
        "invested_inr": _to_float(data.get("invested_inr")),
        "total_transactions_count": len(txns),
        "buy_transactions_count": len(buy_txns),
        "avg_buy_nav": avg_buy_nav,
        "latest_nav": latest_nav,
        "nav_multiple": nav_multiple,
        "return_pct": (
            round(data["return_pct"] * 100, 2)
            if data.get("return_pct") is not None
            else None
        ),
        "xirr": (
            round(data["xirr"] * 100, 2)
            if data.get("xirr") is not None
            else None
        ),
        "nav_history_points_count": len(data.get("nav_history", [])),
    }


# ===========================================================================
# 7. Master 360° Historical Portfolio Intelligence Report
# ===========================================================================

async def analyze_portfolio_historical(
    investor_id: int,
    from_date: date | str | None = None,
    to_date: date | str | None = None,
    granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    risk_free_rate: float = 0.065,
    repo: Optional[PortfolioRepository] = None,
) -> dict[str, Any]:
    """Generate consolidated master 360-degree historical portfolio intelligence report.

    Aggregates net worth trajectory, maximum drawdown, risk-adjusted ratios (Sharpe/Sortino),
    cash flow discipline, and capital gains history into a unified response.

    Args:
        investor_id: Unique investor ID.
        from_date: Start date for time series.
        to_date: End date for time series.
        granularity: 'daily', 'weekly', or 'monthly'.
        risk_free_rate: Risk-free rate for Sharpe/Sortino ratios (default: 0.065).
        repo: Optional PortfolioRepository instance.

    Returns:
        Consolidated master historical intelligence report.
    """
    active_repo = repo or PortfolioRepository()

    # Fetch status
    try:
        raw_status = await active_repo.get_valuation_status(investor_id)
        val_status = {
            "status": getattr(raw_status, "status", "UNKNOWN"),
            "is_provisional": getattr(raw_status, "is_provisional", False),
            "computed_through": (
                raw_status.computed_through.isoformat()
                if getattr(raw_status, "computed_through", None)
                else None
            ),
        }
    except Exception:
        val_status = {"status": "UNKNOWN", "is_provisional": False, "computed_through": None}

    # Parallelize / resolve components
    trajectory = await get_historical_valuation_trajectory(
        investor_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        repo=active_repo,
    )

    drawdown = await get_historical_drawdown_analysis(
        investor_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        value_series={"points": trajectory.get("trajectory", [])},
        repo=active_repo,
    )

    risk_returns = await get_historical_risk_and_returns(
        investor_id,
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        risk_free_rate=risk_free_rate,
        value_series={"points": trajectory.get("trajectory", [])},
        repo=active_repo,
    )

    cashflows = await get_historical_cashflows(
        investor_id,
        repo=active_repo,
    )

    capital_gains = await get_historical_capital_gains(
        investor_id,
        repo=active_repo,
    )

    # Deterministic factual insights synthesis
    insights: list[str] = []

    cagr_val = risk_returns.get("annualized_return_cagr")
    if cagr_val is not None:
        insights.append(
            f"Portfolio compounded at an annualized CAGR of {cagr_val}% across recorded periods."
        )

    mdd_val = drawdown.get("max_drawdown_pct", 0.0)
    if mdd_val < 0:
        trough_date = drawdown.get("trough_date")
        rec_status = "fully recovered" if drawdown.get("is_recovered") else "currently unrecovered"
        insights.append(
            f"Maximum peak-to-trough drawdown was {mdd_val}% on {trough_date} ({rec_status})."
        )

    sharpe_val = risk_returns.get("sharpe_ratio")
    if sharpe_val is not None:
        insights.append(
            f"Risk-adjusted Sharpe ratio stands at {sharpe_val} (benchmark Rf: {risk_free_rate * 100:.1f}%)."
        )

    sip_share = cashflows.get("sip_metrics", {}).get("sip_share_of_inflows_pct", 0.0)
    if sip_share > 0:
        insights.append(
            f"Systematic investments (SIP) account for {sip_share}% of total capital inflows."
        )

    cum_gain = capital_gains.get("cumulative_realized_gain_inr", 0.0)
    if cum_gain != 0.0:
        insights.append(
            f"Cumulative realized capital gains across all financial years total ₹{cum_gain:,.2f}."
        )

    return {
        "investor_id": investor_id,
        "as_of": str(date.today()),
        "valuation_status": val_status,
        "trajectory_summary": {
            "initial_value_inr": trajectory.get("initial_value_inr"),
            "latest_value_inr": trajectory.get("latest_value_inr"),
            "net_invested_change_inr": trajectory.get("net_invested_change_inr"),
            "net_wealth_generated_inr": trajectory.get("net_wealth_generated_inr"),
            "absolute_growth_pct": trajectory.get("absolute_growth_pct"),
            "peak_valuation_inr": trajectory.get("peak_valuation_inr"),
            "peak_valuation_date": trajectory.get("peak_valuation_date"),
        },
        "drawdown_summary": {
            "max_drawdown_pct": drawdown.get("max_drawdown_pct"),
            "max_drawdown_inr": drawdown.get("max_drawdown_inr"),
            "current_drawdown_pct": drawdown.get("current_drawdown_pct"),
            "is_at_all_time_high": drawdown.get("is_at_all_time_high"),
            "is_recovered": drawdown.get("is_recovered"),
        },
        "risk_adjusted_performance": {
            "annualized_return_cagr": risk_returns.get("annualized_return_cagr"),
            "annualized_volatility_pct": risk_returns.get("annualized_volatility_pct"),
            "downside_deviation_pct": risk_returns.get("downside_deviation_pct"),
            "sharpe_ratio": risk_returns.get("sharpe_ratio"),
            "sortino_ratio": risk_returns.get("sortino_ratio"),
            "calmar_ratio": risk_returns.get("calmar_ratio"),
            "win_rate_pct": risk_returns.get("win_rate_pct"),
        },
        "cashflow_discipline": {
            "total_gross_inflows_inr": cashflows.get("total_gross_inflows_inr"),
            "net_cash_invested_inr": cashflows.get("net_cash_invested_inr"),
            "portfolio_vintage_years": cashflows.get("portfolio_vintage_years"),
            "sip_metrics": cashflows.get("sip_metrics"),
        },
        "realized_tax_summary": {
            "cumulative_stcg_inr": capital_gains.get("cumulative_stcg_inr"),
            "cumulative_ltcg_inr": capital_gains.get("cumulative_ltcg_inr"),
            "cumulative_realized_gain_inr": capital_gains.get("cumulative_realized_gain_inr"),
        },
        "key_insights": insights,
        "full_trajectory": trajectory.get("trajectory", []),
        "drawdown_episodes": drawdown.get("drawdown_episodes", []),
        "yearly_cashflow_summary": cashflows.get("yearly_summary", []),
        "capital_gains_by_fy": capital_gains.get("fy_breakdown", []),
    }
