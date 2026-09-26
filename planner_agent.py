"""Planner Agent — Chief of Staff / Program Director.

This is the FIRST agent in the boardroom. Before anyone analyses money,
markets or risk, somebody has to answer: what is actually being asked for?

It answers the four questions the user cares about up front:
    WHAT to do   -> phases[].what_to_do + scope_included / scope_excluded
    HOW to do it -> phases[].how_to_do_it + recommended_approach
    WHEN to do it-> phases[].start_month / duration_months
    HOW MUCH     -> budget_allocation (percentages, costed in Python)

Everything downstream (Finance, Marketing, Operations, Risk) receives this
plan, so the whole board reasons about the same interpretation of the request.
"""
from agents.schemas import PlannerOutput
from agents.base import scenario_context_block
from services.gemini_service import invoke_structured
from services.projections import timeline_to_months, build_budget

SYSTEM_PROMPT = """You are the Chief of Staff / Program Director acting as the
Planner Agent in an autonomous AI boardroom. You run BEFORE the Finance,
Marketing, Operations and Risk agents, and your plan is handed to all of them.

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- List items: 1 sentence each, 15 words max. No filler, no qualifiers.
- reasoning: 3-4 sentences max covering only the critical judgment call.
- understood_request / business_objective / recommended_approach: 1-2 sentences each.
- Phases: keep what_to_do and how_to_do_it to 1-2 sentences each.
A busy executive must grasp the entire plan in under 60 seconds.

Your job has four parts:

1. UNDERSTAND. Restate, in your own words, what the company is actually asking
   for — including the parts they implied but did not say. If the request is
   ambiguous, say what you assumed and list the open questions a real program
   director would ask before committing budget.

2. SCOPE. State plainly what IS in scope and what is explicitly NOT in scope
   for this investment. Excluding things is as valuable as including them.

3. PLAN. Break the work into 4-6 sequential (or overlapping) phases. For each
   phase give: what to do, HOW to do it concretely, which month it starts,
   how many months it runs, who owns it, the deliverables, and the exit
   criteria that let the company move to the next phase. The phases must fit
   inside the stated timeline. If the timeline cannot fit the work, still plan
   realistically and flag it in your reasoning.

4. BUDGET SHAPE. Propose how the investment should be split across categories
   as PERCENTAGES that add up to 100. Do not give rupee amounts — the system
   computes those. Always include a contingency/buffer line.

Also define 3-5 success metrics with concrete targets, so the board knows what
"this worked" will look like 12 months from now.

Be specific to THIS business and THIS industry. Generic project-management
boilerplate is a failure. Never invent market statistics; if you need a number
that was not provided, list it under critical_assumptions."""


def run_planner_agent(scenario):
    months = timeline_to_months(getattr(scenario, "timeline", None), default=6)

    user_prompt = f"""{scenario_context_block(scenario)}

PLANNING CONSTRAINTS:
- The stated timeline resolves to approximately {months} months. Your phases
  should fit inside that window (phase start_month is 0-indexed from today).
- The investment available is Rs. {float(scenario.investment or 0):,.0f}. Split it
  as percentages across 5-7 categories that sum to 100.
- Judge the complexity (LOW / MEDIUM / HIGH) and a readiness_score out of 100
  reflecting how ready this request is to be executed as written — a vague
  request with missing numbers scores low even if the idea is good.

Produce the structured plan now."""

    result: PlannerOutput = invoke_structured(
        PlannerOutput, SYSTEM_PROMPT, user_prompt, temperature=0.35
    )
    data = result.model_dump()

    # Cost the plan deterministically in Python.
    data["budget"] = build_budget(scenario.investment, data.get("budget_allocation"))
    data["timeline_months"] = months
    return data
