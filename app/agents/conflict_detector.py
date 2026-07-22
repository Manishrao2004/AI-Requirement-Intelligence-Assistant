"""Agent 7 — Conflict Detector: Find contradictions between requirements."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a requirements engineer. Analyze the following requirements and find any CONFLICTS or CONTRADICTIONS.

A conflict occurs when:
- Two requirements specify different values for the same parameter
- Two requirements are mutually exclusive
- A requirement contradicts a constraint or non-functional requirement

Return ONLY valid JSON array:
[
  {{
    "requirement_a_id": "FR-3",
    "requirement_a_text": "Password minimum length is 8",
    "requirement_b_id": "FR-7",
    "requirement_b_text": "Password minimum length is 6",
    "conflict_description": "Contradictory password length requirements"
  }}
]

If no conflicts found, return an empty array [].

Requirements:
{requirements}
"""

def detect_conflicts(state: AnalysisState) -> dict:
    llm = get_llm()
    reqs = state.get("requirements", {})
    all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])

    if len(all_reqs) < 2:
        return {"conflicts": []}

    try:
        response = llm.invoke(PROMPT.format(requirements=json.dumps(all_reqs, indent=2)))
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"conflicts": result}
    except Exception as e:
        return {"conflicts": [], "errors": [f"ConflictDetector: {e}"]}
