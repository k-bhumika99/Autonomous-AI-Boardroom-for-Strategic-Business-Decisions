"""Marketing Agent — CMO / Chief Marketing Strategist.

Main question: "Will customers want this, and how do we grow it?"

The agent supplies the growth ASSUMPTIONS (channel mix, funnel conversion
rates, year-one growth); services/projections.py turns them into the adoption
curve, funnel volumes, channel spend and unit economics on the dashboard.
"""
from agents.schemas import MarketingOutput
from agents.base import scenario_context_block, plan_context_block
from services.gemini_service import invoke_structured
from services import projections as proj

SYSTEM_PROMPT = """You are the CMO of a company, acting as the Marketing Agent in an
autonomous AI boardroom. Your responsibility is market, customer and GROWTH
analysis: demand, segments, competition, pricing, positioning, acquisition
channels, the conversion funnel and how the customer base grows over time.
You do not comment on financial accounting or engineering feasibility.

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- List items (growth_levers, key_findings, risks, opportunities): 1 sentence each, 15 words max.
- reasoning, positioning_statement, pricing_recommendation: 1-2 sentences each.
A busy CMO must absorb this in under 60 seconds.

You must supply, in addition to your qualitative analysis:
- segments: 2-4 customer segments with share_percent summing to ~100 and why
  each one matters
- channels: 3-6 acquisition channels with budget_share_percent summing to ~100,
  a realistic expected_cac (customer acquisition cost in rupees) for this market,
  and the expected conversion percent
- funnel: 4-6 ordered stages from awareness to paying customer, each with the
  percentage that converts from the PREVIOUS stage (the first stage is 100)
- year_one_growth_percent: how fast the customer base compounds after the
  initial ramp
- marketing_budget_share_percent: what share of the total investment should go
  to marketing and sales
- positioning_statement and pricing_recommendation: one concrete sentence each
- growth_levers: the 3-5 specific things that would most accelerate growth

CRITICAL: Do NOT invent market-size numbers, competitor names, or statistics the
user did not provide. Where you need a data point that was not given, state it
clearly under assumptions. CAC and conversion estimates ARE expected — mark them
as assumptions, but make them realistic for this industry and market."""


def run_marketing_agent(scenario, plan_result=None):
    months = proj.timeline_to_months(getattr(scenario, "timeline", None), default=6)

    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

GROWTH CONTEXT:
- Total investment available: Rs. {float(scenario.investment or 0):,.0f}
- Expected annual revenue at run-rate: Rs. {float(scenario.expected_revenue or 0):,.0f}
- Customer target provided by the user: {scenario.expected_customers or "not specified"}
- Launch ramp: roughly {months} months.

Provide your structured marketing and growth analysis now, from the perspective
of the CMO."""

    result: MarketingOutput = invoke_structured(MarketingOutput, SYSTEM_PROMPT, user_prompt)
    data = result.model_dump()

    # ---- Deterministic growth model from the agent's assumptions ---------
    investment = float(scenario.investment or 0)
    mkt_share = float(data.get("marketing_budget_share_percent") or 20)
    marketing_budget = round(investment * mkt_share / 100.0, 2)

    data["marketing_budget"] = marketing_budget
    data["growth"] = proj.customer_growth_curve(
        scenario.expected_customers, ramp_months=months,
        horizon_months=max(24, months + 18),
        year_growth_percent=data.get("year_one_growth_percent", 30),
    )
    data["funnel_model"] = proj.build_funnel(
        data.get("funnel"), expected_customers=scenario.expected_customers
    )
    data["channel_model"] = proj.channel_plan(
        data.get("channels"), marketing_budget, scenario.expected_customers
    )
    data["unit_economics"] = proj.unit_economics(
        scenario.expected_revenue, scenario.expected_customers,
        marketing_budget, scenario.operating_cost,
    )
    data["segments_model"] = proj.normalize_percentages(
        data.get("segments"), key="share_percent"
    )
    return data
