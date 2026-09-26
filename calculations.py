"""
Deterministic numerical calculations. The LLM never does arithmetic —
it only interprets numbers that Python has already computed here.
"""


def compute_financials(investment: float, expected_revenue: float, operating_cost: float):
    investment = float(investment or 0)
    expected_revenue = float(expected_revenue or 0)
    operating_cost = float(operating_cost or 0)

    total_cost = investment + operating_cost
    profit = expected_revenue - total_cost
    roi = (profit / investment * 100) if investment > 0 else 0.0

    # Break-even in "years" of the revenue run-rate needed to recover investment,
    # using annual net contribution (revenue - operating_cost) as the payback rate.
    annual_net = expected_revenue - operating_cost
    if annual_net > 0:
        breakeven_years = round(investment / annual_net, 2)
    else:
        breakeven_years = None  # never breaks even at this run-rate

    margin_pct = (profit / expected_revenue * 100) if expected_revenue > 0 else 0.0

    return {
        "investment": round(investment, 2),
        "expected_revenue": round(expected_revenue, 2),
        "operating_cost": round(operating_cost, 2),
        "total_cost": round(total_cost, 2),
        "profit": round(profit, 2),
        "roi_percent": round(roi, 2),
        "profit_margin_percent": round(margin_pct, 2),
        "breakeven_years": breakeven_years,
    }


def financial_score_from_metrics(metrics: dict) -> float:
    """A deterministic 0-100 score derived purely from the numbers, used as a
    floor/sanity-check alongside the LLM's qualitative score."""
    roi = metrics.get("roi_percent", 0)
    margin = metrics.get("profit_margin_percent", 0)
    breakeven = metrics.get("breakeven_years")

    score = 50.0
    score += max(-30, min(30, roi / 4))       # ROI contributes up to +/-30
    score += max(-15, min(15, margin / 4))    # margin contributes up to +/-15

    if breakeven is None:
        score -= 15
    elif breakeven <= 1:
        score += 10
    elif breakeven > 3:
        score -= 10

    return round(max(0, min(100, score)), 2)
