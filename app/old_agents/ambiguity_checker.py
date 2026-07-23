"""Agent 5 — Ambiguity Checker: Flag vague or unclear requirements using the Validation Tool."""
from app.state import AnalysisState
from app.tools.validation_tool import validate_requirement


def check_ambiguities(state: AnalysisState) -> dict:
    reqs = state.get("requirements", {})
    all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])

    if not all_reqs:
        return {"ambiguities": []}

    ambiguities = []
    try:
        for req in all_reqs:
            # Execute the LangChain tool directly
            res = validate_requirement.invoke({"text": req.get("text", "")})
            
            # If the requirement scored less than perfect, it has ambiguities
            if res.get("score", 100) < 100:
                ambiguities.append({
                    "requirement_id": req.get("id", ""),
                    "original_text": req.get("text", ""),
                    "issue": "Vague terms detected: " + ", ".join(res.get("ambiguities", [])),
                    "suggestion": res.get("feedback", "")
                })
        return {"ambiguities": ambiguities}
    except Exception as e:
        return {"ambiguities": [], "errors": [f"AmbiguityChecker: {e}"]}
