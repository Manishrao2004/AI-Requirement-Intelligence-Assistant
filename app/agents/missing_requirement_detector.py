"""Agent 6 — Missing Requirement Detector: Identify gaps in the requirements using Semantic Search."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm
from app.tools.search_tool import get_search_tool

PROMPT = """You are a senior software architect reviewing a requirements document for completeness.

Given the existing requirements and the context extracted via semantic search, identify requirements that are MISSING but would typically be expected for this type of system.

Consider:
- Authentication, Authorization, Error handling, Data backup, Security, Accessibility, Monitoring.

Context extracted from document regarding Security/Auth/Data:
{search_context}

Return ONLY valid JSON array:
[
  {{
    "category": "Authentication",
    "suggestion": "Forgot Password flow",
    "reason": "Login is mentioned but no password recovery mechanism is defined"
  }}
]

If nothing is missing, return an empty array [].

Existing Requirements:
{requirements}
"""

def detect_missing_requirements(state: AnalysisState) -> dict:
    llm = get_llm()
    reqs = state.get("requirements", {})
    doc_text = state.get("document_text", "")
    all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])

    try:
        # Use the intelligent search tool to proactively scan for missing areas
        search_tool = get_search_tool(doc_text)
        search_context = search_tool.invoke({"query": "What are the security, authentication, and data backup constraints?"})

        response = llm.invoke(PROMPT.format(
            requirements=json.dumps(all_reqs, indent=2),
            search_context=search_context
        ))
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"missing": result}
    except Exception as e:
        return {"missing": [], "errors": [f"MissingRequirementDetector: {e}"]}
