"""
Deterministic projection engine.

Everything numeric that the dashboards plot is computed HERE, in Python,
from the user's inputs plus the qualitative assumptions the agents return
(growth rates, budget split percentages, channel mix, funnel conversions).

The LLM never produces a number that ends up on a chart axis — it produces
*assumptions* and *interpretations*, and this module turns those into series.
That keeps every chart internally consistent and reproducible.
"""
from __future__ import annotations

import math
import re

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

DEFAULT_BUDGET_SPLIT = [
    {"category": "Product / Engineering", "percent": 35.0},
    {"category": "Marketing & Sales", "percent": 20.0},
    {"category": "Infrastructure & Tooling", "percent": 15.0},
    {"category": "Team & Hiring", "percent": 15.0},
    {"category": "Compliance & Legal", "percent": 7.0},
    {"category": "Contingency Buffer", "percent": 8.0},
]


def _f(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def timeline_to_months(timeline: str | None, default: int = 6) -> int:
    """Parses '6 months', '1 year', '18 weeks', 'Q3' into a month count."""
    if not timeline:
        return default
    text = str(timeline).lower()
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    n = float(nums[0]) if nums else default

    if "year" in text or "yr" in text or "annum" in text:
        months = n * 12
    elif "week" in text:
        months = n / 4.345
    elif "day" in text:
        months = n / 30.0
    elif "quarter" in text or text.strip().startswith("q"):
        months = n * 3
    else:
        months = n

    return max(1, min(60, int(round(months))))


def normalize_percentages(items, key="percent"):
    """Rescales a list of dicts so their percent field sums to exactly 100."""
    clean = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        p = _f(it.get(key))
        if p > 0:
            row = dict(it)
            row[key] = p
            clean.append(row)
    if not clean:
        return []
    total = sum(r[key] for r in clean)
    if total <= 0:
        return []
    for r in clean:
        r[key] = round(r[key] / total * 100, 2)
    return clean


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------

def build_budget(investment: float, allocation=None):
    """Turns a percentage allocation into concrete rupee amounts.

    Returns {'total', 'items': [{category, percent, amount, note}], 'largest'}
    """
    investment = _f(investment)
    alloc = normalize_percentages(allocation) or [dict(x) for x in DEFAULT_BUDGET_SPLIT]
    alloc = normalize_percentages(alloc)

    items = []
    for row in alloc:
        amount = round(investment * row["percent"] / 100.0, 2)
        items.append({
            "category": str(row.get("category", "Other"))[:60],
            "percent": row["percent"],
            "amount": amount,
            "note": str(row.get("note", "") or "")[:220],
        })

    items.sort(key=lambda x: x["amount"], reverse=True)
    return {
        "total": round(investment, 2),
        "items": items,
        "largest": items[0]["category"] if items else None,
        "contingency": next(
            (i["amount"] for i in items if "conting" in i["category"].lower() or "buffer" in i["category"].lower()),
            0.0,
        ),
    }


# --------------------------------------------------------------------------
# Multi-year P&L projection
# --------------------------------------------------------------------------

def build_projection(investment, expected_revenue, operating_cost,
                     revenue_growth_percent=20.0, cost_growth_percent=10.0,
                     years=3, ramp_months=6):
    """Year-by-year revenue / cost / profit / cumulative cashflow.

    Year 1 revenue is discounted by the ramp: a product that takes `ramp_months`
    to launch only earns for the remaining part of year one.
    """
    investment = _f(investment)
    revenue = _f(expected_revenue)
    opex = _f(operating_cost)
    g_rev = _f(revenue_growth_percent, 20.0) / 100.0
    g_cost = _f(cost_growth_percent, 10.0) / 100.0
    years = max(1, min(7, int(years or 3)))
    ramp_months = max(0, min(24, int(ramp_months or 0)))

    # Fraction of year 1 that actually earns revenue
    earning_fraction = max(0.15, min(1.0, (12 - min(ramp_months, 11)) / 12.0))

    rows = []
    cumulative = -investment
    for y in range(1, years + 1):
        year_rev = revenue * ((1 + g_rev) ** (y - 1))
        year_cost = opex * ((1 + g_cost) ** (y - 1))
        if y == 1:
            year_rev *= earning_fraction
        capex = investment if y == 1 else 0.0
        profit = year_rev - year_cost - capex
        cumulative += year_rev - year_cost
        rows.append({
            "year": f"Year {y}",
            "revenue": round(year_rev, 2),
            "operating_cost": round(year_cost, 2),
            "capex": round(capex, 2),
            "profit": round(profit, 2),
            "net_contribution": round(year_rev - year_cost, 2),
            "cumulative_cashflow": round(cumulative, 2),
            "margin_percent": round((profit / year_rev * 100) if year_rev > 0 else 0.0, 2),
        })

    payback_year = next((r["year"] for r in rows if r["cumulative_cashflow"] >= 0), None)

    total_rev = sum(r["revenue"] for r in rows)
    total_profit = sum(r["profit"] for r in rows)

    return {
        "rows": rows,
        "years": years,
        "payback_year": payback_year,
        "total_revenue": round(total_rev, 2),
        "total_profit": round(total_profit, 2),
        "cagr_percent": round(g_rev * 100, 2),
        "earning_fraction_year_one": round(earning_fraction, 2),
    }


def monthly_cashflow(investment, expected_revenue, operating_cost,
                     ramp_months=6, horizon_months=24):
    """Month-by-month cash position using an S-curve revenue ramp.

    Returns the series a break-even chart needs, plus the break-even month.
    """
    investment = _f(investment)
    monthly_rev_full = _f(expected_revenue) / 12.0
    monthly_cost = _f(operating_cost) / 12.0
    ramp_months = max(1, int(ramp_months or 6))
    horizon = max(12, min(60, int(horizon_months or 24)))

    labels, revenue, cost, net, cumulative = [], [], [], [], []
    running = -investment
    breakeven_month = None

    for m in range(1, horizon + 1):
        # Logistic ramp: ~50% of run-rate at ramp_months, ~95% at 2x ramp
        progress = 1.0 / (1.0 + math.exp(-(m - ramp_months) / max(1.0, ramp_months / 3.0)))
        r = monthly_rev_full * progress
        c = monthly_cost * (0.55 + 0.45 * progress)  # fixed costs start before revenue
        running += r - c

        labels.append(f"M{m}")
        revenue.append(round(r, 2))
        cost.append(round(c, 2))
        net.append(round(r - c, 2))
        cumulative.append(round(running, 2))

        if breakeven_month is None and running >= 0:
            breakeven_month = m

    trough = min(cumulative) if cumulative else 0.0

    return {
        "labels": labels,
        "revenue": revenue,
        "cost": cost,
        "net": net,
        "cumulative": cumulative,
        "breakeven_month": breakeven_month,
        "peak_funding_need": round(abs(trough), 2) if trough < 0 else 0.0,
        "horizon_months": horizon,
    }


def scenario_bands(expected_revenue, operating_cost, investment,
                   optimistic_multiplier=1.25, pessimistic_multiplier=0.7,
                   revenue_growth_percent=20.0, cost_growth_percent=10.0,
                   years=3, ramp_months=6):
    """Best / base / worst case three-year outcomes."""
    opt = max(1.0, _f(optimistic_multiplier, 1.25))
    pess = min(0.99, max(0.2, _f(pessimistic_multiplier, 0.7)))

    def run(rev_mult, cost_mult, g_adjust):
        return build_projection(
            investment, _f(expected_revenue) * rev_mult, _f(operating_cost) * cost_mult,
            revenue_growth_percent=_f(revenue_growth_percent, 20.0) + g_adjust,
            cost_growth_percent=cost_growth_percent, years=years, ramp_months=ramp_months,
        )

    best = run(opt, 0.95, 8)
    base = run(1.0, 1.0, 0)
    worst = run(pess, 1.15, -8)

    return {
        "best": {"label": "Best case", "total_profit": best["total_profit"],
                 "total_revenue": best["total_revenue"], "payback_year": best["payback_year"],
                 "rows": best["rows"]},
        "base": {"label": "Base case", "total_profit": base["total_profit"],
                 "total_revenue": base["total_revenue"], "payback_year": base["payback_year"],
                 "rows": base["rows"]},
        "worst": {"label": "Worst case", "total_profit": worst["total_profit"],
                  "total_revenue": worst["total_revenue"], "payback_year": worst["payback_year"],
                  "rows": worst["rows"]},
    }


def profit_bridge(investment, expected_revenue, operating_cost):
    """Waterfall steps from revenue down to net profit."""
    revenue = _f(expected_revenue)
    opex = _f(operating_cost)
    capex = _f(investment)
    return [
        {"label": "Revenue", "value": round(revenue, 2), "type": "positive"},
        {"label": "Operating Cost", "value": round(-opex, 2), "type": "negative"},
        {"label": "Investment", "value": round(-capex, 2), "type": "negative"},
        {"label": "Net Profit", "value": round(revenue - opex - capex, 2), "type": "total"},
    ]


# --------------------------------------------------------------------------
# Marketing / growth
# --------------------------------------------------------------------------

def customer_growth_curve(expected_customers, ramp_months=6, horizon_months=24,
                          year_growth_percent=None):
    """S-curve customer adoption, then compounding growth after the ramp."""
    target = max(0.0, _f(expected_customers))
    ramp_months = max(1, int(ramp_months or 6))
    horizon = max(12, min(60, int(horizon_months or 24)))
    yearly_growth = _f(year_growth_percent, 30.0) / 100.0

    labels, customers, new_customers = [], [], []
    prev = 0.0
    for m in range(1, horizon + 1):
        s = 1.0 / (1.0 + math.exp(-(m - ramp_months) / max(1.0, ramp_months / 3.0)))
        base = target * s
        if m > ramp_months * 2:
            extra_years = (m - ramp_months * 2) / 12.0
            base = target * ((1 + yearly_growth) ** extra_years)
        labels.append(f"M{m}")
        customers.append(round(base, 1))
        new_customers.append(round(max(0.0, base - prev), 1))
        prev = base

    return {
        "labels": labels, "customers": customers, "new_customers": new_customers,
        "final": customers[-1] if customers else 0,
        "month_12": customers[11] if len(customers) > 11 else (customers[-1] if customers else 0),
    }


def build_funnel(stages, top_of_funnel=None, expected_customers=0):
    """Turns [{stage, conversion_percent}] into absolute volumes.

    If no top-of-funnel size is given, it is back-solved from the customer
    target so the funnel actually lands on the number the user entered.
    """
    stages = [s for s in (stages or []) if isinstance(s, dict) and s.get("stage")]
    if not stages:
        stages = [
            {"stage": "Reached", "conversion_percent": 100},
            {"stage": "Engaged", "conversion_percent": 25},
            {"stage": "Qualified Lead", "conversion_percent": 30},
            {"stage": "Demo / Trial", "conversion_percent": 40},
            {"stage": "Customer", "conversion_percent": 30},
        ]

    convs = []
    for s in stages:
        c = _f(s.get("conversion_percent"), 100.0)
        convs.append(max(1.0, min(100.0, c)))

    cumulative = 1.0
    factors = []
    for c in convs:
        cumulative *= c / 100.0
        factors.append(cumulative)

    if top_of_funnel:
        top = _f(top_of_funnel)
    else:
        final_factor = factors[-1] if factors else 1.0
        top = (_f(expected_customers) / final_factor) if final_factor > 0 else _f(expected_customers)
        top = max(top, _f(expected_customers))

    rows = []
    for s, c, f in zip(stages, convs, factors):
        rows.append({
            "stage": str(s.get("stage"))[:40],
            "conversion_percent": round(c, 1),
            "volume": int(round(top * f)),
        })
    return {"rows": rows, "top_of_funnel": int(round(top))}


def channel_plan(channels, marketing_budget, expected_customers=0):
    """Allocates the marketing budget across channels and derives CAC / customers."""
    chans = normalize_percentages(channels, key="budget_share_percent")
    if not chans:
        chans = normalize_percentages([
            {"name": "Direct / Field Sales", "budget_share_percent": 30, "expected_cac": 0},
            {"name": "Digital Ads", "budget_share_percent": 25, "expected_cac": 0},
            {"name": "Content & SEO", "budget_share_percent": 20, "expected_cac": 0},
            {"name": "Partnerships", "budget_share_percent": 15, "expected_cac": 0},
            {"name": "Events & Community", "budget_share_percent": 10, "expected_cac": 0},
        ], key="budget_share_percent")

    budget = _f(marketing_budget)
    fallback_cac = (budget / _f(expected_customers)) if _f(expected_customers) > 0 else 0.0

    rows = []
    for c in chans:
        share = c["budget_share_percent"]
        spend = round(budget * share / 100.0, 2)
        cac = _f(c.get("expected_cac")) or fallback_cac
        acquired = int(spend / cac) if cac > 0 else 0
        rows.append({
            "name": str(c.get("name", "Channel"))[:40],
            "budget_share_percent": share,
            "spend": spend,
            "cac": round(cac, 2),
            "customers": acquired,
            "conversion_percent": round(_f(c.get("expected_conversion_percent"), 0), 2),
            "note": str(c.get("note", "") or "")[:200],
        })

    rows.sort(key=lambda r: r["spend"], reverse=True)
    total_customers = sum(r["customers"] for r in rows)
    blended_cac = round(budget / total_customers, 2) if total_customers else 0.0
    return {"rows": rows, "budget": budget, "total_customers": total_customers,
            "blended_cac": blended_cac}


def unit_economics(expected_revenue, expected_customers, marketing_budget,
                   operating_cost, retention_years=3.0):
    """ARPU, CAC, LTV, LTV:CAC and payback in months."""
    customers = _f(expected_customers)
    revenue = _f(expected_revenue)
    arpu = revenue / customers if customers > 0 else 0.0
    cac = _f(marketing_budget) / customers if customers > 0 else 0.0
    gross_margin = 1 - (_f(operating_cost) / revenue) if revenue > 0 else 0.6
    gross_margin = max(0.05, min(0.95, gross_margin))
    ltv = arpu * gross_margin * _f(retention_years, 3.0)
    ratio = (ltv / cac) if cac > 0 else 0.0
    payback_months = (cac / (arpu * gross_margin / 12)) if arpu > 0 and gross_margin > 0 else 0.0

    return {
        "arpu": round(arpu, 2),
        "cac": round(cac, 2),
        "ltv": round(ltv, 2),
        "ltv_cac_ratio": round(ratio, 2),
        "gross_margin_percent": round(gross_margin * 100, 1),
        "payback_months": round(payback_months, 1),
        "healthy": ratio >= 3.0,
    }


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------

def build_roadmap(phases, total_months=6):
    """Normalizes agent-supplied phases into a Gantt-ready series."""
    total_months = max(1, int(total_months or 6))
    clean = []
    for p in phases or []:
        if not isinstance(p, dict) or not p.get("phase"):
            continue
        start = max(0, int(_f(p.get("start_month"), 0)))
        dur = max(1, int(_f(p.get("duration_months"), 1)))
        clean.append({
            "phase": str(p.get("phase"))[:60],
            "start_month": start,
            "duration_months": dur,
            "end_month": start + dur,
            "owner": str(p.get("owner", "Unassigned") or "Unassigned")[:40],
            "deliverables": [str(d)[:160] for d in (p.get("deliverables") or [])][:6],
            "risk_level": str(p.get("risk_level", "MEDIUM") or "MEDIUM").upper(),
        })

    if not clean:
        step = max(1, total_months // 4)
        clean = [
            {"phase": "Discovery & Design", "start_month": 0, "duration_months": step,
             "end_month": step, "owner": "Product", "deliverables": [], "risk_level": "LOW"},
            {"phase": "Build", "start_month": step, "duration_months": step * 2,
             "end_month": step * 3, "owner": "Engineering", "deliverables": [], "risk_level": "HIGH"},
            {"phase": "Pilot & QA", "start_month": step * 3, "duration_months": step,
             "end_month": step * 4, "owner": "QA", "deliverables": [], "risk_level": "MEDIUM"},
            {"phase": "Launch & Scale", "start_month": step * 4, "duration_months": step,
             "end_month": step * 5, "owner": "GTM", "deliverables": [], "risk_level": "MEDIUM"},
        ]

    clean.sort(key=lambda p: (p["start_month"], p["end_month"]))
    span = max([p["end_month"] for p in clean] + [total_months])
    return {"phases": clean, "span_months": span,
            "critical_path": [p["phase"] for p in clean if p["risk_level"] in ("HIGH", "CRITICAL")]}


def resource_costs(resources, months=6):
    """Turns [{role, headcount, monthly_cost}] into total staffing cost."""
    months = max(1, int(months or 6))
    rows = []
    for r in resources or []:
        if not isinstance(r, dict) or not r.get("role"):
            continue
        head = max(0.0, _f(r.get("headcount"), 1))
        monthly = max(0.0, _f(r.get("monthly_cost")))
        rows.append({
            "role": str(r.get("role"))[:50],
            "headcount": round(head, 1),
            "monthly_cost": round(monthly, 2),
            "total_cost": round(monthly * head * months, 2),
            "note": str(r.get("note", "") or "")[:180],
        })
    rows.sort(key=lambda r: r["total_cost"], reverse=True)
    return {
        "rows": rows,
        "months": months,
        "total_headcount": round(sum(r["headcount"] for r in rows), 1),
        "total_cost": round(sum(r["total_cost"] for r in rows), 2),
    }


# --------------------------------------------------------------------------
# Risk
# --------------------------------------------------------------------------

SEVERITY_WEIGHT = {"LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 95}


def risk_matrix(risks, investment=0.0):
    """Builds probability x impact bubble data + category and severity rollups."""
    points, categories, severities = [], {}, {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    total_exposure = 0.0

    for r in risks or []:
        if not isinstance(r, dict):
            continue
        sev = str(r.get("severity", "MEDIUM") or "MEDIUM").upper()
        if sev not in severities:
            sev = "MEDIUM"
        prob = _f(r.get("probability_percent"), SEVERITY_WEIGHT[sev] * 0.8)
        impact = _f(r.get("impact_percent"), SEVERITY_WEIGHT[sev])
        prob = max(1.0, min(100.0, prob))
        impact = max(1.0, min(100.0, impact))
        exposure_pct = _f(r.get("financial_exposure_percent"), impact / 4.0)
        exposure = _f(investment) * max(0.0, min(100.0, exposure_pct)) / 100.0
        total_exposure += exposure

        cat = str(r.get("category", "General") or "General")[:30]
        categories[cat] = categories.get(cat, 0) + 1
        severities[sev] += 1

        points.append({
            "risk": str(r.get("risk", "Unnamed risk"))[:180],
            "category": cat,
            "severity": sev,
            "probability": round(prob, 1),
            "impact": round(impact, 1),
            "exposure": round(exposure, 2),
            "score": round(prob * impact / 100.0, 1),
            "mitigation": [str(m)[:200] for m in (r.get("mitigation") or [])][:5],
        })

    points.sort(key=lambda p: p["score"], reverse=True)
    return {
        "points": points,
        "categories": categories,
        "severities": severities,
        "total_exposure": round(total_exposure, 2),
        "top_risks": points[:5],
        "average_score": round(sum(p["score"] for p in points) / len(points), 1) if points else 0.0,
    }


# --------------------------------------------------------------------------
# Portfolio analytics (across all of a user's decisions)
# --------------------------------------------------------------------------

def portfolio_analytics(scenarios):
    """Aggregates every completed scenario into dashboard-ready series."""
    labels, scores, investments, revenues, profits, dates = [], [], [], [], [], []
    recommendations = {}
    agent_totals = {"finance": [], "marketing": [], "operations": [], "risk": [], "strategic_fit": []}

    for s in scenarios:
        if not s.decision:
            continue
        labels.append((s.title or "Untitled")[:28])
        scores.append(round(_f(s.decision.weighted_score), 1))
        investments.append(round(_f(s.investment), 2))
        revenues.append(round(_f(s.expected_revenue), 2))
        profits.append(round(_f(s.expected_revenue) - _f(s.investment) - _f(s.operating_cost), 2))
        dates.append(s.created_at.strftime("%d %b") if s.created_at else "")

        rec = s.decision.final_recommendation or "UNKNOWN"
        recommendations[rec] = recommendations.get(rec, 0) + 1

        report = s.decision.report_data() or {}
        for key, val in (report.get("agent_scores") or {}).items():
            if key in agent_totals and val is not None:
                agent_totals[key].append(_f(val))

    avg_agent_scores = {
        k: round(sum(v) / len(v), 1) if v else 0.0 for k, v in agent_totals.items()
    }

    return {
        "labels": labels,
        "scores": scores,
        "investments": investments,
        "revenues": revenues,
        "profits": profits,
        "dates": dates,
        "recommendations": recommendations,
        "avg_agent_scores": avg_agent_scores,
        "count": len(labels),
        "total_investment": round(sum(investments), 2),
        "total_revenue": round(sum(revenues), 2),
        "approved": sum(v for k, v in recommendations.items() if "RECOMMEND" in k),
    }
