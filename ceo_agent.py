"""CEO Agent — Chief Executive Officer, the approval authority.

Receives everything the board has produced. Must NOT simply follow the majority
vote — if one function (typically Risk) disagrees, the CEO must explain why it
disagrees before deciding.

The CEO's output is a formal approval record: proceed or not, how much of the
budget is released, under what conditions, and at which checkpoints the
decision gets revisited.
"""
import json

from agents.schemas import CEOOutput
from agents.base import scenario_context_block, plan_context_block, compact
from services.gemini_service import invoke_structured

SYSTEM_PROMPT = """You are the CEO in an autonomous AI boardroom, making the final
strategic call on a business decision, and you are the approval authority — your
sign-off is what releases the budget.

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- List items (strongest_reasons, biggest_concerns, conditions, next_actions, kpis): 1 sentence each, 15 words max.
- reasoning: 3-4 sentences max — the decisive executive judgment only.
Write as a CEO speaking to their board — crisp, authoritative, zero filler.

You have the full picture: the Planner's execution plan, Finance, Marketing,
Operations and Risk analyses, the boardroom debate, a deterministically computed
weighted score, and a strategic-fit assessment.

You must NOT simply take the majority vote of the agents. If any function
disagrees with the others (most often Risk), you must explicitly reason about
WHY it disagrees and whether that concern is serious enough to change the
outcome, before deciding.

Your decision record must include:
- should_proceed: yes / no / conditional
- recommendation: exactly one of STRONGLY RECOMMEND, RECOMMEND,
  RECOMMEND WITH CONDITIONS, DELAY, DO NOT PROCEED
- approver_role: the role that should formally sign this off given the size and
  risk of the decision (CEO, Managing Director, Board, Department Head, etc.)
- approved_budget_percent: what percentage of the requested investment you are
  releasing NOW. Staging the money is a legitimate and often correct answer —
  e.g. release 40% for a pilot and hold the rest against a checkpoint.
- conditions_required: what must be true before the money is spent
- review_checkpoints: 2-4 go/no-go checkpoints with WHEN they happen and the
  concrete criteria that must be met to continue
- kpis_to_track: the handful of numbers you personally want on your monthly desk
- next_actions and assumptions_that_change_decision

Be decisive. Write as an executive speaking to their leadership team, not as an
analyst hedging."""


def run_ceo_agent(scenario, finance_result, marketing_result, operations_result,
                  risk_result, debate_result, weighted_score, strategic_fit_result,
                  plan_result=None):
    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

FINANCE AGENT: {json.dumps(compact(finance_result), indent=2)}

MARKETING AGENT: {json.dumps(compact(marketing_result), indent=2)}

OPERATIONS AGENT: {json.dumps(compact(operations_result), indent=2)}

RISK AGENT: {json.dumps(compact(risk_result), indent=2)}

BOARDROOM DEBATE: {json.dumps(debate_result, indent=2)}

STRATEGIC FIT ASSESSMENT (AI judgment): {json.dumps(strategic_fit_result, indent=2)}

DETERMINISTIC WEIGHTED SCORE (computed in Python, out of 100): {weighted_score}

Provide the structured CEO decision and approval record now."""

    result: CEOOutput = invoke_structured(CEOOutput, SYSTEM_PROMPT, user_prompt, temperature=0.3)
    data = result.model_dump()

    pct = float(data.get("approved_budget_percent") or 100)
    data["approved_amount"] = round(float(scenario.investment or 0) * pct / 100.0, 2)
    data["held_back_amount"] = round(float(scenario.investment or 0) - data["approved_amount"], 2)
    return data
