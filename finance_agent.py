"""Finance Agent — CFO / Chief Financial Analyst.

Main question: "Does this business decision make financial sense?"

Every number on the finance dashboard is computed deterministically in
services/calculations.py and services/projections.py. Gemini supplies only
the ASSUMPTIONS that drive those projections (growth rates, best/worst
multipliers, budget split) and the qualitative interpretation.
"""
from agents.schemas import FinanceOutput
from agents.base import scenario_context_block, plan_context_block
from services.gemini_service import invoke_structured
from services.calculations import compute_financials, financial_score_from_metrics
from services import projections as proj

SYSTEM_PROMPT = """You are the CFO of a company, acting as the Finance Agent in an
autonomous AI boardroom. Your sole responsibility is financial analysis — you do
not comment on marketing, operations or general risk beyond financial risk.

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- List items (profit_drivers, loss_drivers, key_findings, risks, etc.): 1 sentence each, 15 words max.
- reasoning: 3-4 sentences max — the critical financial judgment only.
- recommendation: 1-2 sentences.
A busy CFO must absorb this in under 60 seconds.

You receive the business scenario, the Planner's execution plan, AND pre-computed
financial metrics (profit, ROI, margin, break-even) calculated deterministically
in Python. Treat those numbers as ground truth — never recompute or contradict them.

Your job is to:
1. Interpret what those numbers mean for the business.
2. Supply the forward-looking ASSUMPTIONS the projection engine needs:
   - revenue_growth_percent: realistic year-on-year revenue growth after year 1
   - cost_growth_percent: year-on-year operating cost growth
   - optimistic_multiplier / pessimistic_multiplier: revenue multipliers for
     the best and worst case (e.g. 1.3 and 0.65)
   - budget_allocation: how the investment should be split, as percentages
     summing to 100, refining the Planner's split from a finance viewpoint
3. Name the specific PROFIT DRIVERS (what makes money here) and LOSS DRIVERS
   (what will quietly bleed money here), concrete cost optimizations, and
   funding recommendations (bootstrapped / staged tranches / debt / equity).
4. Give 4-6 KPIs the finance team should watch monthly.

Be honest and specific. If the user did not provide enough information for a
metric, list it as an assumption rather than inventing a number."""


def run_finance_agent(scenario, plan_result=None):
    metrics = compute_financials(
        scenario.investment, scenario.expected_revenue, scenario.operating_cost
    )
    deterministic_score = financial_score_from_metrics(metrics)
    months = proj.timeline_to_months(getattr(scenario, "timeline", None), default=6)

    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

PRE-COMPUTED FINANCIAL METRICS (Python, deterministic — do not alter these):
Total Cost: Rs. {metrics['total_cost']:,.0f}
Profit: Rs. {metrics['profit']:,.0f}
ROI: {metrics['roi_percent']}%
Profit Margin: {metrics['profit_margin_percent']}%
Break-even: {metrics['breakeven_years']} years (null means it does not break even at this run-rate)
Build/launch ramp: roughly {months} months before revenue reaches run-rate.

A deterministic financial-health baseline score is {deterministic_score}/100 —
use it as a strong anchor, but you may adjust the final `score` field by a
modest amount if qualitative factors justify it.

Provide your structured financial analysis now."""

    result: FinanceOutput = invoke_structured(FinanceOutput, SYSTEM_PROMPT, user_prompt)
    data = result.model_dump()

    # ---- Deterministic projections built from the agent's assumptions -----
    data["metrics"] = metrics
    data["deterministic_score"] = deterministic_score
    data["budget"] = proj.build_budget(scenario.investment, data.get("budget_allocation"))
    data["projection"] = proj.build_projection(
        scenario.investment, scenario.expected_revenue, scenario.operating_cost,
        revenue_growth_percent=data.get("revenue_growth_percent", 20),
        cost_growth_percent=data.get("cost_growth_percent", 10),
        years=3, ramp_months=months,
    )
    data["cashflow"] = proj.monthly_cashflow(
        scenario.investment, scenario.expected_revenue, scenario.operating_cost,
        ramp_months=months, horizon_months=max(24, months + 18),
    )
    data["scenarios"] = proj.scenario_bands(
        scenario.expected_revenue, scenario.operating_cost, scenario.investment,
        optimistic_multiplier=data.get("optimistic_multiplier", 1.25),
        pessimistic_multiplier=data.get("pessimistic_multiplier", 0.7),
        revenue_growth_percent=data.get("revenue_growth_percent", 20),
        cost_growth_percent=data.get("cost_growth_percent", 10),
        years=3, ramp_months=months,
    )
    data["bridge"] = proj.profit_bridge(
        scenario.investment, scenario.expected_revenue, scenario.operating_cost
    )
    return data
