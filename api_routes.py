"""JSON API endpoints used by the frontend JavaScript (polling, AJAX)."""
import logging
import threading

from flask import Blueprint, jsonify, session, abort, current_app

from database import db
from models import Scenario
from graph.boardroom_graph import run_boardroom
from services.flow import FLOW_STEPS, step_state

api_bp = Blueprint("api", __name__)
logger = logging.getLogger("boardroom.api")

_running_lock = threading.Lock()
_running_scenarios = set()


def _owned_or_404(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    if scenario.user_id != session.get("user_id"):
        abort(404)
    return scenario


def _background_run(app, scenario_id, user_id):
    try:
        run_boardroom(app, scenario_id, user_id)
    except Exception:
        logger.exception("Boardroom run crashed for scenario %s", scenario_id)
        with app.app_context():
            scenario = db.session.get(Scenario, scenario_id)
            if scenario:
                scenario.status = "failed"
                scenario.add_error("The workflow crashed unexpectedly. Please try again.")
                db.session.commit()
    finally:
        with _running_lock:
            _running_scenarios.discard(scenario_id)


RERUNNABLE_STATUSES = ("pending", "running", "failed", "completed_with_errors", "completed")


def _reset_scenario_for_rerun(scenario):
    """Clear the previous run's output so a re-run starts from a clean slate.

    Without this, a scenario that failed (e.g. because GEMINI_API_KEY was
    missing) kept its failed AgentResult rows forever and the agent pages
    stayed blank even after the key was fixed.
    """
    from models import AgentResult, Debate, Decision

    AgentResult.query.filter_by(scenario_id=scenario.id).delete()
    Debate.query.filter_by(scenario_id=scenario.id).delete()
    Decision.query.filter_by(scenario_id=scenario.id).delete()
    scenario.errors = "[]"
    scenario.status = "pending"
    scenario.current_stage = "created"
    db.session.commit()


def start_boardroom_run(scenario, user_id):
    """Kick off the LangGraph run in a background thread if one isn't already
    in flight for this scenario. Used both by the manual retry endpoint below
    and directly by new_decision() so the agents start working the instant a
    scenario is created — the user never has to visit a separate "run" page."""
    with _running_lock:
        already_running = scenario.id in _running_scenarios
        if already_running or scenario.status not in RERUNNABLE_STATUSES:
            return False
        _reset_scenario_for_rerun(scenario)
        _running_scenarios.add(scenario.id)
        app_obj = current_app._get_current_object()
        thread = threading.Thread(
            target=_background_run, args=(app_obj, scenario.id, user_id),
            daemon=True,
        )
        thread.start()
        return True


@api_bp.route("/decision/<int:scenario_id>/start", methods=["POST"])
def start_decision(scenario_id):
    scenario = _owned_or_404(scenario_id)
    started = start_boardroom_run(scenario, session["user_id"])
    return jsonify({"started": started, "status": scenario.status,
                    "stage": scenario.current_stage})


@api_bp.route("/decision/<int:scenario_id>/status")
def decision_status(scenario_id):
    """Drives both the step list and the sticky flow chart on the run page."""
    scenario = _owned_or_404(scenario_id)

    failed = {r.agent_name.strip().lower() for r in scenario.agent_results
              if r.status == "failed"}
    completed = [r.agent_name for r in scenario.agent_results if r.status == "completed"]

    nodes = [
        {"key": s["key"], "icon": s["icon"], "label": s["label"], "short": s["short"],
         "desc": s["desc"],
         "state": step_state(s["key"], scenario.current_stage, scenario.status, failed)}
        for s in FLOW_STEPS
    ]
    done_count = sum(1 for n in nodes if n["state"] == "done")

    return jsonify({
        "status": scenario.status,
        "stage": scenario.current_stage,
        "errors": scenario.get_errors(),
        "completed_agents": completed,
        "failed_agents": sorted(failed),
        "has_debate": scenario.debate is not None,
        "has_decision": scenario.decision is not None,
        "nodes": nodes,
        "progress_percent": round(done_count / len(nodes) * 100),
    })


@api_bp.route("/decision/<int:scenario_id>/results")
def decision_results(scenario_id):
    scenario = _owned_or_404(scenario_id)
    results = {r.agent_name: r.data() for r in scenario.agent_results}
    payload = {
        "scenario_id": scenario.id,
        "status": scenario.status,
        "agent_results": results,
        "debate": scenario.debate.as_dict() if scenario.debate else None,
    }
    if scenario.decision:
        payload["decision"] = {
            "weighted_score": scenario.decision.weighted_score,
            "strategic_fit_score": scenario.decision.strategic_fit_score,
            "final_recommendation": scenario.decision.final_recommendation,
            "approval_status": scenario.decision.approval_status,
            "ceo": scenario.decision.ceo_data(),
            "report": scenario.decision.report_data(),
        }
    return jsonify(payload)


@api_bp.route("/decision/<int:scenario_id>", methods=["DELETE"])
def api_delete_decision(scenario_id):
    scenario = _owned_or_404(scenario_id)
    with _running_lock:
        _running_scenarios.discard(scenario_id)
    session.pop(f"what_if_{scenario_id}", None)
    db.session.delete(scenario)
    db.session.commit()
    return jsonify({"success": True, "deleted_id": scenario_id})


@api_bp.route("/agents/<agent_key>/chat", methods=["POST"])
@api_bp.route("/chat/<agent_key>", methods=["POST"])
def api_agent_chat(agent_key):
    from flask import request
    from datetime import datetime
    from services.agent_catalog import get_agent
    from services.agent_chat_service import generate_agent_response

    agent = get_agent(agent_key.lower())
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    scenario_id = data.get("scenario_id")
    scenario = None
    if scenario_id and session.get("user_id"):
        scenario = Scenario.query.filter_by(id=scenario_id, user_id=session["user_id"]).first()

    history = data.get("history", [])

    reply = generate_agent_response(agent_key, message, scenario=scenario, history=history)

    return jsonify({
        "success": True,
        "agent": agent_key.lower(),
        "reply": reply,
        "timestamp": datetime.now().strftime("%H:%M")
    })


