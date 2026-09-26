"""Database models for the Autonomous AI Boardroom."""
import json
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from database import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), default="Founder")   # Founder / CEO / Manager / Team Lead
    company = db.Column(db.String(160))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scenarios = db.relationship("Scenario", backref="user", lazy=True,
                                cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Scenario(db.Model):
    __tablename__ = "scenario"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    investment = db.Column(db.Float, default=0.0)
    expected_revenue = db.Column(db.Float, default=0.0)
    operating_cost = db.Column(db.Float, default=0.0)
    target_market = db.Column(db.String(200))
    expected_customers = db.Column(db.Integer, default=0)
    timeline = db.Column(db.String(120))
    additional_information = db.Column(db.Text)

    # Context that materially improves the quality of the plan
    industry = db.Column(db.String(120))
    business_model = db.Column(db.String(120))     # SaaS / Marketplace / Services / D2C ...
    decision_owner = db.Column(db.String(120))     # who signs this off

    status = db.Column(db.String(30), default="pending")          # pending/running/completed/completed_with_errors/failed
    current_stage = db.Column(db.String(60), default="created")   # see static/js/boardroom.js STAGE_ORDER
    errors = db.Column(db.Text, default="[]")                     # JSON list of human-readable error strings

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    agent_results = db.relationship("AgentResult", backref="scenario", lazy=True,
                                    cascade="all, delete-orphan")
    debate = db.relationship("Debate", backref="scenario", uselist=False,
                             cascade="all, delete-orphan")
    decision = db.relationship("Decision", backref="scenario", uselist=False,
                               cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_result(self, agent_name):
        """agent_name: 'planner' | 'finance' | 'marketing' | 'operations' | 'risk'."""
        target = agent_name.strip().lower()
        for r in self.agent_results:
            if r.agent_name.strip().lower().startswith(target):
                return r
        return None

    def result_data(self, agent_name):
        r = self.get_result(agent_name)
        return r.data() if r else {}

    def get_errors(self):
        try:
            return json.loads(self.errors) if self.errors else []
        except (TypeError, json.JSONDecodeError):
            return []

    def add_error(self, message):
        errs = self.get_errors()
        errs.append(message)
        self.errors = json.dumps(errs)

    @property
    def is_done(self):
        return self.status in ("completed", "completed_with_errors")

    @property
    def profit(self):
        return (self.expected_revenue or 0) - (self.investment or 0) - (self.operating_cost or 0)


class AgentResult(db.Model):
    __tablename__ = "agent_result"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("scenario.id"), nullable=False, index=True)
    agent_name = db.Column(db.String(60), nullable=False)  # "finance" / "marketing" / ...
    score = db.Column(db.Float, default=0.0)
    confidence = db.Column(db.Float, default=0.0)
    recommendation = db.Column(db.String(255))
    analysis = db.Column(db.Text)  # JSON blob of the full structured agent output
    status = db.Column(db.String(20), default="completed")  # completed/failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def data(self):
        try:
            return json.loads(self.analysis) if self.analysis else {}
        except (TypeError, json.JSONDecodeError):
            return {}


class Debate(db.Model):
    __tablename__ = "debate"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("scenario.id"), nullable=False, index=True)
    summary = db.Column(db.Text)
    agreements = db.Column(db.Text)
    disagreements = db.Column(db.Text)
    contradictions = db.Column(db.Text)
    strongest_for = db.Column(db.Text)
    strongest_against = db.Column(db.Text)
    resolution = db.Column(db.Text)
    consensus = db.Column(db.Text)
    consensus_strength = db.Column(db.Float, default=60.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        def _l(v):
            try:
                return json.loads(v) if v else []
            except (TypeError, json.JSONDecodeError):
                return []
        return {
            "summary": self.summary or "",
            "agreements": _l(self.agreements),
            "disagreements": _l(self.disagreements),
            "contradictions": _l(self.contradictions),
            "strongest_for": _l(self.strongest_for),
            "strongest_against": _l(self.strongest_against),
            "resolution": _l(self.resolution),
            "consensus": self.consensus or "",
            "consensus_strength": self.consensus_strength or 0,
        }


class Decision(db.Model):
    __tablename__ = "decision"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey("scenario.id"), nullable=False, index=True)
    weighted_score = db.Column(db.Float, default=0.0)
    strategic_fit_score = db.Column(db.Float, default=0.0)
    final_recommendation = db.Column(db.String(60))
    ceo_reasoning = db.Column(db.Text)
    ceo_result = db.Column(db.Text)    # JSON blob (full CEOOutput)
    final_report = db.Column(db.Text)  # JSON blob (full executive report)

    # ---- Human sign-off ---------------------------------------------------
    # The AI CEO proposes; a real person (CEO / manager / team lead) approves.
    approval_status = db.Column(db.String(30), default="awaiting_approval")
    # awaiting_approval / approved / approved_with_conditions / rejected / sent_back
    approver_role = db.Column(db.String(60), default="CEO")
    approved_by = db.Column(db.String(120))
    approval_note = db.Column(db.Text)
    approved_budget_percent = db.Column(db.Float, default=0.0)
    approved_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    APPROVAL_LABELS = {
        "awaiting_approval": ("Awaiting sign-off", "badge-review", "⏳"),
        "approved": ("Approved", "badge-strong", "✅"),
        "approved_with_conditions": ("Approved with conditions", "badge-conditions", "📝"),
        "rejected": ("Rejected", "badge-reject", "⛔"),
        "sent_back": ("Sent back for rework", "badge-review", "↩️"),
    }

    def ceo_data(self):
        try:
            return json.loads(self.ceo_result) if self.ceo_result else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def report_data(self):
        try:
            return json.loads(self.final_report) if self.final_report else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    @property
    def approval_label(self):
        return self.APPROVAL_LABELS.get(
            self.approval_status or "awaiting_approval",
            ("Awaiting sign-off", "badge-review", "⏳"),
        )
