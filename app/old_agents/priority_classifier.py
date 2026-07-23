"""Agent 4 — Priority Classifier: Classify requirements as Must Have / Should Have / Nice To Have."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a product strategist. Classify each requirement by priority for an MVP.

Categories:
- must_have: Critical for launch, system cannot work without it
- should_have: Important but system can launch without it
- nice_to_have: Enhances UX but not essential

Return ONLY valid JSON array:
[
  {{"requirement_id": "FR-1", "text": "...", "priority": "must_have", "reason": "Core authentication is required for all users"}}
]

Requirements:
{requirements}
"""

def classify_priorities(state: AnalysisState) -> dict:
    llm = get_llm()
    reqs = state.get("requirements", {})
    all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])

    if not all_reqs:
        return {"priorities": []}

    try:
        response = llm.invoke(PROMPT.format(requirements=json.dumps(all_reqs, indent=2)))
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"priorities": result}
    except Exception as e:
        return {"priorities": [], "errors": [f"PriorityClassifier: {e}"]}
