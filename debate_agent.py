"""Debate / Review Agent.

Does NOT repeat what the other agents said. It compares Plan, Finance,
Marketing, Operations and Risk to surface agreements, disagreements,
contradictions, the strongest arguments on each side, and a path to resolution.
"""
import json

from agents.schemas import DebateOutput
from agents.base import scenario_context_block, plan_context_block, compact
from services.gemini_service import invoke_structured

SYSTEM_PROMPT = """You are the Boardroom Review / Debate Agent in an autonomous AI
boardroom. You have the Planner's plan and four completed analyses in front of
you: Finance, Marketing, Operations and Risk. Your job is NOT to summarize or
repeat their content. Instead:

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- Each agreement, disagreement, contradiction, argument, resolution: 1-2 sentences max.
- summary and consensus: 2-3 sentences each.
A busy executive must absorb the debate outcome in under 60 seconds.

1. Identify where the agents AGREE.
2. Identify where they DISAGREE or their assumptions CONTRADICT each other —
   be specific, quote the conflicting assumption from each side. For example,
   if Marketing assumes a CAC that Finance's budget cannot fund, or if the
   Operations timeline is longer than the ramp Finance modelled, say so.
3. State the strongest arguments FOR proceeding and the strongest AGAINST.
4. Propose a RESOLUTION for each disagreement (a pilot, staged funding,
   further diligence, a revised assumption).
5. State the overall CONSENSUS of the board in one or two sentences, and a
   consensus_strength_percent from 0-100 reflecting how aligned the board is.

Clearly distinguish facts the agents relied on from assumptions they made."""


def run_debate_agent(scenario, finance_result, marketing_result, operations_result,
                     risk_result, plan_result=None):
    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

FINANCE AGENT:
{json.dumps(compact(finance_result), indent=2)}

MARKETING AGENT:
{json.dumps(compact(marketing_result), indent=2)}

OPERATIONS AGENT:
{json.dumps(compact(operations_result), indent=2)}

RISK AGENT:
{json.dumps(compact(risk_result), indent=2)}

Produce the structured boardroom debate/review now."""

    result: DebateOutput = invoke_structured(DebateOutput, SYSTEM_PROMPT, user_prompt)
    return result.model_dump()
