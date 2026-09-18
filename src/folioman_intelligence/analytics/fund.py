"""Mutual Fund Analytics Layer.

Defines domain-specific analytical functions for mutual funds.
Performs deterministic calculations, metrics aggregation, MPT ratios,
portfolio concentration, sector rotation, peer benchmarking, manager analysis,
taxation, and health audit.
"""

from __future__ import annotations

from datetime import datetime, timezone
import statistics
from typing import Any, Optional

from src.folioman_intelligence.repository.fund import MutualFundRepository


async def _resolve_fund_data(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
    hint_name: Optional[str] = None,
) -> dict[str, Any]:
    """Helper to fetch standardized fund data if not already provided."""
    if fund_data is not None:
        return fund_data
    repo = MutualFundRepository()
    return await repo.get_fund_data(identifier, hint_name=hint_name)


def _calc_fund_age_years(inception_timestamp: Any) -> Optional[float]:
    """Calculate fund age in years from Unix epoch timestamp string or int."""
    if not inception_timestamp:
        return None
    try:
        ts = float(inception_timestamp)
        # Convert ms to seconds if timestamp is > 1e11
        if ts > 1e11:
            ts /= 1000.0
        launch_date = datetime.fromtimestamp(ts, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age_days = (now - launch_date).days
        return round(age_days / 365.25, 1)
    except Exception:
        return None


# ===========================================================================
# 1. Overview & Scheme Profile
# ===========================================================================
async def get_fund_overview(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate comprehensive baseline scheme overview and metadata."""
    data = await _resolve_fund_data(identifier, fund_data)

    nav = data.get("nav")
    nav_1d = data.get("nav_1d_change")
    nav_1d_pct = (
        round((nav_1d / (nav - nav_1d)) * 100, 2)
        if nav is not None and nav_1d is not None and (nav - nav_1d) != 0
        else None
    )

    fund_age = _calc_fund_age_years(data.get("inception_date"))
    aum = data.get("faq_ratios", {}).get("aum")

    # Extract min investment values
    tax_meta = data.get("tax_meta", {})
    min_sip = tax_meta.get("minSipAmount")
    min_lump = tax_meta.get("minLumpInvAmt")

    return {
        "mf_id": data.get("mf_id"),
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "isin": data.get("isin"),
        "slug": data.get("slug"),
        "amc": data.get("amc"),
        "plan": data.get("plan"),
        "option": data.get("option"),
        "category": data.get("category"),
        "subsector": data.get("subsector"),
        "subsector_description": data.get("subsector_desc"),
        "benchmark": data.get("benchmark"),
        "risk_classification": data.get("risk_classification"),
        "nav": nav,
        "nav_1d_change": nav_1d,
        "nav_1d_change_pct": nav_1d_pct,
        "fund_age_years": fund_age,
        "aum_in_cr": aum,
        "min_sip_amount": min_sip,
        "min_lumpsum_amount": min_lump,
        "sip_allowed": data.get("sip_allowed"),
        "lumpsum_allowed": data.get("lumpsum_allowed"),
        "objective": data.get("objective"),
        "exit_load_remarks": data.get("exit_load_remarks"),
    }


# ===========================================================================
# 2. Returns & Trailing Performance
# ===========================================================================
async def get_trailing_returns(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extract trailing returns across standard horizons (1Y, 3Y, 5Y, Life CAGR)."""
    data = await _resolve_fund_data(identifier, fund_data)

    returns_list = data.get("trailing_returns", [])
    returns_by_horizon: dict[str, Optional[float]] = {}
    for r in returns_list:
        duration = r.get("duration")
        val = r.get("value")
        if duration and val is not None:
            returns_by_horizon[duration] = round(val, 2)

    # Life CAGR from peers_tab_data for self
    life_cagr = None
    peers_tab = data.get("peers_tab_data", [])
    if peers_tab:
        self_tab = next(
            (p for p in peers_tab if p.get("mfId") == data.get("mf_id")),
            peers_tab[0],
        )
        cagr = self_tab.get("ratios", {}).get("retCagr")
        if cagr is not None:
            life_cagr = round(cagr, 2)

    return {
        "fund_name": data.get("name"),
        "return_1y": returns_by_horizon.get("1y"),
        "return_3y_cagr": returns_by_horizon.get("3y"),
        "return_5y_cagr": returns_by_horizon.get("5y"),
        "life_cagr": life_cagr,
        "all_trailing_returns": returns_list,
    }


async def get_cagr_history(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Analyze historical rolling CAGR trajectory to assess compounding consistency."""
    data = await _resolve_fund_data(identifier, fund_data)
    series = data.get("cagr_series", [])

    if not series:
        return {
            "fund_name": data.get("name"),
            "data_points_count": 0,
            "observations": [],
        }

    cagr_values = [
        pt["value"] for pt in series if "value" in pt and pt["value"] is not None
    ]
    if not cagr_values:
        return {
            "fund_name": data.get("name"),
            "data_points_count": 0,
            "observations": [],
        }

    min_cagr = round(min(cagr_values), 2)
    max_cagr = round(max(cagr_values), 2)
    median_cagr = round(statistics.median(cagr_values), 2)
    latest_cagr = round(cagr_values[0], 2)

    return {
        "fund_name": data.get("name"),
        "data_points_count": len(series),
        "latest_observation_cagr": latest_cagr,
        "min_cagr": min_cagr,
        "max_cagr": max_cagr,
        "median_cagr": median_cagr,
        "cagr_spread": round(max_cagr - min_cagr, 2),
        "observations": [
            {
                "year_diff": pt.get("yearDiff"),
                "cagr": round(pt.get("value", 0), 2),
            }
            for pt in series[:10]  # top 10 recent intervals
        ],
    }


# ===========================================================================
# 3. Risk, Volatility & Valuation
# ===========================================================================
async def get_risk_and_volatility(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Calculate MPT risk-adjusted ratios: Alpha, Beta/StdDev, Sharpe, Sortino."""
    data = await _resolve_fund_data(identifier, fund_data)

    faq_ratios = data.get("faq_ratios", {})
    key_ratios = {
        r.get("backL"): r.get("value")
        for r in data.get("key_ratios", [])
        if "backL" in r
    }

    alpha = faq_ratios.get("alpha")
    std_dev = faq_ratios.get("stdDev")
    sharpe = faq_ratios.get("sharpe") or key_ratios.get("sharpe")
    sortino = faq_ratios.get("sortino")
    cat_sharpe = key_ratios.get("catSharpe")

    sharpe_outperformance = (
        round(sharpe - cat_sharpe, 3)
        if sharpe is not None and cat_sharpe is not None
        else None
    )

    # Qualitative risk profile classification
    if sharpe and sharpe > 0.5:
        risk_profile = "High Risk-Adjusted Return (Strong Sharpe & Alpha)"
    elif sharpe and sharpe > 0:
        risk_profile = "Moderate Risk-Adjusted Return"
    else:
        risk_profile = "Subdued Risk-Adjusted Return"

    return {
        "fund_name": data.get("name"),
        "alpha": alpha,
        "standard_deviation": round(std_dev, 2) if std_dev is not None else None,
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "sortino_ratio": round(sortino, 3) if sortino is not None else None,
        "category_sharpe_ratio": (
            round(cat_sharpe, 3) if cat_sharpe is not None else None
        ),
        "sharpe_outperformance_vs_category": sharpe_outperformance,
        "risk_profile": risk_profile,
    }


async def get_portfolio_valuation(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Evaluate underlying portfolio valuation (P/E ratio) vs category benchmark."""
    data = await _resolve_fund_data(identifier, fund_data)

    faq_ratios = data.get("faq_ratios", {})
    key_ratios = {
        r.get("backL"): r.get("value")
        for r in data.get("key_ratios", [])
        if "backL" in r
    }

    fund_pe = faq_ratios.get("pe") or key_ratios.get("pe")
    cat_pe = key_ratios.get("catPe")

    premium_pct = None
    if fund_pe and cat_pe and cat_pe != 0:
        premium_pct = round(((fund_pe - cat_pe) / cat_pe) * 100, 2)

    return {
        "fund_name": data.get("name"),
        "portfolio_pe": round(fund_pe, 2) if fund_pe is not None else None,
        "category_pe": round(cat_pe, 2) if cat_pe is not None else None,
        "valuation_premium_pct": premium_pct,
        "valuation_status": (
            f"Trading at a {abs(premium_pct)}% premium vs category"
            if premium_pct and premium_pct > 0
            else (
                f"Trading at a {abs(premium_pct or 0)}% discount vs category"
                if premium_pct
                else "In line with category"
            )
        ),
    }


# ===========================================================================
# 4. Portfolio Holdings & Activity
# ===========================================================================
async def get_top_holdings(
    identifier: str,
    top_n: int = 10,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Analyze underlying stock holdings, top 5/10 concentration, and high conviction bets."""
    data = await _resolve_fund_data(identifier, fund_data)

    holdings = data.get("current_allocation", [])
    sorted_holdings = sorted(holdings, key=lambda x: x.get("latest") or 0, reverse=True)

    top_n_items = [
        {
            "rank": idx,
            "title": h.get("title"),
            "ticker": h.get("ticker"),
            "sid": h.get("sid"),
            "weight_pct": round(h.get("latest", 0), 2),
            "change_3m_pct": round(h.get("change3m", 0), 2),
            "type": h.get("type"),
            "rating": h.get("rating"),
        }
        for idx, h in enumerate(sorted_holdings[:top_n], start=1)
    ]

    top_5_weight = sum(h.get("latest", 0) for h in sorted_holdings[:5])
    top_10_weight = sum(h.get("latest", 0) for h in sorted_holdings[:10])

    high_conviction = [
        {
            "title": h.get("title"),
            "ticker": h.get("ticker"),
            "weight_pct": round(h.get("latest", 0), 2),
        }
        for h in sorted_holdings
        if (h.get("latest") or 0) >= 5.0
    ]

    return {
        "fund_name": data.get("name"),
        "total_holdings_count": len(holdings),
        "top_5_concentration_pct": round(top_5_weight, 2),
        "top_10_concentration_pct": round(top_10_weight, 2),
        "high_conviction_bets_count": len(high_conviction),
        "high_conviction_bets": high_conviction,
        "top_holdings": top_n_items,
    }


async def get_portfolio_activity(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Identify recent fund manager moves: accumulated vs trimmed stocks in the last 3 months."""
    data = await _resolve_fund_data(identifier, fund_data)

    holdings = data.get("current_allocation", [])

    accumulated = []
    trimmed = []
    for h in holdings:
        ch = h.get("change3m")
        if ch is not None and ch > 0:
            accumulated.append(
                {
                    "title": h.get("title"),
                    "ticker": h.get("ticker"),
                    "weight_pct": round(h.get("latest", 0), 2),
                    "change_3m_pct": round(ch, 2),
                }
            )
        elif ch is not None and ch < 0:
            trimmed.append(
                {
                    "title": h.get("title"),
                    "ticker": h.get("ticker"),
                    "weight_pct": round(h.get("latest", 0), 2),
                    "change_3m_pct": round(ch, 2),
                }
            )

    accumulated.sort(key=lambda x: x["change_3m_pct"], reverse=True)
    trimmed.sort(key=lambda x: x["change_3m_pct"])  # most negative first

    return {
        "fund_name": data.get("name"),
        "accumulated_stocks_count": len(accumulated),
        "trimmed_stocks_count": len(trimmed),
        "top_accumulated": accumulated[:10],
        "top_trimmed": trimmed[:10],
    }


async def search_stock_in_fund(
    identifier: str,
    query: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Check if a specific stock or company is held in the fund's portfolio."""
    data = await _resolve_fund_data(identifier, fund_data)

    q = query.strip().lower()
    holdings = data.get("current_allocation", [])
    matches = []

    for h in holdings:
        title = (h.get("title") or "").lower()
        ticker = (h.get("ticker") or "").lower()
        sid = (h.get("sid") or "").lower()

        if q in title or q in ticker or q in sid:
            matches.append(
                {
                    "title": h.get("title"),
                    "ticker": h.get("ticker"),
                    "sid": h.get("sid"),
                    "weight_pct": round(h.get("latest", 0), 2),
                    "change_3m_pct": round(h.get("change3m", 0), 2),
                    "type": h.get("type"),
                }
            )

    return {
        "fund_name": data.get("name"),
        "query": query,
        "is_held": len(matches) > 0,
        "matches_count": len(matches),
        "matches": matches,
    }


# ===========================================================================
# 5. Asset Allocation & Derivatives / Hedging
# ===========================================================================
async def get_asset_allocation(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Analyze current and historical asset allocation breakdown across asset classes."""
    data = await _resolve_fund_data(identifier, fund_data)

    history = data.get("asset_allocation_history", [])
    if not history:
        return {
            "fund_name": data.get("name"),
            "current_allocation": {},
            "history_periods_count": 0,
        }

    latest_entry = history[-1]
    holdings = latest_entry.get("holdings", [])

    breakdown = {h.get("assetClass"): round(h.get("value", 0), 2) for h in holdings}

    # Extract key specific classes
    equity = breakdown.get("Equity", 0.0)
    derivatives = breakdown.get("Futures & Options", 0.0)
    debt = breakdown.get("Treasury Bills", 0.0)
    cash = breakdown.get("Cash & Equivalents", 0.0)
    reits = breakdown.get("REITs & InvIT", breakdown.get("REITs & InvITs", 0.0))

    return {
        "fund_name": data.get("name"),
        "current_allocation": {
            "equity_pct": equity,
            "derivatives_fo_pct": derivatives,
            "debt_tbills_pct": debt,
            "cash_equivalents_pct": cash,
            "reits_invits_pct": reits,
            "full_breakdown": breakdown,
        },
        "has_active_derivatives": derivatives > 1.0,
        "history_periods_count": len(history),
    }


async def check_mandate_compliance(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Verify whether current asset allocation adheres to SEBI / Scheme limits."""
    data = await _resolve_fund_data(identifier, fund_data)

    targets = data.get("target_asset_allocation", [])
    history = data.get("asset_allocation_history", [])
    latest_entry = history[-1] if history else {}
    actual_holdings = {
        h.get("assetClass"): h.get("value", 0) for h in latest_entry.get("holdings", [])
    }

    compliance_results = []
    breaches = []
    for tgt in targets:
        asset_class = tgt.get("assetClass")
        min_lim = tgt.get("min", 0)
        max_lim = tgt.get("max", 100)

        # Match actual
        actual_val = actual_holdings.get(asset_class, 0.0)
        # Check tolerance
        is_compliant = min_lim <= actual_val <= max_lim
        status = {
            "asset_class": asset_class,
            "min_allowed_pct": min_lim,
            "max_allowed_pct": max_lim,
            "actual_pct": round(actual_val, 2),
            "compliant": is_compliant,
        }
        compliance_results.append(status)
        if not is_compliant:
            breaches.append(status)

    return {
        "fund_name": data.get("name"),
        "overall_compliant": len(breaches) == 0,
        "breaches_count": len(breaches),
        "breaches": breaches,
        "target_limits": compliance_results,
    }


# ===========================================================================
# 6. Sector Distribution & Sector Rotation Trends
# ===========================================================================
async def get_sector_allocation(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extract current sector weights and concentration metrics."""
    data = await _resolve_fund_data(identifier, fund_data)

    sectors = data.get("sector_distribution", [])
    if not sectors:
        return {
            "fund_name": data.get("name"),
            "sectors_count": 0,
            "top_sectors": [],
        }

    latest_sectors = sectors[-1].get("holdings", [])
    sorted_sectors = sorted(
        latest_sectors, key=lambda x: x.get("value") or 0, reverse=True
    )

    top_3_pct = sum(s.get("value", 0) for s in sorted_sectors[:3])
    top_5_pct = sum(s.get("value", 0) for s in sorted_sectors[:5])

    return {
        "fund_name": data.get("name"),
        "sectors_count": len(sorted_sectors),
        "top_3_sectors_concentration_pct": round(top_3_pct, 2),
        "top_5_sectors_concentration_pct": round(top_5_pct, 2),
        "top_sectors": [
            {
                "sector": s.get("sector"),
                "weight_pct": round(s.get("value", 0), 2),
            }
            for s in sorted_sectors[:10]
        ],
    }


async def get_sector_rotation_trends(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Analyze historical sector changes to identify macro sector rotation."""
    data = await _resolve_fund_data(identifier, fund_data)

    sector_history = data.get("sector_weightage", [])
    if not sector_history:
        return {
            "fund_name": data.get("name"),
            "tracked_sectors_count": 0,
            "expanding_sectors": [],
            "contracting_sectors": [],
        }

    shifts = []
    for sec in sector_history:
        name = sec.get("sector")
        holdings = sec.get("holdings", [])
        if len(holdings) >= 2:
            initial_val = holdings[0].get("value", 0)
            latest_val = holdings[-1].get("value", 0)
            delta = latest_val - initial_val
            shifts.append(
                {
                    "sector": name,
                    "initial_weight_pct": round(initial_val, 2),
                    "latest_weight_pct": round(latest_val, 2),
                    "change_pct": round(delta, 2),
                }
            )

    expanding = sorted(
        [s for s in shifts if s["change_pct"] > 0],
        key=lambda x: x["change_pct"],
        reverse=True,
    )
    contracting = sorted(
        [s for s in shifts if s["change_pct"] < 0], key=lambda x: x["change_pct"]
    )

    return {
        "fund_name": data.get("name"),
        "tracked_sectors_count": len(sector_history),
        "expanding_sectors": expanding[:5],
        "contracting_sectors": contracting[:5],
    }


# ===========================================================================
# 7. Peer Comparison & Ranking
# ===========================================================================
async def get_peer_comparison(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compare the scheme against category peers for returns, expense ratio, and rankings."""
    data = await _resolve_fund_data(identifier, fund_data)

    peers_tab = data.get("peers_tab_data", [])
    peers_summary = data.get("peers", [])

    # Map expense ratios from securitySummary.peers
    exp_ratios = {}
    for p in peers_summary:
        mf_id = p.get("mfId")
        for r in p.get("ratios", []):
            if r.get("backL") == "expRatio":
                exp_ratios[mf_id] = r.get("value")

    # Current fund's expense ratio
    key_ratios = {
        r.get("backL"): r.get("value")
        for r in data.get("key_ratios", [])
        if "backL" in r
    }
    exp_ratios[data.get("mf_id")] = key_ratios.get("expRatio")

    comparison_table = []
    for p in peers_tab:
        mid = p.get("mfId")
        ratios = p.get("ratios", {})
        ret_1y = ratios.get("ret1y")
        ret_3y = ratios.get("ret3y")
        ret_cagr = ratios.get("retCagr")
        exp = exp_ratios.get(mid)

        comparison_table.append(
            {
                "mf_id": mid,
                "name": p.get("name"),
                "return_1y": round(ret_1y, 2) if ret_1y is not None else None,
                "return_3y_cagr": round(ret_3y, 2) if ret_3y is not None else None,
                "life_cagr": round(ret_cagr, 2) if ret_cagr is not None else None,
                "expense_ratio": exp,
                "is_target_fund": mid == data.get("mf_id"),
            }
        )

    # Compute ranks for target fund
    target_id = data.get("mf_id")
    rank_1y = None
    rank_3y = None

    valid_1y = [p for p in comparison_table if p["return_1y"] is not None]
    valid_1y.sort(key=lambda x: x["return_1y"], reverse=True)
    for idx, p in enumerate(valid_1y, start=1):
        if p["mf_id"] == target_id:
            rank_1y = f"{idx} of {len(valid_1y)}"
            break

    valid_3y = [p for p in comparison_table if p["return_3y_cagr"] is not None]
    valid_3y.sort(key=lambda x: x["return_3y_cagr"], reverse=True)
    for idx, p in enumerate(valid_3y, start=1):
        if p["mf_id"] == target_id:
            rank_3y = f"{idx} of {len(valid_3y)}"
            break

    return {
        "fund_name": data.get("name"),
        "peer_group_size": len(comparison_table),
        "rank_1y_return": rank_1y,
        "rank_3y_cagr": rank_3y,
        "comparison_table": comparison_table,
    }


# ===========================================================================
# 8. Fund Managers Pedigree & Capacity
# ===========================================================================
async def get_fund_managers_analysis(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Analyze fund managers' qualifications, experience, total AUM, and workload."""
    data = await _resolve_fund_data(identifier, fund_data)

    managers = data.get("fund_managers", [])
    manager_profiles = []

    for m in managers:
        funds = m.get("funds", [])
        manager_profiles.append(
            {
                "name": m.get("name"),
                "qualification": m.get("qualification"),
                "experience_years": m.get("exp"),
                "aum_in_cr": m.get("aumInCr"),
                "other_funds_managed_count": len(funds),
                "sample_managed_funds": [
                    {
                        "name": f.get("name"),
                        "category": f.get("subsector"),
                        "return_1y": next(
                            (
                                r["value"]
                                for r in f.get("ratios", [])
                                if r.get("backL") == "ret1y"
                            ),
                            None,
                        ),
                        "return_3y": next(
                            (
                                r["value"]
                                for r in f.get("ratios", [])
                                if r.get("backL") == "ret3y"
                            ),
                            None,
                        ),
                    }
                    for f in funds[:3]
                ],
            }
        )

    return {
        "fund_name": data.get("name"),
        "fund_managers_count": len(manager_profiles),
        "manager_profiles": manager_profiles,
    }


# ===========================================================================
# 9. Costs, Exit Load & Tax Profile
# ===========================================================================
async def get_cost_and_tax_profile(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Extract expense ratio comparison, redemption exit load, and taxation rules."""
    data = await _resolve_fund_data(identifier, fund_data)

    key_ratios = {
        r.get("backL"): r.get("value")
        for r in data.get("key_ratios", [])
        if "backL" in r
    }
    exp_ratio = key_ratios.get("expRatio")
    cat_exp_ratio = key_ratios.get("catExpRatio")

    bps_advantage = None
    if exp_ratio is not None and cat_exp_ratio is not None:
        bps_advantage = round((cat_exp_ratio - exp_ratio) * 100, 1)

    tax_meta = data.get("tax_meta", {})
    rules = tax_meta.get("rules", [])

    return {
        "fund_name": data.get("name"),
        "expense_ratio_pct": exp_ratio,
        "category_expense_ratio_pct": cat_exp_ratio,
        "cost_advantage_basis_points": bps_advantage,
        "exit_load_remarks": data.get("exit_load_remarks"),
        "taxation_rules": rules,
        "fund_type": tax_meta.get("fundType", data.get("category")),
    }


# ===========================================================================
# 10. Scorecard & Red Flags Health Audit
# ===========================================================================
async def get_fund_health_audit(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate comprehensive health check across scorecard pillars and red flags."""
    data = await _resolve_fund_data(identifier, fund_data)

    scorecard_items = data.get("scorecard", [])
    pillars = [
        {
            "name": s.get("name"),
            "tag": s.get("tag"),
            "color": s.get("colour"),
            "description": s.get("description"),
        }
        for s in scorecard_items
    ]

    red_flags = data.get("total_red_flags", {})

    return {
        "fund_name": data.get("name"),
        "scorecard_pillars": pillars,
        "total_red_flags": red_flags,
        "has_red_flags": any(
            v > 0 for v in red_flags.values() if isinstance(v, (int, float))
        ),
    }


# ===========================================================================
# 11. Comprehensive Master Fund Due-Diligence Summary
# ===========================================================================
async def analyze_fund_comprehensive(
    identifier: str,
    fund_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Execute complete 360-degree fund analysis combining all core analytical domains."""
    data = await _resolve_fund_data(identifier, fund_data)

    overview = await get_fund_overview(identifier, fund_data=data)
    returns = await get_trailing_returns(identifier, fund_data=data)
    risk = await get_risk_and_volatility(identifier, fund_data=data)
    holdings = await get_top_holdings(identifier, top_n=5, fund_data=data)
    sectors = await get_sector_allocation(identifier, fund_data=data)
    costs = await get_cost_and_tax_profile(identifier, fund_data=data)
    health = await get_fund_health_audit(identifier, fund_data=data)

    return {
        "overview": overview,
        "performance": returns,
        "risk_and_volatility": risk,
        "top_holdings_concentration": {
            "top_5_concentration_pct": holdings.get("top_5_concentration_pct"),
            "top_5_stocks": holdings.get("top_holdings"),
        },
        "top_sectors": sectors.get("top_sectors", [])[:3],
        "costs_and_taxes": {
            "expense_ratio": costs.get("expense_ratio_pct"),
            "category_expense_ratio": costs.get("category_expense_ratio_pct"),
            "cost_advantage_bps": costs.get("cost_advantage_basis_points"),
            "exit_load": costs.get("exit_load_remarks"),
        },
        "health_and_red_flags": health,
    }
