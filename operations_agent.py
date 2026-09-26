"""Operations Agent — COO / Chief Operations Officer.

Main question: "Can the company actually execute this, with whom, and by when?"

Supplies the execution roadmap (phases with months), the staffing plan
(roles x headcount x monthly cost) and a readiness assessment across six
dimensions. Python costs the plan and builds the Gantt/radar series.
"""
from agents.schemas import OperationsOutput
from agents.base import scenario_context_block, plan_context_block
from services.gemini_service import invoke_structured
from services import projections as proj

SYSTEM_PROMPT = """You are the COO of a company, acting as the Operations Agent in an
autonomous AI boardroom. Your responsibility is execution feasibility: technical
feasibility, timeline realism, staffing, infrastructure, deployment, support,
scalability, dependencies and operational bottlenecks. You do not comment on
financial ROI or market demand beyond how they affect execution.

BREVITY IS MANDATORY. Every field must be short, crisp, and high-signal:
- List items (key_findings, resource_requirements, bottlenecks, risks): 1 sentence each, 15 words max.
- reasoning: 3-4 sentences max — the critical ops judgment only.
- Phase what_to_do / how_to_do_it: 1-2 sentences each.
A busy COO must absorb this in under 60 seconds.

You must supply, in addition to your qualitative analysis:
- phases: the execution roadmap, 4-6 phases, each with what_to_do, how_to_do_it,
  start_month (0-indexed), duration_months, owner (the team accountable),
  deliverables, exit_criteria and a risk_level. Phases may overlap.
- resource_plan: the roles needed, with headcount and a realistic MONTHLY cost
  in rupees per person for this market. Include engineering, QA, support,
  compliance and any specialist roles the work actually needs.
- readiness: score these six dimensions 0-100 with a one-line comment each:
  Technology, Team & Skills, Process & Governance, Infrastructure,
  Customer Support, Compliance & Security.
- timeline_realism: REALISTIC, TIGHT or UNREALISTIC for the stated timeline,
  plus recommended_timeline_months — what you would actually commit to.

Be concrete. If the stated timeline cannot fit the work, say so plainly and
explain which phase is the constraint. Name the specific bottleneck, not
"resource constraints" in the abstract."""


def run_operations_agent(scenario, plan_result=None):
    months = proj.timeline_to_months(getattr(scenario, "timeline", None), default=6)

    user_prompt = f"""{scenario_context_block(scenario)}

{plan_context_block(plan_result)}

EXECUTION CONTEXT:
- Stated timeline resolves to approximately {months} months.
- Investment available: Rs. {float(scenario.investment or 0):,.0f}
- Annual operating cost budgeted: Rs. {float(scenario.operating_cost or 0):,.0f}

Provide your structured operations analysis now, from the perspective of the COO."""

    result: OperationsOutput = invoke_structured(OperationsOutput, SYSTEM_PROMPT, user_prompt)
    data = result.model_dump()

    recommended = int(data.get("recommended_timeline_months") or months)
    data["roadmap"] = proj.build_roadmap(data.get("phases"), total_months=max(months, recommended))
    data["resources"] = proj.resource_costs(
        data.get("resource_plan"), months=data["roadmap"]["span_months"] or months
    )
    data["timeline_months"] = months
    data["timeline_gap_months"] = max(0, recommended - months)

    # Staffing cost vs the operating budget actually available for the build window.
    budget_for_window = float(scenario.operating_cost or 0) * (data["roadmap"]["span_months"] / 12.0)
    data["staffing_vs_budget"] = {
        "staffing_cost": data["resources"]["total_cost"],
        "budget_available": round(budget_for_window, 2),
        "over_budget": data["resources"]["total_cost"] > budget_for_window > 0,
    }
    return data
