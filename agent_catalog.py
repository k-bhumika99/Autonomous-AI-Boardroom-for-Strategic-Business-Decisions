"""Agent Catalog — complete profiles and metadata for all 7 AI Boardroom agents.

Corresponds exactly to the boardroom reference layout:
1. Planner Agent (Strategic Planning)
2. Finance Agent (Financial Analysis)
3. Marketing Agent (Market Analysis)
4. Operations Agent (Operational Feasibility)
5. Risk Agent (Risk Assessment)
6. Debate Agent (Discussion & Consensus)
7. CEO Agent (Strategic Review)
"""

AGENTS_CATALOG = {
    "planner": {
        "key": "planner",
        "name": "Planner Agent",
        "role": "Strategic Planning",
        "icon": "📅",
        "color_theme": "purple",
        "bg_gradient": "linear-gradient(180deg, #F8F6FF 0%, #FFFFFF 100%)",
        "border_color": "#E9E3FC",
        "badge_bg": "#EFEAFC",
        "badge_color": "#6338C7",
        "icon_bg": "#EDE7FE",
        "tagline": "Defines scope, phases, what/how/when, and budget split for your decision.",
        "board_title": "Project Plan",
        "checklist": ["Scope", "Timeline", "Resources", "Milestones"],
        "focus_tags": ["STRATEGY", "PLANNING", "EXECUTION"],
        "summary": "The Planner Agent translates ambiguous business directives into disciplined, stage-gated implementation architectures. It maps dependencies, defines critical paths, and allocates timelines so the board can execute with predictable velocity.",
        "workflow": [
            {"step": "1", "title": "Scope Deconstruction", "desc": "Analyzes the business scenario objectives, identifying core deliverables and operational boundaries."},
            {"step": "2", "title": "Milestone & Phase Mapping", "desc": "Structures rollout into distinct milestones with quantifiable completion criteria."},
            {"step": "3", "title": "Critical Path & Dependency Analysis", "desc": "Maps cross-functional prerequisites to detect sequence bottlenecks early."},
            {"step": "4", "title": "Phased Budget Distribution", "desc": "Recommends budget allocation curve across early research, MVP launch, and scale phases."}
        ],
        "methodologies": [
            {"title": "Agile Stage-Gate Framework", "desc": "Breaks major initiatives into discovery, prototype, validation, and expansion gates with go/no-go criteria.", "icon": "🚪"},
            {"title": "Critical Path Method (CPM)", "desc": "Calculates earliest and latest event times to optimize the total critical sequence duration.", "icon": "⚡"},
            {"title": "Resource Leveling", "desc": "Balances team capacity against deliverables to avoid burnout and scheduling collisions.", "icon": "⚖️"}
        ],
        "deliverables": [
            "Comprehensive 4-phase execution roadmap with target deadlines",
            "Deliverable checklist with clear ownership and success metrics",
            "Cross-departmental dependency matrix",
            "Staged budget drawdown schedule tied to milestone signoffs"
        ],
        "kpi_benchmarks": [
            {"label": "Project Horizons", "value": "3 Execution Phases", "tone": "mint"},
            {"label": "Milestones Defined", "value": "8 Checkpoints", "tone": "mint"},
            {"label": "Dependency Safety", "value": "94% Clean Paths", "tone": "mint"},
            {"label": "Resource Fit", "value": "Optimized", "tone": "mint"}
        ]
    },

    "finance": {
        "key": "finance",
        "name": "Finance Agent",
        "role": "Financial Analysis",
        "icon": "🪙",
        "color_theme": "emerald",
        "bg_gradient": "linear-gradient(180deg, #F0FDF8 0%, #FFFFFF 100%)",
        "border_color": "#D3F5E6",
        "badge_bg": "#D9F6E8",
        "badge_color": "#0E7E5A",
        "icon_bg": "#E3F9EE",
        "tagline": "Analyzes budget, ROI, profit & loss, and 3-year financial projections.",
        "board_title": "Financial Overview",
        "checklist": ["Revenue", "Expenses", "Profit", "ROI", "3 Year Forecast"],
        "focus_tags": ["BUDGET", "FORECAST", "INVESTMENT", "PROFITABILITY"],
        "summary": "The Finance Agent applies quantitative corporate finance models to measure viability, calculate internal rates of return, project 36-month P&L statements, and safeguard cash runway before capital is deployed.",
        "workflow": [
            {"step": "1", "title": "Capital Requirement Auditing", "desc": "Validates upfront investment requests against realistic market cost benchmarks."},
            {"step": "2", "title": "Unit Economics Modeling", "desc": "Analyzes margin contribution, operating expenditure, and per-customer revenue models."},
            {"step": "3", "title": "Multi-Year Projection Engine", "desc": "Runs discounted cash flow models forecasting Year 1 through Year 3 revenue and EBITDA."},
            {"step": "4", "title": "ROI & Break-Even Determination", "desc": "Calculates expected payback horizon, capital efficiency ratio, and investment score."}
        ],
        "methodologies": [
            {"title": "Discounted Cash Flow (DCF)", "desc": "Projects future cash flows discounted back to present value using industry cost of capital.", "icon": "💵"},
            {"title": "Unit Economics & Margin Analysis", "desc": "Calculates contribution margin after direct acquisition and operational costs.", "icon": "📊"},
            {"title": "Sensitivity & Scenario Modeling", "desc": "Tests financial resilience against ±20% and ±40% revenue deviations.", "icon": "📉"}
        ],
        "deliverables": [
            "3-Year detailed pro-forma revenue, cost, and net profit projections",
            "Break-even timeline and cash runway buffer calculation",
            "Projected ROI percentage and capital efficiency index",
            "Cost-to-income sensitivity table under varying market adoption rates"
        ],
        "kpi_benchmarks": [
            {"label": "Projected ROI", "value": "140% – 280%", "tone": "mint"},
            {"label": "Break-Even Horizon", "value": "8 – 14 Months", "tone": "mint"},
            {"label": "Profit Margin", "value": "32% Net Target", "tone": "mint"},
            {"label": "Capital Efficiency", "value": "2.4x Multiple", "tone": "mint"}
        ]
    },

    "marketing": {
        "key": "marketing",
        "name": "Marketing Agent",
        "role": "Market Analysis",
        "icon": "📢",
        "color_theme": "coral",
        "bg_gradient": "linear-gradient(180deg, #FFF4F2 0%, #FFFFFF 100%)",
        "border_color": "#FFE3DC",
        "badge_bg": "#FFEBE6",
        "badge_color": "#C43823",
        "icon_bg": "#FFEAE5",
        "tagline": "Analyzes growth curve, channels, funnel, CAC & LTV to identify market opportunities.",
        "board_title": "Marketing Strategy",
        "checklist": ["Awareness", "Consideration", "Conversion", "Retention"],
        "focus_tags": ["BRAND", "CAMPAIGN", "GROWTH"],
        "summary": "The Marketing Agent evaluates go-to-market channels, customer acquisition economics, audience demand curves, and brand differentiation to ensure sustainable commercial traction.",
        "workflow": [
            {"step": "1", "title": "Market Opportunity Sizing", "desc": "Calculates Total Addressable Market (TAM) and Serviceable Obtainable Market (SOM)."},
            {"step": "2", "title": "Funnel Optimization Modeling", "desc": "Simulates conversion velocity across Awareness, Consideration, Conversion, and Retention."},
            {"step": "3", "title": "CAC & LTV Econometrics", "desc": "Assesses paid vs organic acquisition costs and projects customer lifetime customer value."},
            {"step": "4", "title": "Omnichannel Campaign Mix", "desc": "Prioritizes high-leverage acquisition channels: Content, Performance, Partnerships, and ABM."}
        ],
        "methodologies": [
            {"title": "Full-Funnel Growth Modeling", "desc": "Optimizes top-of-funnel reach down to post-purchase advocacy and expansion loops.", "icon": "🎯"},
            {"title": "CAC-to-LTV Cohort Analysis", "desc": "Enforces minimum 3:1 LTV:CAC threshold for healthy unit economics.", "icon": "📈"},
            {"title": "Value Proposition Resonance", "desc": "Benchmarks brand positioning against incumbent alternatives to secure differentiation.", "icon": "🏷️"}
        ],
        "deliverables": [
            "Target customer persona dossiers with pain points and buying triggers",
            "Omnichannel marketing budget distribution across primary channels",
            "Projected funnel conversion ratios and acquisition cost targets",
            "Competitive differentiation and messaging battlecard"
        ],
        "kpi_benchmarks": [
            {"label": "LTV : CAC Target", "value": "3.5x Ratio", "tone": "mint"},
            {"label": "Conversion Rate", "value": "3.8% Benchmark", "tone": "mint"},
            {"label": "Payback on CAC", "value": "< 5 Months", "tone": "mint"},
            {"label": "Organic Share", "value": "45% by Month 6", "tone": "mint"}
        ]
    },

    "operations": {
        "key": "operations",
        "name": "Operations Agent",
        "role": "Operational Feasibility",
        "icon": "⚙️",
        "color_theme": "blue",
        "bg_gradient": "linear-gradient(180deg, #F1F7FF 0%, #FFFFFF 100%)",
        "border_color": "#D5E7FC",
        "badge_bg": "#DFEFFE",
        "badge_color": "#1C66BF",
        "icon_bg": "#E1EFFF",
        "tagline": "Evaluates roadmap, staffing, readiness, and infrastructure bottlenecks.",
        "board_title": "Operations Readiness",
        "checklist": ["Resources", "Infrastructure", "Process Flow", "Team Readiness", "Timeline"],
        "focus_tags": ["SMOOTH OPERATIONS", "STRONGER OUTCOMES"],
        "summary": "The Operations Agent stress-tests operational capabilities, team staffing capacities, vendor dependencies, and tech stack scalability to ensure ideas can be reliably executed.",
        "workflow": [
            {"step": "1", "title": "Capacity & Staffing Audit", "desc": "Measures existing headcount, critical skills gaps, and recruitment lead times."},
            {"step": "2", "title": "Infrastructure Readiness Review", "desc": "Validates cloud systems, software tooling, and security compliance readiness."},
            {"step": "3", "title": "Workflow Bottleneck Simulation", "desc": "Identifies process handoff delays and operational friction points across teams."},
            {"step": "4", "title": "SLA & Quality Control Architecture", "desc": "Establishes operational KPIs, incident protocols, and service level targets."}
        ],
        "methodologies": [
            {"title": "Theory of Constraints (TOC)", "desc": "Identifies the single most restrictive operational bottleneck and designs mitigations.", "icon": "⛓️"},
            {"title": "RACI Matrix Allocation", "desc": "Defines who is Responsible, Accountable, Consulted, and Informed for every deliverable.", "icon": "👥"},
            {"title": "Scalability Stress Testing", "desc": "Models operational stability under 5x to 10x customer volume surges.", "icon": "🚀"}
        ],
        "deliverables": [
            "Operational readiness audit score and gap remediation list",
            "Staffing requirements roadmap with hiring priority tiers",
            "Infrastructure and tooling requirement specifications",
            "Service level agreement (SLA) framework and quality gates"
        ],
        "kpi_benchmarks": [
            {"label": "Readiness Score", "value": "86 / 100", "tone": "mint"},
            {"label": "Staffing Gap", "value": "3 Key Hires Needed", "tone": "coral"},
            {"label": "Process Velocity", "value": "Optimized", "tone": "mint"},
            {"label": "System Uptime SLA", "value": "99.9% Target", "tone": "mint"}
        ]
    },

    "risk": {
        "key": "risk",
        "name": "Risk Agent",
        "role": "Risk Assessment",
        "icon": "🛡️",
        "color_theme": "rose",
        "bg_gradient": "linear-gradient(180deg, #FFF3F3 0%, #FFFFFF 100%)",
        "border_color": "#FFDADA",
        "badge_bg": "#FFE3E3",
        "badge_color": "#C42929",
        "icon_bg": "#FFE8E8",
        "tagline": "Uses probability × impact matrix to identify risks and suggests mitigation strategies.",
        "board_title": "Risk Matrix",
        "checklist": ["Identify Risks", "Assess Impact", "Mitigation Plan", "Monitor & Track"],
        "focus_tags": ["COMPLIANCE", "SECURITY", "BUSINESS CONTINUITY"],
        "summary": "The Risk Agent acts as the analytical guardian of the boardroom. It searches for blind spots, scores likelihood versus financial impact, and constructs contingency plans before risks materialize.",
        "workflow": [
            {"step": "1", "title": "Threat Vector Scanning", "desc": "Catalogs market, financial, legal/compliance, and execution hazards."},
            {"step": "2", "title": "Probability × Impact Scoring", "desc": "Plots each hazard on a calibrated 3×3 matrix to classify severity."},
            {"step": "3", "title": "Contingency & Mitigation Design", "desc": "Formulates proactive safeguards and early warning trigger indicators."},
            {"step": "4", "title": "Residual Exposure Monitoring", "desc": "Measures net risk exposure after mitigations are deployed."}
        ],
        "methodologies": [
            {"title": "3×3 Probability × Impact Matrix", "desc": "Quantifies threat severity across Low, Medium, High, and Critical thresholds.", "icon": "⚠️"},
            {"title": "Failure Mode & Effects Analysis (FMEA)", "desc": "Pinpoints single points of failure and calculates Risk Priority Numbers (RPN).", "icon": "🔍"},
            {"title": "Business Continuity Planning (BCP)", "desc": "Establishes fallback procedures to maintain core revenue streams during disruptions.", "icon": "🛡️"}
        ],
        "deliverables": [
            "Calibrated 3×3 Risk Matrix with plotted high-exposure threats",
            "Detailed risk register with likelihood, impact, and mitigation protocols",
            "Early warning trigger metrics and contingency action plans",
            "Executive compliance & downside exposure summary"
        ],
        "kpi_benchmarks": [
            {"label": "Max Risk Exposure", "value": "Medium / Controlled", "tone": "mint"},
            {"label": "Critical Vulnerabilities", "value": "0 Unmitigated", "tone": "mint"},
            {"label": "Mitigation Coverage", "value": "100% Top Risks", "tone": "mint"},
            {"label": "Compliance Index", "value": "High Confidence", "tone": "mint"}
        ]
    },

    "debate": {
        "key": "debate",
        "name": "Debate Agent",
        "role": "Discussion & Consensus",
        "icon": "💬",
        "color_theme": "violet",
        "bg_gradient": "linear-gradient(180deg, #F5F3FF 0%, #FFFFFF 100%)",
        "border_color": "#E5DEFC",
        "badge_bg": "#EBE5FD",
        "badge_color": "#5834D1",
        "icon_bg": "#ECE5FE",
        "tagline": "Facilitates multi-agent discussion, highlights conflicting perspectives, and helps reach consensus.",
        "board_title": "Discussion & Consensus",
        "checklist": ["Let's discuss...", "Different perspectives", "Consider the trade-offs", "Find the best option"],
        "focus_tags": ["BETTER QUESTIONS", "BETTER DECISIONS"],
        "summary": "The Debate Agent orchestrates structured adversarial deliberations. It pits optimistic market assumptions against conservative financial models and operational realities to find genuine consensus.",
        "workflow": [
            {"step": "1", "title": "Perspective Extraction", "desc": "Extracts conflicting hypotheses from Planner, Finance, Marketing, and Risk findings."},
            {"step": "2", "title": "Dialectic Cross-Examination", "desc": "Simulates cross-agent debate rounds where each domain challenges the others' assumptions."},
            {"step": "3", "title": "Trade-Off Arbitration", "desc": "Quantifies the compromises required between speed, margin, and risk mitigation."},
            {"step": "4", "title": "Synthesized Consensus Formulation", "desc": "Distills resolved points into unified recommendations for executive signoff."}
        ],
        "methodologies": [
            {"title": "Dialectic Deliberation (Thesis / Antithesis)", "desc": "Systematically tests propositions against strong counter-arguments to uncover truth.", "icon": "⚖️"},
            {"title": "Multi-Agent Cross-Validation", "desc": "Forces cross-checks (e.g. Marketing customer acquisition budget vs Finance runway).", "icon": "🔄"},
            {"title": "Consensus Scoring Engine", "desc": "Measures alignment percentage across domain agents to identify unresolved friction.", "icon": "🤝"}
        ],
        "deliverables": [
            "Complete multi-round transcript of cross-agent boardroom debate",
            "Key tensions & resolutions summary highlighting agreed trade-offs",
            "Alignment index measuring consensus across domain agents",
            "Consensus-backed strategic directives presented to the CEO"
        ],
        "kpi_benchmarks": [
            {"label": "Debate Rounds", "value": "3 Deliberations", "tone": "mint"},
            {"label": "Tensions Resolved", "value": "4 Core Trade-offs", "tone": "mint"},
            {"label": "Consensus Index", "value": "88% Board Alignment", "tone": "mint"},
            {"label": "Blind Spots Uncovered", "value": "3 Key Findings", "tone": "mint"}
        ]
    },

    "ceo": {
        "key": "ceo",
        "name": "CEO Agent",
        "role": "Strategic Review",
        "icon": "👑",
        "color_theme": "amber",
        "bg_gradient": "linear-gradient(180deg, #FFFDF0 0%, #FFFFFF 100%)",
        "border_color": "#F7EFC2",
        "badge_bg": "#FDF0C6",
        "badge_color": "#946300",
        "icon_bg": "#FCF1CA",
        "tagline": "Synthesizes all insights, evaluates trade-offs, and provides the final strategic decision with clear action points.",
        "board_title": "Final Decision",
        "checklist": ["Key Findings", "Strategic Options", "Recommended Action", "Next Steps"],
        "focus_tags": ["STRATEGIC DECISIONS CREATE BRIGHTER TOMORROWS"],
        "summary": "The CEO Agent reviews the totality of boardroom findings, weighs executive trade-offs, and delivers the authoritative strategic decision — complete with staged budget release gates and human signoff workflow.",
        "workflow": [
            {"step": "1", "title": "Holistic Intelligence Synthesis", "desc": "Ingests ratings, data models, and debate transcripts from all 6 prior agents."},
            {"step": "2", "title": "Weighted Scoring Evaluation", "desc": "Applies proprietary boardroom weights to calculate composite Strategic Fit score."},
            {"step": "3", "title": "Staged Budget & Gate Formulation", "desc": "Defines approval conditions and releases capital in phased tranches."},
            {"step": "4", "title": "Executive Verdict & Human Sign-off", "desc": "Produces the executive verdict ready for budget owner approval and implementation."}
        ],
        "methodologies": [
            {"title": "Multi-Criteria Decision Analysis (MCDA)", "desc": "Weights financial return (30%), strategic fit (25%), risk (25%), and ops (20%).", "icon": "⚖️"},
            {"title": "Staged Capital Commitment", "desc": "Releases capital in phased gates (e.g. 30% kickoff, 40% milestone 1, 30% scale).", "icon": "💰"},
            {"title": "Human-in-the-Loop Governance", "desc": "Empowers executive leaders to Approve, Approve with Conditions, or Reject.", "icon": "✍️"}
        ],
        "deliverables": [
            "Authoritative Boardroom Verdict (Approve / Conditional / Reject)",
            "Composite Strategic Fit & Viability Score (0 – 100)",
            "Staged Capital Release schedule with gate criteria",
            "Immediate 90-Day Action Roadmap with owner assignments"
        ],
        "kpi_benchmarks": [
            {"label": "Executive Verdict", "value": "Approved w/ Conditions", "tone": "mint"},
            {"label": "Weighted Fit Score", "value": "84 / 100", "tone": "mint"},
            {"label": "Budget Tranche 1", "value": "35% Released", "tone": "mint"},
            {"label": "Action Items", "value": "5 Immediate Priorities", "tone": "mint"}
        ]
    }
}

# Ordered list of keys for sequence rendering
AGENTS_ORDER = ["planner", "finance", "marketing", "operations", "risk", "debate", "ceo"]


def get_all_agents():
    """Returns list of all 7 agents in boardroom sequence."""
    return [AGENTS_CATALOG[k] for k in AGENTS_ORDER]


def get_agent(agent_key):
    """Returns agent dict or None."""
    return AGENTS_CATALOG.get(agent_key)
