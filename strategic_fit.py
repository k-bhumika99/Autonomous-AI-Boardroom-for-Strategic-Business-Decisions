"""Strategic fit evaluation.

This is explicitly an AI *assessment*, not an objective fact — it is labeled
as such everywhere it is displayed.
"""
import json

from agents.schemas import StrategicFitOutput
from agents.base import scenario_context_block, plan_context_block
from services.gemini_service import invoke_structured

SYSTEM_PROMPT = """You assess STRATEGIC FIT for a business decision inside an
autonomous AI boardroom: alignment with typical company goals, long-term growth
potential, competitive advantage, scalability and strategic importance. This is
an AI judgment call, not a measured fact — say so plainly in your notes."""


def run_strategic_fit(scenario, finance_result, marketing_result, operations_result,
                      plan_result=None):
    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

FINANCE SUMMARY: {json.dumps(finance_result.get('key_findings', []))}
MARKETING SUMMARY: {json.dumps(marketing_result.get('key_findings', []))}
OPERATIONS SUMMARY: {json.dumps(operations_result.get('key_findings', []))}

Give a strategic fit score (0-100) and brief alignment notes."""
    result: StrategicFitOutput = invoke_structured(StrategicFitOutput, SYSTEM_PROMPT, user_prompt)
    return result.model_dump()
