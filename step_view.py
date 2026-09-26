"""
Builds the crisp, single-screen content for each step-wizard agent page
(templates/agent_step.html): four headline KPI tiles, a couple of short
bullet sections, and a one-line conclusion. Anything that ends up as a
number is computed here in Python from the scenario + the agent's own
(already-validated) structured output — never left to Jinja arithmetic.
"""
from services.calculations import compute_financials
from services.formatting import inr_short


def _pct(value, default=0):
    try:
        return round(float(value if value is not None else default), 1)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- Finance --
def finance_step_context(scenario, result: dict):
    metrics = compute_financials(scenario.investment, scenario.expected_revenue,
                                 scenario.operating_cost)
    kpis = [
        {"icon": "📈", "label": "Estimated Revenue", "value": f"₹{inr_short(metrics['expected_revenue'])}", "tone": "sky"},
        {"icon": "🧾", "label": "Estimated Cost", "value": f"₹{inr_short(metrics['total_cost'])}", "tone": "coral"},
        {"icon": "💰", "label": "Projected Profit", "value": f"₹{inr_short(metrics['profit'])}",
         "tone": "mint" if metrics["profit"] >= 0 else "coral"},
        {"icon": "🎯", "label": "Expected ROI", "value": f"{metrics['roi_percent']:.0f}%", "tone": "lilac"},
    ]
    sections = [
        {"icon": "✅", "label": "Recommendations", "tone": "mint",
         "items": (result.get("funding_recommendations") or result.get("profit_drivers") or [])[:5]
                 or ["Proceed with a phased rollout to control cash burn."]},
        {"icon": "💡", "label": "Key Insights", "tone": "sky",
         "items": (result.get("key_findings") or [])[:5] or ["No additional findings were returned."]},
        {"icon": "⚠️", "label": "Financial Risks", "tone": "coral",
         "items": (result.get("loss_drivers") or result.get("risks") or [])[:5]
                 or ["No specific financial risks were flagged."]},
    ]
    return {
        "icon": "💰", "title": "Financial Analysis", "agent_label": "Finance Agent",
        "tagline": "Evaluating the financial viability and profitability of the decision.",
        "kpis": kpis, "sections": sections,
        "conclusion_label": "Finance Agent's Conclusion",
        "conclusion_text": result.get("reasoning") or "Financial analysis complete.",
        "conclusion_good": metrics["profit"] >= 0 and (result.get("score") or 0) >= 50,
    }


# --------------------------------------------------------------- Marketing -
def marketing_step_context(scenario, result: dict):
    growth = _pct(result.get("year_one_growth_percent"), 30)
    budget_share = _pct(result.get("marketing_budget_share_percent"), 20)
    channels = result.get("channels") or []
    top_channel = max(channels, key=lambda c: c.get("budget_share_percent", 0))["name"] if channels else "—"
    customers = int(scenario.expected_customers or 0)

    kpis = [
        {"icon": "📈", "label": "Year 1 Growth Target", "value": f"{growth:.0f}%", "tone": "sky"},
        {"icon": "🎯", "label": "Target Customers", "value": f"{customers:,}" if customers else "—", "tone": "lilac"},
        {"icon": "📣", "label": "Top Channel", "value": top_channel, "tone": "mint"},
        {"icon": "💸", "label": "Marketing Budget Share", "value": f"{budget_share:.0f}%", "tone": "coral"},
    ]
    sections = [
        {"icon": "✅", "label": "Recommendations", "tone": "mint",
         "items": (result.get("growth_levers") or [])[:5]
                 or ["Start with the highest-converting channel and scale gradually."]},
        {"icon": "💡", "label": "Key Insights", "tone": "sky",
         "items": (result.get("key_findings") or result.get("opportunities") or [])[:5]
                 or ["No additional findings were returned."]},
        {"icon": "⚠️", "label": "Marketing Risks", "tone": "coral",
         "items": (result.get("risks") or [])[:5] or ["No specific marketing risks were flagged."]},
    ]
    return {
        "icon": "📣", "title": "Marketing Strategy", "agent_label": "Marketing Agent",
        "tagline": "Assessing positioning, channels and growth potential.",
        "kpis": kpis, "sections": sections,
        "conclusion_label": "Marketing Agent's Conclusion",
        "conclusion_text": result.get("reasoning") or result.get("positioning_statement")
                          or "Marketing analysis complete.",
        "conclusion_good": (result.get("score") or 0) >= 50,
    }


# -------------------------------------------------------------- Operations -
def operations_step_context(scenario, result: dict):
    timeline = _pct(result.get("recommended_timeline_months"), 6)
    resource_plan = result.get("resource_plan") or []
    headcount = sum(_pct(r.get("headcount"), 0) for r in resource_plan)
    monthly_cost = sum(_pct(r.get("monthly_cost"), 0) for r in resource_plan)
    readiness_rows = result.get("readiness") or []
    readiness_avg = (sum(_pct(r.get("score"), 0) for r in readiness_rows) / len(readiness_rows)
                     if readiness_rows else _pct(result.get("score"), 0))

    kpis = [
        {"icon": "🗓️", "label": "Recommended Timeline", "value": f"{timeline:.0f} mo", "tone": "sky"},
        {"icon": "👥", "label": "Team Size", "value": f"{headcount:.0f}" if headcount else "—", "tone": "lilac"},
        {"icon": "🧾", "label": "Monthly Run Cost", "value": f"₹{inr_short(monthly_cost)}" if monthly_cost else "—", "tone": "coral"},
        {"icon": "✅", "label": "Readiness", "value": f"{readiness_avg:.0f}/100", "tone": "mint"},
    ]
    sections = [
        {"icon": "✅", "label": "Recommendations", "tone": "mint",
         "items": (result.get("resource_requirements") or [])[:5]
                 or ["Staff the core team first, then scale support functions."]},
        {"icon": "💡", "label": "Key Insights", "tone": "sky",
         "items": (result.get("key_findings") or [])[:5] or ["No additional findings were returned."]},
        {"icon": "⚠️", "label": "Operational Risks", "tone": "coral",
         "items": (result.get("bottlenecks") or result.get("risks") or [])[:5]
                 or ["No specific operational bottlenecks were flagged."]},
    ]
    return {
        "icon": "⚙️", "title": "Operations Plan", "agent_label": "Operations Agent",
        "tagline": "Checking delivery timeline, resourcing and readiness.",
        "kpis": kpis, "sections": sections,
        "conclusion_label": "Operations Agent's Conclusion",
        "conclusion_text": result.get("reasoning") or "Operations analysis complete.",
        "conclusion_good": (result.get("score") or 0) >= 50,
    }


# -------------------------------------------------------------------- Risk -
def risk_step_context(scenario, result: dict):
    risks = result.get("risks") or []
    overall = (result.get("overall_risk_level") or "MEDIUM").title()
    contingency = _pct(result.get("contingency_percent_recommended"), 10)
    top_exposure = max((_pct(r.get("financial_exposure_percent"), 0) for r in risks), default=0)

    kpis = [
        {"icon": "🚦", "label": "Overall Risk Level", "value": overall,
         "tone": {"Low": "mint", "Medium": "sky", "High": "coral", "Critical": "coral"}.get(overall, "sky")},
        {"icon": "📋", "label": "Risks Identified", "value": str(len(risks)), "tone": "lilac"},
        {"icon": "💥", "label": "Top Exposure", "value": f"{top_exposure:.0f}% of budget", "tone": "coral"},
        {"icon": "🛟", "label": "Contingency Recommended", "value": f"{contingency:.0f}%", "tone": "mint"},
    ]
    mitigations = []
    for r in risks[:5]:
        mitigations.extend((r.get("mitigation") or [])[:1])
    top_risks = [f"{r.get('risk', 'Risk')} ({(r.get('severity') or 'MEDIUM').title()})" for r in risks[:5]]

    sections = [
        {"icon": "✅", "label": "Mitigations", "tone": "mint",
         "items": mitigations[:5] or ["No specific mitigations were returned."]},
        {"icon": "💡", "label": "Deal-Breakers to Watch", "tone": "sky",
         "items": (result.get("deal_breakers") or [])[:5] or ["No deal-breaking risks were flagged."]},
        {"icon": "⚠️", "label": "Top Risks", "tone": "coral",
         "items": top_risks or ["No specific risks were flagged."]},
    ]
    return {
        "icon": "⚠️", "title": "Risk Assessment", "agent_label": "Risk Agent",
        "tagline": "Weighing what could go wrong against the upside.",
        "kpis": kpis, "sections": sections,
        "conclusion_label": "Risk Agent's Conclusion",
        "conclusion_text": result.get("reasoning") or "Risk assessment complete.",
        "conclusion_good": overall in ("Low", "Medium"),
    }


# --------------------------------------------------------------------- CEO -
def ceo_step_context(scenario, decision, ceo: dict):
    budget_pct = _pct(ceo.get("approved_budget_percent"), 100)
    should = (ceo.get("should_proceed") or "").strip().lower()
    proceed_label = {"yes": "Proceed", "no": "Do Not Proceed"}.get(should, "Proceed with Conditions")

    kpis = [
        {"icon": "🏆", "label": "Weighted Score", "value": f"{_pct(decision.weighted_score, 0):.0f}/100", "tone": "lilac"},
        {"icon": "🚦", "label": "CEO Verdict", "value": proceed_label,
         "tone": {"yes": "mint", "no": "coral"}.get(should, "sky")},
        {"icon": "💵", "label": "Budget Approved For Release", "value": f"{budget_pct:.0f}%", "tone": "sky"},
        {"icon": "👔", "label": "Approver Role", "value": ceo.get("approver_role") or "CEO", "tone": "mint"},
    ]
    sections = [
        {"icon": "✅", "label": "Strongest Reasons", "tone": "mint",
         "items": (ceo.get("strongest_reasons") or [])[:5] or ["No reasons were returned."]},
        {"icon": "💡", "label": "Next Actions", "tone": "sky",
         "items": (ceo.get("next_actions") or [])[:5] or ["No next actions were returned."]},
        {"icon": "⚠️", "label": "Biggest Concerns", "tone": "coral",
         "items": (ceo.get("biggest_concerns") or [])[:5] or ["No specific concerns were flagged."]},
    ]
    return {
        "icon": "👔", "title": "CEO Decision", "agent_label": "CEO Agent",
        "tagline": "The final recommendation — a human still has to sign off.",
        "kpis": kpis, "sections": sections,
        "conclusion_label": "CEO Agent's Recommendation",
        "conclusion_text": ceo.get("reasoning") or decision.final_recommendation or "Decision complete.",
        "conclusion_good": should == "yes",
    }
