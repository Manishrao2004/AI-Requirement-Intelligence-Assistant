"""Agent 2 — User Story Generator: Convert requirements into user stories."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a product manager. Convert the following requirements into user stories.

Use this format for each:
"As a [role], I want to [action] so that [benefit]"

Return ONLY valid JSON array:
[
  {{
    "requirement_id": "FR-1",
    "role": "customer",
    "action": "login with Google",
    "benefit": "I can access the app quickly",
    "story": "As a customer, I want to login with Google so that I can access the app quickly"
  }}
]

Requirements:
{requirements}
"""

def generate_user_stories(state: AnalysisState) -> dict:
    llm = get_llm()
    reqs = state.get("requirements", {})
    all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])

    if not all_reqs:
        return {"user_stories": []}

    try:
        response = llm.invoke(PROMPT.format(requirements=json.dumps(all_reqs, indent=2)))
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"user_stories": result}
    except Exception as e:
        return {"user_stories": [], "errors": [f"UserStoryGenerator: {e}"]}
