"""
What-if analysis. Numbers are recomputed deterministically in Python from the
base scenario's finance metrics and the *existing* agent scores/weights — we
do not re-run the full multi-agent workflow for every what-if tweak (that
would be slow and costly); instead we recompute the financial metrics and
re-blend the weighted score, then use Gemini once for a short qualitative
interpretation of what changed and why.
"""
from services.calculations import compute_financials, financial_score_from_metrics
from services.scoring import compute_weighted_score, decision_label, risk_level_to_score


def run_what_if(scenario, decision, risk_result: dict, strategic_fit_score: float,
                 marketing_score: float, operations_score: float, weights: dict,
                 new_investment=None, new_revenue=None, new_operating_cost=None,
                 scenario_name: str = None):
    """Returns a comprehensive dict comparing the base case to the what-if case,
    including the strategic score, recommendation verdict, qualitative narrative,
    key opportunities, risks, and action steps."""
    base_metrics = compute_financials(scenario.investment, scenario.expected_revenue,
                                       scenario.operating_cost)
    base_finance_score = financial_score_from_metrics(base_metrics)

    investment = float(new_investment if new_investment is not None else (scenario.investment or 0))
    revenue = float(new_revenue if new_revenue is not None else (scenario.expected_revenue or 0))
    operating_cost = float(new_operating_cost if new_operating_cost is not None else (scenario.operating_cost or 0))

    whatif_metrics = compute_financials(investment, revenue, operating_cost)
    whatif_finance_score = financial_score_from_metrics(whatif_metrics)

    # Dynamic risk adjustment based on bottom-line financial health
    base_risk_level = risk_result.get("overall_risk_level", "MEDIUM") if risk_result else "MEDIUM"
    risk_score = risk_level_to_score(base_risk_level)
    if whatif_metrics["profit"] < 0:
        risk_score = max(15.0, risk_score - 25.0)
    elif whatif_metrics["profit"] < base_metrics["profit"]:
        risk_score = max(25.0, risk_score - 10.0)
    elif whatif_metrics["profit"] > base_metrics["profit"] * 1.25:
        risk_score = min(95.0, risk_score + 10.0)

    base_score = float(decision.weighted_score if decision else 50.0)
    whatif_score = compute_weighted_score(
        finance_score=whatif_finance_score,
        marketing_score=marketing_score,
        operations_score=operations_score,
        risk_score=risk_score,
        strategic_fit_score=strategic_fit_score,
        weights=weights,
    )

    base_rec = decision_label(base_score)
    whatif_rec = decision_label(whatif_score)

    name = scenario_name.strip() if scenario_name and scenario_name.strip() else "Custom Simulation"
    profit_diff = whatif_metrics["profit"] - base_metrics["profit"]
    score_diff = round(whatif_score - base_score, 2)
    roi_diff = round(whatif_metrics["roi_percent"] - base_metrics["roi_percent"], 2)
    margin_diff = round(whatif_metrics["profit_margin_percent"] - base_metrics["profit_margin_percent"], 2)

    # Factors
    factors = []
    if roi_diff != 0:
        factors.append(f"ROI shifts from {base_metrics['roi_percent']}% to {whatif_metrics['roi_percent']}% ({roi_diff:+0.1f}%)")
    if profit_diff != 0:
        factors.append(f"Net profit shifts from Rs. {base_metrics['profit']:,.0f} to Rs. {whatif_metrics['profit']:,.0f} ({profit_diff:+,.0f})")
    if whatif_metrics["breakeven_years"] != base_metrics["breakeven_years"]:
        factors.append(f"Break-even shifts from {base_metrics['breakeven_years'] or 'None'} to {whatif_metrics['breakeven_years'] or 'None'} years")
    if margin_diff != 0:
        factors.append(f"Profit margin shifts from {base_metrics['profit_margin_percent']}% to {whatif_metrics['profit_margin_percent']}%")

    # Boardroom Recommendation Verdict Narrative
    badge_class = (
        "badge-strong" if whatif_rec == "STRONGLY RECOMMEND"
        else "badge-conditions" if "CONDITIONS" in whatif_rec
        else "badge-review" if "REVIEW" in whatif_rec
        else "badge-reject"
    )

    if whatif_score >= 75:
        verdict = (
            f"Under this scenario ('{name}'), the business case shows superior capital efficiency with an expected "
            f"net profit of ₹{whatif_metrics['profit']:,.0f} and {whatif_metrics['roi_percent']}% ROI. "
            f"The Boardroom strongly recommends rapid resource deployment to capture the upside."
        )
    elif whatif_score >= 60:
        verdict = (
            f"Under this scenario ('{name}'), the project maintains positive unit economics (₹{whatif_metrics['profit']:,.0f} net profit). "
            f"The Boardroom recommends proceeding conditionally, prioritizing milestone-based capital tranches and strict monthly cost tracking."
        )
    elif whatif_score >= 45:
        verdict = (
            f"Under this scenario ('{name}'), profit margins and capital recovery are noticeably strained (Strategic score: {whatif_score}/100). "
            f"The Boardroom advises reviewing pricing, renegotiating vendor contracts, or deferring non-essential expansion."
        )
    else:
        verdict = (
            f"Under this scenario ('{name}'), the venture faces severe capital erosion with a projected net loss of ₹{abs(whatif_metrics['profit']):,.0f}. "
            f"The Boardroom advises against proceeding without structural revisions to the business model."
        )

    # Key Opportunities
    opportunities = []
    if whatif_metrics["profit"] > base_metrics["profit"]:
        opportunities.append(f"Higher bottom-line returns: Net profit increases by ₹{profit_diff:,.0f}.")
    if whatif_metrics["roi_percent"] > base_metrics["roi_percent"]:
        opportunities.append(f"Enhanced capital efficiency: ROI expands from {base_metrics['roi_percent']}% to {whatif_metrics['roi_percent']}%.")
    if margin_diff > 0:
        opportunities.append(f"Expanded margin buffer: Profit margin widens by {margin_diff:+0.1f}%.")
    if whatif_score > base_score:
        opportunities.append(f"Stronger board alignment: Strategic confidence index increases by {score_diff:+0.1f} points.")
    if not opportunities:
        opportunities.append("Provides a valuable stress-test baseline to identify minimum sustainable revenue targets.")
        opportunities.append("Incentivizes lean cost management and disciplined supplier negotiations.")

    # Key Risks & Vulnerabilities
    risks = []
    if whatif_metrics["profit"] < 0:
        risks.append(f"Cash flow deficit: Projected operating burn of ₹{abs(whatif_metrics['profit']):,.0f}.")
    elif profit_diff < 0:
        risks.append(f"Profit erosion: Returns drop by ₹{abs(profit_diff):,.0f} compared to the original baseline.")
    if whatif_metrics["breakeven_years"] is None:
        risks.append("Capital recovery failure: No break-even point is reached within the operating horizon.")
    elif base_metrics["breakeven_years"] and whatif_metrics["breakeven_years"] > base_metrics["breakeven_years"]:
        risks.append(f"Extended payback: Break-even widens to {whatif_metrics['breakeven_years']} years (baseline: {base_metrics['breakeven_years']} yrs).")
    if whatif_metrics["investment"] > base_metrics["investment"]:
        risks.append(f"Increased capital commitment: Requires ₹{whatif_metrics['investment'] - base_metrics['investment']:,.0f} additional investment.")
    if not risks:
        risks.append("Execution speed and competitor price aggression remain key watchpoints.")

    # Recommended Boardroom Actions
    actions = []
    if whatif_score >= 70:
        actions.append("Scale marketing and distribution channels aggressively to capture early market share.")
        actions.append("Lock in supplier volume commitments early to protect healthy profit margins.")
        actions.append("Implement monthly KPI dashboards tracking customer acquisition cost and net retention.")
    elif whatif_score >= 55:
        actions.append("Release investment capital in phased tranches tied to verified monthly revenue milestones.")
        actions.append("Establish a 10% contingency reserve to absorb unexpected operating cost fluctuations.")
        actions.append("Focus acquisition efforts on high-margin customer cohorts.")
    else:
        actions.append("Freeze capital commitment until unit economics or cost parameters are renegotiated.")
        actions.append("Explore lean MVP or partnership distribution to reduce upfront capital requirements.")
        actions.append("Pivot pricing tiers or value proposition to restore positive gross margins.")

    return {
        "scenario_name": name,
        "base_case": {
            "investment": base_metrics["investment"],
            "revenue": base_metrics["expected_revenue"],
            "operating_cost": base_metrics["operating_cost"],
            "profit": base_metrics["profit"],
            "roi_percent": base_metrics["roi_percent"],
            "profit_margin_percent": base_metrics["profit_margin_percent"],
            "breakeven_years": base_metrics["breakeven_years"],
            "score": base_score,
            "decision": base_rec,
        },
        "what_if_case": {
            "investment": whatif_metrics["investment"],
            "revenue": whatif_metrics["expected_revenue"],
            "operating_cost": whatif_metrics["operating_cost"],
            "profit": whatif_metrics["profit"],
            "roi_percent": whatif_metrics["roi_percent"],
            "profit_margin_percent": whatif_metrics["profit_margin_percent"],
            "breakeven_years": whatif_metrics["breakeven_years"],
            "score": whatif_score,
            "decision": whatif_rec,
        },
        "score_change": score_diff,
        "profit_change": round(profit_diff, 2),
        "roi_change": roi_diff,
        "margin_change": margin_diff,
        "decision_changed": whatif_rec != base_rec,
        "main_factors": factors,
        "badge_class": badge_class,
        "verdict_narrative": verdict,
        "opportunities": opportunities,
        "risks": risks,
        "recommended_actions": actions,
    }

