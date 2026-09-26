"""Shared helpers used across the agent modules."""
import logging

logger = logging.getLogger("boardroom.agents")

# Keys that hold large computed series — useful for charts, useless (and
# expensive) inside another agent's prompt.
_HEAVY_KEYS = {
    "projection", "cashflow", "scenarios", "bridge", "growth", "funnel_model",
    "channel_model", "segments_model", "matrix", "roadmap", "resources",
    "budget", "metrics", "evidence",
}


def scenario_context_block(scenario) -> str:
    """Builds the shared 'facts' block every agent receives, so every agent
    reasons from the same user-supplied facts rather than re-deriving them."""
    return f"""
BUSINESS SCENARIO (facts as provided by the user — do not contradict these):
Title: {scenario.title}
Description: {scenario.description}
Industry: {getattr(scenario, "industry", None) or "Not specified"}
Business Model: {getattr(scenario, "business_model", None) or "Not specified"}
Investment: Rs. {float(scenario.investment or 0):,.0f}
Expected Annual Revenue: Rs. {float(scenario.expected_revenue or 0):,.0f}
Operating Cost: Rs. {float(scenario.operating_cost or 0):,.0f}
Target Market: {scenario.target_market or "Not specified"}
Expected Customers: {scenario.expected_customers or "Not specified"}
Timeline: {scenario.timeline or "Not specified"}
Additional Information: {scenario.additional_information or "None provided"}
""".strip()


def plan_context_block(plan_result) -> str:
    """The Planner's interpretation, handed to every downstream agent so the
    whole board works from one shared reading of the request."""
    if not plan_result or plan_result.get("_failed"):
        return "APPROVED PLAN: not available — reason from the scenario facts alone."

    phases = plan_result.get("phases") or []
    phase_lines = "\n".join(
        f"  - {p.get('phase')}: {p.get('what_to_do', '')} "
        f"(month {p.get('start_month', 0)}, {p.get('duration_months', 1)} months, "
        f"owner: {p.get('owner', 'TBD')})"
        for p in phases[:8]
    ) or "  - none specified"

    budget_lines = "\n".join(
        f"  - {b.get('category')}: {b.get('percent')}%"
        for b in (plan_result.get("budget_allocation") or [])[:8]
    ) or "  - none specified"

    metrics = ", ".join(
        f"{m.get('metric')} ({m.get('target')})"
        for m in (plan_result.get("success_metrics") or [])[:5]
    ) or "none specified"

    return f"""
PLANNER AGENT'S APPROVED PLAN (all agents must reason against this plan):
Understood request: {plan_result.get('understood_request', '')}
Business objective: {plan_result.get('business_objective', '')}
Decision type: {plan_result.get('decision_type', '')} | Complexity: {plan_result.get('complexity', '')}
Recommended approach: {plan_result.get('recommended_approach', '')}
In scope: {"; ".join(plan_result.get('scope_included', [])[:6]) or "not specified"}
Out of scope: {"; ".join(plan_result.get('scope_excluded', [])[:6]) or "not specified"}
Success metrics: {metrics}
Phases:
{phase_lines}
Proposed budget split:
{budget_lines}
""".strip()


def compact(result: dict, keep_lists: int = 6) -> dict:
    """Strips the heavy computed series out of an agent result before it is
    embedded in another agent's prompt, and truncates long lists. Keeps the
    prompts small enough to stay fast and cheap without losing the substance."""
    if not isinstance(result, dict):
        return {}
    out = {}
    for k, v in result.items():
        if k in _HEAVY_KEYS:
            continue
        if isinstance(v, list):
            out[k] = v[:keep_lists]
        else:
            out[k] = v
    return out
