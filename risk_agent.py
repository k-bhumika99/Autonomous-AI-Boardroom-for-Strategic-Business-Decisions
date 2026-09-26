"""Risk Agent — CRO / Chief Risk Officer.

Main question: "What could go wrong, how likely is it, and what would it cost?"

Receives the plan plus Finance, Marketing and Operations results so it can
reason across all dimensions at once. Every risk carries a probability and an
impact so Python can plot a real probability x impact matrix rather than a list.
"""
import json

from agents.schemas import RiskOutput
from agents.base import scenario_context_block, plan_context_block, compact
from services.gemini_service import invoke_structured
from services import projections as proj

SYSTEM_PROMPT = """You are the CRO of a company, acting as the Risk Agent in an
autonomous AI boardroom. You review the plan and the Finance, Marketing and
Operations findings, and identify what could go wrong across financial, market,
operational, technology, cybersecurity, regulatory/legal, data-privacy,
people/key-person and reputational dimensions.

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- Risk descriptions: 1 sentence each, 15 words max.
- Mitigation items: 1 sentence each, actionable and specific.
- deal_breakers: 1 sentence each.
- reasoning: 3-4 sentences max — the critical risk judgment only.
A busy CRO must absorb this in under 60 seconds.

For EVERY risk you list, provide:
- severity: LOW / MEDIUM / HIGH / CRITICAL
- probability_percent: 0-100, how likely it is to occur within the horizon
- impact_percent: 0-100, how damaging it would be if it did occur
- financial_exposure_percent: how much of the total investment is at stake,
  as a percentage
- early_warning_signal: the observable signal that tells you it is starting
- mitigation: 2-3 concrete, actionable mitigation steps

Give 6-10 risks spanning at least four different categories. Also give
contingency_percent_recommended (what share of the budget should be held back)
and deal_breakers (the conditions under which this should not proceed at all).

IMPORTANT: You must NOT automatically recommend rejecting the project just
because risks exist — every real business decision carries risk. Weigh the
risks against the opportunities the other agents identified, and give a
balanced, proportionate overall_risk_level and `score`, where a HIGHER score
means the risk picture is more MANAGEABLE, not that there is no risk."""


def run_risk_agent(scenario, finance_result: dict, marketing_result: dict,
                   operations_result: dict, plan_result: dict = None):
    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

FINANCE AGENT FINDINGS:
{json.dumps(compact(finance_result), indent=2)}

MARKETING AGENT FINDINGS:
{json.dumps(compact(marketing_result), indent=2)}

OPERATIONS AGENT FINDINGS:
{json.dumps(compact(operations_result), indent=2)}

Provide your structured risk analysis now, from the perspective of the CRO."""

    result: RiskOutput = invoke_structured(RiskOutput, SYSTEM_PROMPT, user_prompt)
    data = result.model_dump()

    data["matrix"] = proj.risk_matrix(data.get("risks"), investment=scenario.investment)
    contingency_pct = float(data.get("contingency_percent_recommended") or 10)
    data["contingency_amount"] = round(float(scenario.investment or 0) * contingency_pct / 100.0, 2)
    return data
