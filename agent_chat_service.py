"""Service module for AI Boardroom Agent Chatbots.

Handles persona-based conversational LLM interactions for each of the 7 executive agents:
- Planner Agent
- Finance Agent
- Marketing Agent
- Operations Agent
- Risk Agent
- Debate Agent
- CEO Agent
"""
import logging
from flask import current_app
from services.agent_catalog import get_agent

logger = logging.getLogger("boardroom.chat")

# Preset suggested questions per agent
SUGGESTED_QUESTIONS = {
    "planner": [
        "How should we phase our strategic execution roadmap?",
        "What are the critical path dependencies in this decision?",
        "How do we allocate the budget across rollout stages?"
    ],
    "finance": [
        "What is our projected break-even horizon and cash runway?",
        "How sensitive is net profit to unexpected revenue drops?",
        "What is our expected 3-year ROI and capital efficiency ratio?"
    ],
    "marketing": [
        "What is our target LTV:CAC ratio and payback period?",
        "Which acquisition channels offer the highest conversion leverage?",
        "How should we position our value proposition against incumbents?"
    ],
    "operations": [
        "What are our primary operational bottlenecks and hiring needs?",
        "How ready is our infrastructure for 5x customer volume growth?",
        "What SLA and quality control frameworks should we enforce?"
    ],
    "risk": [
        "What are the top critical risk factors in this scenario?",
        "How can we mitigate financial and market downside exposure?",
        "What early warning trigger metrics should we monitor?"
    ],
    "debate": [
        "What are the main conflicts between Finance and Marketing?",
        "What core trade-offs require executive arbitration?",
        "Where is the strongest consensus among the 7 agents?"
    ],
    "ceo": [
        "What is your final executive recommendation and verdict?",
        "What are the immediate 90-day action priorities?",
        "How should capital be released across stage-gate tranches?"
    ]
}


def get_suggested_questions(agent_key: str):
    """Return preset questions for the specified agent."""
    return SUGGESTED_QUESTIONS.get(agent_key.lower(), [
        "How does your agent role analyze this business decision?",
        "What are the key outputs from your domain analysis?",
        "What recommendations do you have for our team?"
    ])


def _extract_text_content(content):
    """Safely extract plain string content from LangChain/Gemini response shapes."""
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(str(item["text"]))
                elif "text" in item:
                    parts.append(str(item["text"]))
        if parts:
            return "\n".join(parts)
    return str(content)


def generate_agent_response(agent_key: str, user_message: str, scenario=None, history=None):
    """
    Generate a response from the specified agent persona tailored to the user's question.
    Uses Gemini when configured, with a domain-aware fallback.
    """
    agent = get_agent(agent_key.lower())
    if not agent:
        return "I'm sorry, I couldn't find the requested agent profile."

    agent_name = agent["name"]
    role = agent["role"]
    summary = agent["summary"]
    tagline = agent["tagline"]

    # Build context from scenario if available
    scenario_context = ""
    if scenario:
        result_obj = scenario.get_result(agent_key.lower()) if hasattr(scenario, 'get_result') else None
        agent_data = result_obj.data() if result_obj else {}
        
        scenario_context = f"""
CURRENT BUSINESS DECISION CONTEXT:
- Decision Title: {scenario.title}
- Scenario Description: {scenario.description}
- Upfront Investment: ${scenario.investment:,.2f}
- Expected Annual Revenue: ${scenario.expected_revenue:,.2f}
- Operating Cost: ${scenario.operating_cost:,.2f}
- Target Market: {scenario.target_market or 'N/A'}
- Timeline: {scenario.timeline or 'N/A'}
- Industry: {scenario.industry or 'N/A'}
"""
        if agent_data:
            scenario_context += f"- Boardroom Results for {agent_name}: {agent_data.get('summary') or agent_data.get('findings') or agent_data.get('reasoning') or 'Analysis completed.'}\n"

    system_prompt = f"""You are the {agent_name} ({role}), an executive AI boardroom agent.
Tagline: {tagline}
Core Profile: {summary}

Your duty is to advise executive leadership in a professional, sharp, insightful, and executive tone.
Respond directly and specifically to the user's current question.
Do NOT repeat generic introductory boilerplate greeting if answering a follow-up question.
Focus on providing structured, actionable insights (using Markdown headings, tables, bullet points, or bold text).

{scenario_context}
"""

    api_key = current_app.config.get("GEMINI_API_KEY")
    if api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = current_app.config.get("GEMINI_MODEL", "gemini-3-flash-preview")
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.4,
            )
            
            messages = [("system", system_prompt)]
            if history and isinstance(history, list):
                # Clean history to avoid duplicating user_message
                clean_history = [
                    item for item in history 
                    if isinstance(item, dict) and item.get("text") and item.get("text").strip() != user_message.strip()
                ]
                for item in clean_history[-6:]: # Keep last 6 exchanges for context
                    role_type = "human" if item.get("sender") == "user" else "ai"
                    messages.append((role_type, item.get("text", "")))
            
            messages.append(("human", user_message))
            
            res = llm.invoke(messages)
            if res and hasattr(res, "content") and res.content:
                text_out = _extract_text_content(res.content)
                if text_out:
                    return text_out
        except Exception as e:
            logger.warning("Gemini chat invoke failed: %s. Falling back to heuristic response.", e)

    # Intelligent Fallback Response when API key is missing or offline
    return _generate_fallback_response(agent, user_message, scenario)


def _generate_fallback_response(agent, user_message: str, scenario=None):
    """Generates an intelligent, domain-rich fallback response tailored to the question."""
    agent_name = agent["name"]
    role = agent["role"]
    msg_lower = user_message.lower()
    
    sc_title = f"'{scenario.title}'" if scenario else "your business scenario"

    if "risk" in msg_lower or "threat" in msg_lower or "danger" in msg_lower:
        return f"As your **{agent_name}** ({role}), I evaluate risks rigorously. For {sc_title}, our primary focus is minimizing unexpected volatility.\n\n### Primary Risk Factors\n1. **Execution Risk:** Resource bottlenecks and rollout delays.\n2. **Market Risk:** Customer adoption velocity and competitor response.\n3. **Financial Risk:** Cost overrun safeguards.\n\n### Recommended Mitigation\nEnforce strict milestone gates before releasing phase capital."

    if "break-even" in msg_lower or "roi" in msg_lower or "profit" in msg_lower or "revenue" in msg_lower or "budget" in msg_lower:
        if scenario:
            net = scenario.expected_revenue - scenario.operating_cost
            roi = ((net / scenario.investment) * 100) if scenario.investment > 0 else 0
            return f"### Financial & ROI Analysis for {sc_title}\n- **Upfront Investment:** ${scenario.investment:,.2f}\n- **Expected Net Return:** ${net:,.2f}\n- **Projected ROI:** **{roi:.1f}%**\n\n### Recommendations\nMaintain a 6-month cash runway buffer and monitor unit economics closely as volume scales."
        return f"### {role} Analysis\nFinancial viability depends on unit economics, contribution margins, and payback horizons. I recommend mapping 36-month P&L statements with stage-gated capital commitments."

    if "roadmap" in msg_lower or "phase" in msg_lower or "timeline" in msg_lower or "plan" in msg_lower or "critical path" in msg_lower:
        return f"### Execution Roadmap & Strategic Phasing for {sc_title}\n\n| Phase | Timeline | Focus | Success Metric |\n|---|---|---|---|\n| **Phase 1: Discovery** | Months 1-2 | Scope & Technical Validation | Prototype Lock |\n| **Phase 2: Build** | Months 3-4 | Mass Production & Beta Testing | UAT Approval |\n| **Phase 3: Launch** | Months 5-6 | Go-To-Market & Acquisition | First 500 Customers |\n| **Phase 4: Scale** | Month 6+ | Omnichannel Expansion | Target Revenue |\n\n### Critical Path\nKey dependencies reside between Phase 1 technical lock and Phase 2 vendor procurement."

    if "marketing" in msg_lower or "cac" in msg_lower or "ltv" in msg_lower or "customer" in msg_lower or "channel" in msg_lower:
        return f"### Market & Customer Acquisition Strategy for {sc_title}\n- **Target LTV:CAC Ratio:** Minimum 3.5x\n- **Primary Channels:** Digital Content, Performance Search/Social, Strategic Partnerships\n- **Payback Horizon:** Sub 6-month target payback on acquisition spend."

    if "operation" in msg_lower or "staff" in msg_lower or "hiring" in msg_lower or "bottleneck" in msg_lower:
        return f"### Operations Feasibility for {sc_title}\n- **Readiness Audit:** 86/100 score\n- **Immediate Staffing:** 3 core hires (Product Lead, Senior Architect, Ops Specialist)\n- **SLA Target:** 99.9% uptime with automated error monitoring."

    if "debate" in msg_lower or "conflict" in msg_lower or "consensus" in msg_lower or "trade-off" in msg_lower:
        return f"### Boardroom Debate & Consensus Review\n- **Primary Trade-off:** Speed of rollout (Marketing & Planner) vs Conservative runway (Finance & Risk).\n- **Consensus:** 88% alignment on stage-gated capital deployment."

    if "ceo" in msg_lower or "verdict" in msg_lower or "decision" in msg_lower or "action" in msg_lower or "priority" in msg_lower:
        return f"### Executive Verdict & 90-Day Priorities for {sc_title}\n**Verdict: Approved w/ Stage-Gate Conditions**\n\n1. Lock key technical specs within 30 days.\n2. Authorize Tranche 1 (35% budget release).\n3. Establish weekly cross-agent milestone tracking."

    # Dynamic fallback tailored directly to user's question
    return f"### {agent_name} Analysis ({role})\nRegarding your question: *\"{user_message}\"*\n\nFor {sc_title}, my strategic recommendation as **{agent_name}** is to focus on stage-gated execution, de-risking key dependencies early, and aligning team KPIs around target deliverables. How else can I assist your boardroom decision?"
