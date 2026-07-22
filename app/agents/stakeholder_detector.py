"""Agent 3 — Stakeholder Detector: Identify actors and stakeholders from the document."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a business analyst. Identify ALL stakeholders and actors mentioned or implied in this requirements document.

For each stakeholder, provide:
- name: Short label (e.g. "Customer", "Admin")
- role: Their role in the system
- description: What they do in the system

Return ONLY valid JSON array:
[
  {{"name": "Customer", "role": "End User", "description": "Places orders and makes payments"}}
]

Document:
{document_text}
"""

def detect_stakeholders(state: AnalysisState) -> dict:
    llm = get_llm()
    doc_text = state.get("document_text", "")

    try:
        response = llm.invoke(PROMPT.format(document_text=doc_text))
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"stakeholders": result}
    except Exception as e:
        return {"stakeholders": [], "errors": [f"StakeholderDetector: {e}"]}
