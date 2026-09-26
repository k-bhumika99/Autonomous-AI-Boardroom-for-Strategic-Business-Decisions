"""Decision Agent — Executive Decision Synthesizer.

Builds the final executive report. Most sections are assembled directly from
data already produced by the other agents/services (no LLM re-generation of
numbers); Gemini is used only to write the executive summary, action plan,
90-day plan and final conclusion in professional prose.
"""
import json

from agents.schemas import DecisionReportOutput
from agents.base import scenario_context_block
from services.gemini_service import invoke_structured

SYSTEM_PROMPT = """You are the Executive Decision Synthesizer in an autonomous AI
boardroom. Write, for a report that already contains every agent's detailed data
and charts separately:

BREVITY IS MANDATORY. Keep every output field short, crisp, and high-signal:
- executive_summary: 4-6 sentences a busy executive reads in 30 seconds.
- action_plan items: 1 sentence each, 15 words max, in priority order.
- ninety_day_plan items: 1-2 sentences each with week ranges.
- what_if_insights: 1 sentence each in "if X, then Y" format.
- final_conclusion: 2-3 sentences closing the matter decisively.
No filler, no hedging, no repetition of raw numbers.

- executive_summary: 4-6 sentences a busy executive can read in 30 seconds —
  what is being proposed, what the board concluded, and the single biggest
  reason for that conclusion.
- action_plan: 5-7 concrete actions in priority order.
- ninety_day_plan: what specifically happens in the first 90 days, week ranges
  included where it helps.
- what_if_insights: 3-5 statements of the form "if X changed, the outcome would
  become Y" — the variables the decision is most sensitive to.
- final_conclusion: 2-3 sentences closing the matter.

Do not repeat numbers verbatim; interpret them. Be concise and avoid filler."""


def run_decision_agent(scenario, finance_result, marketing_result, operations_result,
                       risk_result, debate_result, ceo_result, weighted_score,
                       strategic_fit_result, decision_label, plan_result=None):
    plan_result = plan_result or {}
    risks = risk_result.get("risks", []) or []
    projection = finance_result.get("projection", {}) or {}

    user_prompt = f"""{scenario_context_block(scenario)}

WEIGHTED SCORE: {weighted_score}/100 -> {decision_label}
STRATEGIC FIT: {strategic_fit_result.get('score')}/100

PLAN OBJECTIVE: {plan_result.get('business_objective', '')}
RECOMMENDED APPROACH: {plan_result.get('recommended_approach', '')}

3-YEAR PROJECTION: total revenue Rs. {projection.get('total_revenue', 0):,.0f},
total profit Rs. {projection.get('total_profit', 0):,.0f}, payback {projection.get('payback_year') or 'not within horizon'}

CEO DECISION: {json.dumps(ceo_result, indent=2)}
DEBATE CONSENSUS: {debate_result.get('consensus', '')}
KEY RISKS: {json.dumps([r.get('risk') for r in risks][:8])}

Write the executive summary, action plan, 90-day plan, what-if insights and
final conclusion."""

    result: DecisionReportOutput = invoke_structured(
        DecisionReportOutput, SYSTEM_PROMPT, user_prompt
    )
    report = result.model_dump()

    report.update({
        "final_recommendation": decision_label,
        "strategic_score": weighted_score,
        "agent_scores": {
            "finance": finance_result.get("score"),
            "marketing": marketing_result.get("score"),
            "operations": operations_result.get("score"),
            "risk": risk_result.get("score"),
            "strategic_fit": strategic_fit_result.get("score"),
        },
        "planning_score": plan_result.get("readiness_score"),
        "business_objective": plan_result.get("business_objective", ""),
        "key_opportunities": marketing_result.get("opportunities", []),
        "key_risks": [r.get("risk") for r in risks],
        "profit_drivers": finance_result.get("profit_drivers", []),
        "loss_drivers": finance_result.get("loss_drivers", []),
        "growth_levers": marketing_result.get("growth_levers", []),
        "bottlenecks": operations_result.get("bottlenecks", []),
        "debate_summary": debate_result.get("summary", ""),
        "conflicts": debate_result.get("disagreements", []),
        "resolutions": debate_result.get("resolution", []),
        "conditions": ceo_result.get("conditions_required", []),
        "approver_role": ceo_result.get("approver_role", "CEO"),
        "approved_budget_percent": ceo_result.get("approved_budget_percent", 100),
        "ceo_reasoning": ceo_result.get("reasoning", ""),
        "financials": {
            "metrics": finance_result.get("metrics", {}),
            "projection": projection,
            "budget": finance_result.get("budget", {}),
        },
    })
    return report
