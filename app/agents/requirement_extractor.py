"""Agent 1 — Requirement Extraction: Classify into Functional / Non-Functional / Business Rules."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a software requirements analyst. Analyze the following document and extract ALL requirements.

Classify each requirement into exactly one category:
- functional: Features the system must do
- non_functional: Performance, security, scalability, usability constraints
- business_rule: Business logic, policies, compliance rules

Return ONLY valid JSON in this exact format:
{{
  "functional": [
    {{"id": "FR-1", "text": "...", "category": "functional"}}
  ],
  "non_functional": [
    {{"id": "NFR-1", "text": "...", "category": "non_functional"}}
  ],
  "business_rules": [
    {{"id": "BR-1", "text": "...", "category": "business_rule"}}
  ]
}}

Document:
{document_text}
"""

def extract_requirements(state: AnalysisState) -> dict:
    llm = get_llm()
    doc_text = state.get("document_text", "")

    try:
        response = llm.invoke(PROMPT.format(document_text=doc_text))
        content = response.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"requirements": result}
    except Exception as e:
        return {"requirements": {"functional": [], "non_functional": [], "business_rules": []}, "errors": [f"RequirementExtractor: {e}"]}
