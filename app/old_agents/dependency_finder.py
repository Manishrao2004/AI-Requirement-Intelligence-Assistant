"""Agent 8 — Dependency Finder: Map dependencies between requirements."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a systems architect. Analyze the requirements and identify DEPENDENCIES between them.

Dependency types:
- depends_on: Requirement A cannot be implemented without Requirement B
- blocks: Requirement A must be completed before Requirement B can start
- related_to: Requirements are logically related but not strictly dependent

Return ONLY valid JSON array:
[
  {{
    "from_requirement": "FR-5",
    "to_requirement": "FR-1",
    "relationship": "depends_on"
  }}
]

If no dependencies found, return an empty array [].

Requirements:
{requirements}
"""

def find_dependencies(state: AnalysisState) -> dict:
    llm = get_llm()
    reqs = state.get("requirements", {})
    all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])

    if len(all_reqs) < 2:
        return {"dependencies": []}

    try:
        response = llm.invoke(PROMPT.format(requirements=json.dumps(all_reqs, indent=2)))
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"dependencies": result}
    except Exception as e:
        return {"dependencies": [], "errors": [f"DependencyFinder: {e}"]}
