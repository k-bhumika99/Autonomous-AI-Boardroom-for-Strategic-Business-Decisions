"""Single source of truth for the boardroom flow chart.

The same node list drives three things:
  1. the sticky flow chart pinned to the top of every decision page
  2. the live progress tracker on the run page (via /api/.../status)
  3. the stage ordering used to decide what is done / running / waiting

Keeping it in one place means the flow chart can never disagree with the graph.
"""

# key, icon, short label, the endpoint its page lives at (None = no page)
FLOW_STEPS = [
    {"key": "validated",     "icon": "📥", "label": "Request",    "short": "Request",
     "endpoint": None,                  "desc": "Scenario received and validated"},
    {"key": "planner",       "icon": "🧭", "label": "Plan",       "short": "Plan",
     "endpoint": "main.plan_page",      "desc": "Understands the request and plans the work"},
    {"key": "finance",       "icon": "💰", "label": "Finance",    "short": "Finance",
     "endpoint": "main.finance_page",   "desc": "Budget, profit, loss, ROI, projections"},
    {"key": "marketing",     "icon": "📣", "label": "Marketing",  "short": "Growth",
     "endpoint": "main.marketing_page", "desc": "Demand, channels, funnel, growth"},
    {"key": "operations",    "icon": "⚙️", "label": "Operations", "short": "Ops",
     "endpoint": "main.operations_page", "desc": "Roadmap, resources, feasibility"},
    {"key": "risk",          "icon": "⚠️", "label": "Risk",       "short": "Risk",
     "endpoint": "main.risk_page",      "desc": "Probability x impact and mitigation"},
    {"key": "debate",        "icon": "🗣️", "label": "Debate",     "short": "Debate",
     "endpoint": "main.debate_page",    "desc": "Where the agents agree and clash"},
    {"key": "scoring",       "icon": "🧮", "label": "Scoring",    "short": "Score",
     "endpoint": None,                  "desc": "Deterministic weighted score"},
    {"key": "ceo",           "icon": "👔", "label": "CEO",        "short": "CEO",
     "endpoint": "main.ceo_page",       "desc": "Decision and budget approval"},
    {"key": "report",        "icon": "📜", "label": "Report",     "short": "Report",
     "endpoint": "main.report_page",    "desc": "Executive report and export"},
]

# Ordered list of every stage value the graph writes to Scenario.current_stage.
STAGE_ORDER = [
    "created", "starting", "validated",
    "planner_running", "planner_done",
    "finance_running", "finance_done",
    "marketing_running", "marketing_done",
    "operations_running", "operations_done",
    "risk_running", "risk_done",
    "debate_running", "debate_done",
    "strategic_fit_running",
    "scoring_done",
    "ceo_running", "ceo_done",
    "report_running", "completed",
]

_DONE_STAGE = {
    "validated": "validated",
    "scoring": "scoring_done",
    "report": "completed",
}
_RUNNING_STAGE = {
    "validated": "starting",
    "scoring": "debate_done",
    "report": "report_running",
}


def stage_index(stage):
    try:
        return STAGE_ORDER.index(stage or "created")
    except ValueError:
        return 0


def step_state(step_key, stage, status=None, failed_agents=()):
    """done / active / failed / pending for one flow node."""
    if step_key in failed_agents:
        return "failed"

    idx = stage_index(stage)
    done_stage = _DONE_STAGE.get(step_key, f"{step_key}_done")
    running_stage = _RUNNING_STAGE.get(step_key, f"{step_key}_running")

    if status == "failed":
        return "failed" if idx < stage_index(done_stage) else "done"
    if idx >= stage_index(done_stage):
        return "done"
    if idx >= stage_index(running_stage):
        return "active"
    return "pending"


def flow_context(scenario, active_key=None):
    """Everything the sticky flow-chart partial needs to render server-side."""
    failed = {
        r.agent_name.strip().lower()
        for r in (scenario.agent_results or []) if r.status == "failed"
    }
    stage = scenario.current_stage or "created"
    status = scenario.status

    nodes = []
    for step in FLOW_STEPS:
        nodes.append({
            **step,
            "state": step_state(step["key"], stage, status, failed),
        })

    done = sum(1 for n in nodes if n["state"] == "done")
    return {
        "nodes": nodes,
        "stage": stage,
        "status": status,
        "active_key": active_key,
        "progress_percent": round(done / len(nodes) * 100),
        "scenario_id": scenario.id,
        "is_live": status in ("pending", "running"),
    }
