"""All HTML page routes."""
from datetime import datetime
from io import BytesIO

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, abort, send_file, current_app)

from database import db
from models import Scenario, Decision
from auth import login_required, current_user
from services.what_if import run_what_if
from services.report_service import build_report_context, generate_pdf_report
from services import projections as proj
from services import step_view
from services.agent_catalog import get_all_agents, get_agent, AGENTS_CATALOG

main_bp = Blueprint("main", __name__)


def _owned_scenario_or_404(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    if scenario.user_id != session.get("user_id"):
        abort(404)
    session["active_scenario_id"] = scenario.id
    return scenario


def _get_active_scenario_or_default():
    user = current_user()
    if not user:
        return None
    sc_id = session.get("active_scenario_id")
    if sc_id:
        scenario = Scenario.query.filter_by(id=sc_id, user_id=user.id).first()
        if scenario:
            return scenario
    latest = Scenario.query.filter_by(user_id=user.id).order_by(Scenario.created_at.desc()).first()
    if latest:
        session["active_scenario_id"] = latest.id
        return latest
    return None


def _agent_page(scenario_id, agent_key, template, **extra):
    """Shared shape for the (non-wizard) agent pages, e.g. Plan."""
    scenario = _owned_scenario_or_404(scenario_id)
    result = scenario.get_result(agent_key)
    return render_template(
        template,
        scenario=scenario,
        result=result.data() if result else None,
        **extra,
    )


# ---------------------------------------------------------------- Home -----
@main_bp.route("/")
@main_bp.route("/index.html")
def home():
    if current_user() is not None:
        return redirect(url_for("main.dashboard"))
    return render_template("home.html")


@main_bp.route("/features")
@main_bp.route("/features.html")
def features():
    return render_template("features.html")


@main_bp.route("/how-it-works")
@main_bp.route("/how-it-works.html")
def how_it_works():
    return render_template("how-it-works.html")


@main_bp.route("/about")
@main_bp.route("/about.html")
def about():
    return render_template("agents_public.html", agents=get_all_agents(), agents_map=AGENTS_CATALOG, active_page="about")


@main_bp.route("/agents")
@main_bp.route("/agents.html")
def agents_hub():
    user = current_user()
    scenarios = []
    if user:
        scenarios = Scenario.query.filter_by(user_id=user.id).order_by(Scenario.created_at.desc()).all()
        return render_template("agents_hub.html", agents=get_all_agents(), agents_map=AGENTS_CATALOG,
                               user=user, scenarios=scenarios, active_page="agents")
    return render_template("agents_public.html", agents=get_all_agents(), agents_map=AGENTS_CATALOG, active_page="agents")


@main_bp.route("/agents/<agent_key>")
def agent_detail(agent_key):
    agent = get_agent(agent_key.lower())
    if not agent:
        abort(404)
    user = current_user()
    scenarios = []
    selected_scenario = None
    agent_result = None

    if user:
        scenarios = Scenario.query.filter_by(user_id=user.id).order_by(Scenario.created_at.desc()).all()
        scenario_id_param = request.args.get("scenario_id")
        if scenario_id_param:
            try:
                selected_scenario = Scenario.query.filter_by(id=int(scenario_id_param), user_id=user.id).first()
            except (ValueError, TypeError):
                selected_scenario = None
        elif scenarios:
            selected_scenario = scenarios[0]

        if selected_scenario:
            if agent_key.lower() == "ceo":
                agent_result = selected_scenario.decision.ceo_data() if selected_scenario.decision else None
            elif agent_key.lower() == "debate":
                agent_result = selected_scenario.debate.as_dict() if selected_scenario.debate else None
            else:
                res_obj = selected_scenario.get_result(agent_key.lower())
                agent_result = res_obj.data() if res_obj else None

    return render_template(
        "agent_detail.html",
        agent=agent,
        all_agents=get_all_agents(),
        agents_map=AGENTS_CATALOG,
        user=user,
        scenarios=scenarios,
        selected_scenario=selected_scenario,
        agent_result=agent_result,
        active_page="agents",
        active_agent=agent_key.lower()
    )


@main_bp.route("/agents/<agent_key>/chat")
@main_bp.route("/chat/<agent_key>")
def agent_chat(agent_key):
    agent = get_agent(agent_key.lower())
    if not agent:
        abort(404)
    user = current_user()
    scenarios = []
    selected_scenario = None

    if user:
        scenarios = Scenario.query.filter_by(user_id=user.id).order_by(Scenario.created_at.desc()).all()
        scenario_id_param = request.args.get("scenario_id")
        if scenario_id_param:
            try:
                selected_scenario = Scenario.query.filter_by(id=int(scenario_id_param), user_id=user.id).first()
            except (ValueError, TypeError):
                selected_scenario = None
        elif scenarios:
            selected_scenario = scenarios[0]

    from services.agent_chat_service import get_suggested_questions
    suggested_questions = get_suggested_questions(agent_key)

    return render_template(
        "agent_chat.html",
        agent=agent,
        all_agents=get_all_agents(),
        agents_map=AGENTS_CATALOG,
        user=user,
        scenarios=scenarios,
        selected_scenario=selected_scenario,
        suggested_questions=suggested_questions,
        active_page="agents",
        active_agent=agent_key.lower()
    )


@main_bp.route("/chat")
def general_chat():
    """Default redirect to Planner agent chat if no agent key specified."""
    return redirect(url_for("main.agent_chat", agent_key="planner"))


@main_bp.route("/contact")
@main_bp.route("/contact.html")
def contact():
    return render_template("contact.html")


@main_bp.route("/signin.html")
def signin_redirect():
    return redirect(url_for("auth.signin"))


@main_bp.route("/signup.html")
def signup_redirect():
    return redirect(url_for("auth.signup"))


@main_bp.route("/style.css")
def root_style():
    import os
    from flask import send_from_directory, current_app
    return send_from_directory(current_app.root_path, "style.css", mimetype="text/css")


@main_bp.route("/images/<path:filename>")
def root_images(filename):
    import os
    from flask import send_from_directory, current_app
    return send_from_directory(os.path.join(current_app.root_path, "images"), filename)


# ----------------------------------------------------------- Dashboard -----
@main_bp.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    scenarios = Scenario.query.filter_by(user_id=user.id).order_by(
        Scenario.created_at.desc()).all()

    total_decisions = len(scenarios)
    completed = [s for s in scenarios if s.is_done]
    completed_count = len(completed)

    scores = [s.decision.weighted_score for s in completed if s.decision]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    pending_approvals = [
        s for s in completed
        if s.decision and s.decision.approval_status == "awaiting_approval"
    ]

    analytics = proj.portfolio_analytics(scenarios)

    # Risk severity & category rollup (merged from the old analytics page)
    severity_totals = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    category_totals = {}
    for s in scenarios:
        risk = s.result_data("risk")
        matrix = risk.get("matrix") or {}
        for sev, count in (matrix.get("severities") or {}).items():
            if sev in severity_totals:
                severity_totals[sev] += count
        for cat, count in (matrix.get("categories") or {}).items():
            category_totals[cat] = category_totals.get(cat, 0) + count

    approvals = {"approved": 0, "approved_with_conditions": 0,
                 "rejected": 0, "awaiting_approval": 0, "sent_back": 0}
    for s in scenarios:
        if s.decision:
            key = s.decision.approval_status or "awaiting_approval"
            approvals[key] = approvals.get(key, 0) + 1

    latest = scenarios[0] if scenarios else None

    hour = datetime.now().hour
    if hour < 12:
        greeting, emoji = "Good morning", "☀️"
    elif hour < 17:
        greeting, emoji = "Good afternoon", "🌤️"
    else:
        greeting, emoji = "Good evening", "🌙"

    return render_template(
        "dashboard.html",
        user=user, scenarios=scenarios[:8],
        total_decisions=total_decisions, completed_count=completed_count,
        avg_score=avg_score, latest=latest, greeting=greeting, greeting_emoji=emoji,
        analytics=analytics, pending_approvals=pending_approvals,
        severity_totals=severity_totals, category_totals=category_totals,
        approvals=approvals,
    )


@main_bp.route("/analytics")
@login_required
def analytics_page():
    """Analytics was merged into Dashboard. Redirect for old bookmarks."""
    return redirect(url_for("main.dashboard"))


# --------------------------------------------------------- New Decision ----
@main_bp.route("/decision/new", methods=["GET", "POST"])
@login_required
def new_decision():
    if request.method == "POST":
        try:
            investment = float(request.form.get("investment") or 0)
            expected_revenue = float(request.form.get("expected_revenue") or 0)
            operating_cost = float(request.form.get("operating_cost") or 0)
            expected_customers = int(float(request.form.get("expected_customers") or 0))
        except ValueError:
            flash("🔢 Please enter valid numbers for the financial fields.", "error")
            return render_template("new_decision.html")

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not title or not description:
            flash("📝 Please provide a title and a business scenario description.", "error")
            return render_template("new_decision.html")

        scenario = Scenario(
            user_id=session["user_id"],
            title=title,
            description=description,
            investment=investment,
            expected_revenue=expected_revenue,
            operating_cost=operating_cost,
            target_market=request.form.get("target_market", "").strip(),
            expected_customers=expected_customers,
            timeline=request.form.get("timeline", "").strip(),
            additional_information=request.form.get("additional_information", "").strip(),
            industry=request.form.get("industry", "").strip(),
            business_model=request.form.get("business_model", "").strip(),
            decision_owner=request.form.get("decision_owner", "").strip() or "CEO",
            status="pending",
            current_stage="created",
        )
        db.session.add(scenario)
        db.session.commit()

        from routes.api_routes import start_boardroom_run
        start_boardroom_run(scenario, session["user_id"])

        return redirect(url_for("main.finance_page", scenario_id=scenario.id))

    return render_template("new_decision.html")


@main_bp.route("/decision/<int:scenario_id>/run")
@login_required
def boardroom_execution(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    from routes.api_routes import start_boardroom_run
    start_boardroom_run(scenario, session["user_id"])
    next_page = request.args.get("next", "finance_page")
    return redirect(url_for(f"main.{next_page}", scenario_id=scenario_id))


# ------------------------------------------------------- Step wizard -------
STEP_AGENTS = ["finance", "marketing", "operations", "risk", "ceo"]
STEP_LABELS = {"finance": "Finance", "marketing": "Marketing",
              "operations": "Operations", "risk": "Risk", "ceo": "CEO Decision"}


def _step_nav(agent_key, scenario_id):
    idx = STEP_AGENTS.index(agent_key)
    next_key = STEP_AGENTS[idx + 1] if idx + 1 < len(STEP_AGENTS) else None
    next_url = url_for(f"main.{next_key}_page" if next_key != "ceo" else "main.ceo_page",
                       scenario_id=scenario_id) if next_key else None
    return {
        "step": idx + 1, "total_steps": len(STEP_AGENTS),
        "next_url": next_url, "next_label": STEP_LABELS.get(next_key, ""),
        "back_url": url_for("main.dashboard"),
        "active_page": agent_key if agent_key != "ceo" else "ceo",
    }


def _render_step(scenario_id, agent_key, template_title, icon, context_builder, approval=False):
    scenario = _owned_scenario_or_404(scenario_id)
    result_row = scenario.get_result(agent_key)
    result = result_row.data() if result_row else None
    nav = _step_nav(agent_key, scenario_id)

    if result is None:
        # Not finished yet — ensure the background run is alive so the user is never stuck
        from routes.api_routes import _running_scenarios, start_boardroom_run
        if scenario.id not in _running_scenarios and scenario.status in ("pending", "running", "failed"):
            start_boardroom_run(scenario, session.get("user_id"))
        return render_template("agent_step.html", scenario=scenario, waiting=True,
                               icon=icon, agent_label=STEP_LABELS[agent_key] + " Agent",
                               title=template_title, agent_key=agent_key, **nav)

    if result.get("_failed"):
        return render_template("agent_step.html", scenario=scenario, waiting=False,
                               result=result, icon=icon,
                               agent_label=STEP_LABELS[agent_key] + " Agent",
                               title=template_title, **nav)

    ctx = context_builder(scenario, result)
    return render_template("agent_step.html", scenario=scenario, waiting=False,
                           result=result, **ctx, **nav)


# --------------------------------------------------- Direct Agent Access Routes ---
@main_bp.route("/plan")
@login_required
def plan_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to generate strategic plans.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.plan_page", scenario_id=scenario.id))


@main_bp.route("/finance")
@login_required
def finance_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to generate financial analysis.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.finance_page", scenario_id=scenario.id))


@main_bp.route("/marketing")
@login_required
def marketing_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to generate marketing strategy.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.marketing_page", scenario_id=scenario.id))


@main_bp.route("/operations")
@login_required
def operations_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to generate operations roadmap.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.operations_page", scenario_id=scenario.id))


@main_bp.route("/risk")
@login_required
def risk_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to generate risk assessment.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.risk_page", scenario_id=scenario.id))


@main_bp.route("/debate")
@login_required
def debate_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to view the multi-agent debate.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.debate_page", scenario_id=scenario.id))


@main_bp.route("/ceo")
@login_required
def ceo_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to review the CEO decision.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.ceo_page", scenario_id=scenario.id))


@main_bp.route("/report")
@login_required
def report_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to generate the executive report.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.report_page", scenario_id=scenario.id))


@main_bp.route("/what-if")
@login_required
def what_if_direct():
    scenario = _get_active_scenario_or_default()
    if not scenario:
        flash("📝 Please enter a scenario first to run what-if simulations.", "info")
        return redirect(url_for("main.new_decision"))
    return redirect(url_for("main.what_if_page", scenario_id=scenario.id))


# ------------------------------------------------------------ Agent pages --
@main_bp.route("/decision/<int:scenario_id>/plan")
@login_required
def plan_page(scenario_id):
    return _agent_page(scenario_id, "planner", "plan.html")


@main_bp.route("/decision/<int:scenario_id>/finance")
@login_required
def finance_page(scenario_id):
    return _render_step(scenario_id, "finance", "Financial Analysis", "💰",
                        step_view.finance_step_context)


@main_bp.route("/decision/<int:scenario_id>/marketing")
@login_required
def marketing_page(scenario_id):
    return _render_step(scenario_id, "marketing", "Marketing Strategy", "📣",
                        step_view.marketing_step_context)


@main_bp.route("/decision/<int:scenario_id>/operations")
@login_required
def operations_page(scenario_id):
    return _render_step(scenario_id, "operations", "Operations Plan", "⚙️",
                        step_view.operations_step_context)


@main_bp.route("/decision/<int:scenario_id>/risk")
@login_required
def risk_page(scenario_id):
    return _render_step(scenario_id, "risk", "Risk Assessment", "⚠️",
                        step_view.risk_step_context)


@main_bp.route("/decision/<int:scenario_id>/debate")
@login_required
def debate_page(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    debate = scenario.debate.as_dict() if scenario.debate else None
    return render_template(
        "debate.html", scenario=scenario, debate=debate,
        finance=scenario.result_data("finance"), marketing=scenario.result_data("marketing"),
        operations=scenario.result_data("operations"), risk=scenario.result_data("risk"),
    )


@main_bp.route("/decision/<int:scenario_id>/ceo")
@login_required
def ceo_page(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    decision = scenario.decision
    nav = _step_nav("ceo", scenario_id)

    if not decision:
        # Risk has finished but the CEO/decision step hasn't landed yet.
        return render_template("agent_step.html", scenario=scenario, waiting=True,
                               icon="👔", agent_label="CEO Agent",
                               title="CEO Decision", agent_key="ceo", **nav)

    ceo = decision.ceo_data() if decision.ceo_data() else {}
    if not ceo or ceo.get("_failed"):
        return render_template("agent_step.html", scenario=scenario, waiting=False,
                               result=ceo or {"_failed": True, "reasoning":
                               "The CEO agent has not produced a recommendation yet."},
                               icon="👔", agent_label="CEO Agent",
                               title="CEO Decision", **nav)

    ctx = step_view.ceo_step_context(scenario, decision, ceo)
    return render_template("agent_step.html", scenario=scenario, waiting=False,
                           result=ceo, decision=decision, approval=True, **ctx, **nav)


# ------------------------------------------------------- Human sign-off ----
VALID_APPROVAL_ACTIONS = {
    "approve": "approved",
    "approve_with_conditions": "approved_with_conditions",
    "reject": "rejected",
    "send_back": "sent_back",
}


@main_bp.route("/decision/<int:scenario_id>/approve", methods=["POST"])
@login_required
def approve_decision(scenario_id):
    """The human sign-off step. The AI CEO recommends; the person who owns the
    budget records the actual decision here."""
    scenario = _owned_scenario_or_404(scenario_id)
    decision = scenario.decision
    if not decision:
        flash("⏳ This decision has not finished processing yet.", "info")
        return redirect(url_for("main.boardroom_execution", scenario_id=scenario_id))

    action = request.form.get("action", "")
    status = VALID_APPROVAL_ACTIONS.get(action)
    if not status:
        flash("❓ Unknown approval action.", "error")
        return redirect(url_for("main.ceo_page", scenario_id=scenario_id))

    try:
        approved_pct = float(request.form.get("approved_budget_percent") or 0)
    except ValueError:
        approved_pct = 0.0
    approved_pct = max(0.0, min(100.0, approved_pct))

    user = current_user()
    decision.approval_status = status
    decision.approved_by = (request.form.get("approved_by", "").strip()
                            or (user.name if user else "Unknown"))
    decision.approver_role = (request.form.get("approver_role", "").strip()
                              or decision.approver_role or "CEO")
    decision.approval_note = request.form.get("approval_note", "").strip()
    decision.approved_budget_percent = 0.0 if status == "rejected" else approved_pct
    decision.approved_at = datetime.utcnow()
    db.session.commit()

    label = decision.approval_label[0]
    flash(f"{decision.approval_label[2]} Decision recorded: {label}.", "success")
    return redirect(url_for("main.ceo_page", scenario_id=scenario_id))


# ---------------------------------------------------------------- Report ---
@main_bp.route("/decision/<int:scenario_id>/report")
@login_required
def report_page(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    decision = scenario.decision
    if not decision:
        flash("⏳ This decision has not finished processing yet.", "info")
        return redirect(url_for("main.boardroom_execution", scenario_id=scenario_id))
    ctx = build_report_context(scenario, decision)
    return render_template("final_report.html", **ctx)


@main_bp.route("/decision/<int:scenario_id>/report/download")
@login_required
def report_download(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    decision = scenario.decision
    if not decision:
        flash("⏳ The report isn't ready to download yet — the board is still deliberating.", "info")
        return redirect(url_for("main.boardroom_execution", scenario_id=scenario_id))
    pdf_bytes = generate_pdf_report(scenario, decision)
    filename = f"boardroom_report_{scenario_id}.pdf"
    return send_file(BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


# --------------------------------------------------------------- What-If ---
@main_bp.route("/decision/<int:scenario_id>/what-if", methods=["GET", "POST"])
@login_required
def what_if_page(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    decision = scenario.decision
    if not decision:
        flash("⏳ This decision has not finished processing yet.", "info")
        return redirect(url_for("main.boardroom_execution", scenario_id=scenario_id))

    risk = scenario.result_data("risk")
    marketing = scenario.get_result("marketing")
    operations = scenario.get_result("operations")

    # Retrieve user input from session if previously entered, else fallback to scenario baseline
    saved_inputs = session.get(f"what_if_{scenario_id}", {})
    current_investment = saved_inputs.get("investment", scenario.investment)
    current_revenue = saved_inputs.get("expected_revenue", scenario.expected_revenue)
    current_operating_cost = saved_inputs.get("operating_cost", scenario.operating_cost)
    scenario_name = saved_inputs.get("scenario_name", "")

    if request.method == "POST":
        try:
            val_inv = request.form.get("investment")
            val_rev = request.form.get("expected_revenue")
            val_cost = request.form.get("operating_cost")
            scenario_name = request.form.get("scenario_name", "").strip()

            current_investment = float(val_inv if val_inv is not None and val_inv != "" else scenario.investment)
            current_revenue = float(val_rev if val_rev is not None and val_rev != "" else scenario.expected_revenue)
            current_operating_cost = float(val_cost if val_cost is not None and val_cost != "" else scenario.operating_cost)

            session[f"what_if_{scenario_id}"] = {
                "investment": current_investment,
                "expected_revenue": current_revenue,
                "operating_cost": current_operating_cost,
                "scenario_name": scenario_name,
            }
        except ValueError:
            flash("🔢 Please enter valid numbers.", "error")
            return redirect(url_for("main.what_if_page", scenario_id=scenario_id))

    # Check if we have modified/custom user input
    has_custom_inputs = (
        abs(float(current_investment) - float(scenario.investment or 0)) > 1e-6 or
        abs(float(current_revenue) - float(scenario.expected_revenue or 0)) > 1e-6 or
        abs(float(current_operating_cost) - float(scenario.operating_cost or 0)) > 1e-6 or
        bool(scenario_name) or
        request.method == "POST"
    )

    # Always compute result so recommendation, charts, and table are ALWAYS displayed
    result = run_what_if(
        scenario, decision, risk, decision.strategic_fit_score,
        marketing.score if marketing else 50, operations.score if operations else 50,
        current_app.config.get("SCORE_WEIGHTS"),
        new_investment=current_investment, new_revenue=current_revenue,
        new_operating_cost=current_operating_cost,
        scenario_name=scenario_name,
    )

    sensitivity = run_sensitivity(scenario, decision, risk, marketing, operations)

    current_inputs = {
        "investment": current_investment,
        "expected_revenue": current_revenue,
        "operating_cost": current_operating_cost,
        "scenario_name": scenario_name,
    }

    return render_template("what_if.html", scenario=scenario, decision=decision,
                           result=result, sensitivity=sensitivity,
                           current_inputs=current_inputs, has_custom_inputs=has_custom_inputs)


@main_bp.route("/decision/<int:scenario_id>/what-if/reset", methods=["POST", "GET"])
@login_required
def what_if_reset(scenario_id):
    _owned_scenario_or_404(scenario_id)
    session.pop(f"what_if_{scenario_id}", None)
    flash("↺ Reset What-If numbers to baseline scenario.", "info")
    return redirect(url_for("main.what_if_page", scenario_id=scenario_id))


def run_sensitivity(scenario, decision, risk, marketing, operations):
    """Sweeps revenue from -40% to +40% so the page can show a sensitivity
    curve without the user having to submit the form repeatedly."""
    weights = current_app.config.get("SCORE_WEIGHTS")
    labels, scores, profits = [], [], []
    for delta in range(-40, 41, 10):
        revenue = float(scenario.expected_revenue or 0) * (1 + delta / 100.0)
        outcome = run_what_if(
            scenario, decision, risk, decision.strategic_fit_score,
            marketing.score if marketing else 50, operations.score if operations else 50,
            weights, new_revenue=revenue,
        )
        labels.append(f"{delta:+d}%")
        scores.append(outcome["what_if_case"]["score"])
        profits.append(outcome["what_if_case"]["profit"])
    return {"labels": labels, "scores": scores, "profits": profits}


# ---------------------------------------------------------------- History --
@main_bp.route("/history")
@login_required
def history():
    scenarios = Scenario.query.filter_by(user_id=session["user_id"]).order_by(
        Scenario.created_at.desc()).all()
    return render_template("history.html", scenarios=scenarios)


@main_bp.route("/decision/<int:scenario_id>/delete", methods=["POST"])
@login_required
def delete_scenario(scenario_id):
    scenario = _owned_scenario_or_404(scenario_id)
    title = scenario.title
    from routes.api_routes import _running_lock, _running_scenarios
    with _running_lock:
        _running_scenarios.discard(scenario_id)
    session.pop(f"what_if_{scenario_id}", None)
    db.session.delete(scenario)
    db.session.commit()
    flash(f"🗑️ Decision '{title}' deleted successfully.", "success")
    return redirect(url_for("main.history"))


# --------------------------------------------------------------- Settings --
@main_bp.route("/settings")
@login_required
def settings():
    user = current_user()
    return render_template("settings.html", user=user)
