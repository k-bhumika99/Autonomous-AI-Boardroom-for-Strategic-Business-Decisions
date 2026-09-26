"""Pydantic schemas used to validate every agent's structured output.

We never trust raw LLM text. Every Gemini call is bound to one of these
schemas via LangChain's structured-output support, and re-validated here.

Design rule: the LLM returns ASSUMPTIONS (growth rates, budget split
percentages, conversion rates, phase durations, probabilities). Every number
that ends up on a chart axis is then computed in services/projections.py.
"""
from typing import List
from pydantic import BaseModel, Field, field_validator

RECOMMENDATION_VALUES = {
    "STRONGLY RECOMMEND", "RECOMMEND", "RECOMMEND WITH CONDITIONS",
    "DELAY", "DO NOT PROCEED", "REVIEW / DELAY",
}


def _clamp_severity(v: str) -> str:
    v = (v or "MEDIUM").upper().strip()
    return v if v in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "MEDIUM"


# ===========================================================================
# 1. Planner Agent — understands the request and plans the work
# ===========================================================================

class SuccessMetric(BaseModel):
    metric: str
    target: str = ""
    why_it_matters: str = ""


class PlanPhase(BaseModel):
    phase: str
    what_to_do: str = ""
    how_to_do_it: str = ""
    start_month: float = 0
    duration_months: float = 1
    owner: str = "Unassigned"
    deliverables: List[str] = []
    exit_criteria: str = ""
    risk_level: str = "MEDIUM"

    @field_validator("risk_level")
    @classmethod
    def _sev(cls, v):
        return _clamp_severity(v)


class BudgetLine(BaseModel):
    category: str
    percent: float = Field(default=0, ge=0, le=100)
    note: str = ""


class PlannerOutput(BaseModel):
    agent_name: str = "Planner Agent"
    understood_request: str = ""
    business_objective: str = ""
    decision_type: str = "New initiative"
    complexity: str = "MEDIUM"
    readiness_score: float = Field(default=50, ge=0, le=100)
    confidence: float = Field(default=0.7, ge=0, le=1)

    scope_included: List[str] = []
    scope_excluded: List[str] = []
    open_questions: List[str] = []
    critical_assumptions: List[str] = []

    success_metrics: List[SuccessMetric] = []
    phases: List[PlanPhase] = []
    budget_allocation: List[BudgetLine] = []

    recommended_approach: str = ""
    immediate_next_steps: List[str] = []
    reasoning: str = ""

    @field_validator("complexity")
    @classmethod
    def _cx(cls, v):
        v = (v or "MEDIUM").upper().strip()
        return v if v in {"LOW", "MEDIUM", "HIGH"} else "MEDIUM"


# ===========================================================================
# 2. Finance Agent
# ===========================================================================

class KPI(BaseModel):
    name: str
    value: str = ""
    trend: str = "flat"   # up / down / flat
    comment: str = ""


class FinanceOutput(BaseModel):
    agent_name: str = "Finance Agent"
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    recommendation: str

    # Assumptions the deterministic projection engine consumes
    revenue_growth_percent: float = Field(default=20, ge=-50, le=300)
    cost_growth_percent: float = Field(default=10, ge=-50, le=200)
    optimistic_multiplier: float = Field(default=1.25, ge=1.0, le=3.0)
    pessimistic_multiplier: float = Field(default=0.7, ge=0.1, le=1.0)
    budget_allocation: List[BudgetLine] = []

    key_findings: List[str] = []
    profit_drivers: List[str] = []
    loss_drivers: List[str] = []
    cost_optimizations: List[str] = []
    funding_recommendations: List[str] = []
    kpis: List[KPI] = []
    risks: List[str] = []
    assumptions: List[str] = []
    evidence: List[str] = []
    reasoning: str = ""


# ===========================================================================
# 3. Marketing Agent
# ===========================================================================

class MarketingChannel(BaseModel):
    name: str
    budget_share_percent: float = Field(default=0, ge=0, le=100)
    expected_cac: float = Field(default=0, ge=0)
    expected_conversion_percent: float = Field(default=0, ge=0, le=100)
    note: str = ""


class FunnelStage(BaseModel):
    stage: str
    conversion_percent: float = Field(default=100, ge=0.1, le=100)
    note: str = ""


class Segment(BaseModel):
    segment: str
    share_percent: float = Field(default=0, ge=0, le=100)
    why: str = ""


class MarketingOutput(BaseModel):
    agent_name: str = "Marketing Agent"
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    recommendation: str

    positioning_statement: str = ""
    pricing_recommendation: str = ""
    year_one_growth_percent: float = Field(default=30, ge=-50, le=500)
    marketing_budget_share_percent: float = Field(default=20, ge=0, le=80)

    segments: List[Segment] = []
    channels: List[MarketingChannel] = []
    funnel: List[FunnelStage] = []
    growth_levers: List[str] = []

    key_findings: List[str] = []
    opportunities: List[str] = []
    risks: List[str] = []
    assumptions: List[str] = []
    evidence: List[str] = []
    reasoning: str = ""


# ===========================================================================
# 4. Operations Agent
# ===========================================================================

class ResourceLine(BaseModel):
    role: str
    headcount: float = Field(default=1, ge=0, le=500)
    monthly_cost: float = Field(default=0, ge=0)
    note: str = ""


class ReadinessDimension(BaseModel):
    dimension: str
    score: float = Field(default=50, ge=0, le=100)
    comment: str = ""


class OperationsOutput(BaseModel):
    agent_name: str = "Operations Agent"
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    recommendation: str

    timeline_realism: str = "REALISTIC"      # REALISTIC / TIGHT / UNREALISTIC
    recommended_timeline_months: float = Field(default=6, ge=1, le=60)

    phases: List[PlanPhase] = []
    resource_plan: List[ResourceLine] = []
    readiness: List[ReadinessDimension] = []

    key_findings: List[str] = []
    resource_requirements: List[str] = []
    bottlenecks: List[str] = []
    dependencies: List[str] = []
    risks: List[str] = []
    assumptions: List[str] = []
    reasoning: str = ""

    @field_validator("timeline_realism")
    @classmethod
    def _tr(cls, v):
        v = (v or "REALISTIC").upper().strip()
        return v if v in {"REALISTIC", "TIGHT", "UNREALISTIC"} else "REALISTIC"


# ===========================================================================
# 5. Risk Agent
# ===========================================================================

class RiskItem(BaseModel):
    risk: str
    category: str = "General"
    severity: str = Field(default="MEDIUM")
    probability_percent: float = Field(default=50, ge=0, le=100)
    impact_percent: float = Field(default=50, ge=0, le=100)
    financial_exposure_percent: float = Field(default=10, ge=0, le=100)
    early_warning_signal: str = ""
    mitigation: List[str] = []

    @field_validator("severity")
    @classmethod
    def check_severity(cls, v):
        return _clamp_severity(v)


class RiskOutput(BaseModel):
    agent_name: str = "Risk Agent"
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    recommendation: str
    overall_risk_level: str = "MEDIUM"
    risks: List[RiskItem] = []
    opportunities_balance: str = ""
    contingency_percent_recommended: float = Field(default=10, ge=0, le=50)
    deal_breakers: List[str] = []
    reasoning: str = ""

    @field_validator("overall_risk_level")
    @classmethod
    def _orl(cls, v):
        return _clamp_severity(v)


# ===========================================================================
# 6. Debate / Review Agent
# ===========================================================================

class DebateOutput(BaseModel):
    summary: str = ""
    agreements: List[str] = []
    disagreements: List[str] = []
    contradictions: List[str] = []
    strongest_arguments_for: List[str] = []
    strongest_arguments_against: List[str] = []
    resolution: List[str] = []
    consensus: str = ""
    consensus_strength_percent: float = Field(default=60, ge=0, le=100)


class StrategicFitOutput(BaseModel):
    score: float = Field(ge=0, le=100)
    alignment_notes: str = ""
    is_ai_assessment: bool = True


# ===========================================================================
# 7. CEO Agent — the approval authority
# ===========================================================================

class ReviewCheckpoint(BaseModel):
    checkpoint: str
    when: str = ""
    go_no_go_criteria: str = ""


class CEOOutput(BaseModel):
    should_proceed: str  # yes/no/conditional
    recommendation: str
    approver_role: str = "CEO"
    approved_budget_percent: float = Field(default=100, ge=0, le=100)
    reasoning: str = ""
    strongest_reasons: List[str] = []
    biggest_concerns: List[str] = []
    conditions_required: List[str] = []
    next_actions: List[str] = []
    review_checkpoints: List[ReviewCheckpoint] = []
    kpis_to_track: List[str] = []
    assumptions_that_change_decision: List[str] = []

    @field_validator("recommendation")
    @classmethod
    def check_rec(cls, v):
        return (v or "").upper().strip()


class DecisionReportOutput(BaseModel):
    executive_summary: str = ""
    action_plan: List[str] = []
    what_if_insights: List[str] = []
    ninety_day_plan: List[str] = []
    final_conclusion: str = ""
