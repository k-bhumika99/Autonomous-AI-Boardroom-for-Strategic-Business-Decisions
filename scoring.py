"""
Weighted scoring engine. Pure Python / deterministic — the LLM is never
allowed to decide the final numeric score, only to interpret it afterwards.
"""

DEFAULT_WEIGHTS = {
    "finance": 0.25,
    "marketing": 0.20,
    "operations": 0.20,
    "risk": 0.20,
    "strategic_fit": 0.15,
}


def compute_weighted_score(finance_score, marketing_score, operations_score,
                            risk_score, strategic_fit_score, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    total_weight = sum(weights.values()) or 1.0

    raw = (
        finance_score * weights.get("finance", 0)
        + marketing_score * weights.get("marketing", 0)
        + operations_score * weights.get("operations", 0)
        + risk_score * weights.get("risk", 0)
        + strategic_fit_score * weights.get("strategic_fit", 0)
    )
    final = raw / total_weight
    return round(max(0.0, min(100.0, final)), 2)


def decision_label(score: float) -> str:
    if score >= 80:
        return "STRONGLY RECOMMEND"
    if score >= 65:
        return "RECOMMEND WITH CONDITIONS"
    if score >= 50:
        return "REVIEW / DELAY"
    return "DO NOT PROCEED"


def risk_level_to_score(overall_risk_level: str) -> float:
    """Converts the Risk Agent's qualitative severity into a 0-100 'risk score'
    where HIGHER means SAFER (lower actual risk), so it can be blended into
    the weighted formula the same way as the other positively-scaled scores."""
    mapping = {
        "LOW": 90,
        "MEDIUM": 65,
        "HIGH": 40,
        "CRITICAL": 15,
    }
    return mapping.get((overall_risk_level or "MEDIUM").upper(), 65)
