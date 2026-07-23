"""Agent 9 — Summary Generator: Create executive, developer, and business summaries."""
import json
from app.state import AnalysisState
from app.agents.llm import get_llm

PROMPT = """You are a technical writer. Based on the analysis results below, generate three summaries and a quality score.

Generate:
1. executive_summary: High-level overview for executives (2-3 paragraphs)
2. developer_summary: Technical summary for developers (focus on architecture, complexity, tech decisions)
3. business_summary: Business impact summary (focus on value, users, market)
4. quality_score: Integer 0-100 rating the overall quality of the requirements document
   - Deduct points for: ambiguities, missing requirements, conflicts, vague terms
   - Add points for: completeness, clear validation conditions, edge cases, examples

Return ONLY valid JSON:
{{
  "executive_summary": "...",
  "developer_summary": "...",
  "business_summary": "...",
  "quality_score": 75
}}

Analysis Data:
- Title: {title}
- Total Requirements: {total_reqs}
- Functional: {functional_count}
- Non-Functional: {nonfunctional_count}
- Stakeholders: {stakeholders}
- Ambiguities Found: {ambiguity_count}
- Missing Requirements: {missing_count}
- Conflicts: {conflict_count}
- Dependencies: {dependency_count}

Document:
{document_text}
"""

def generate_summary(state: AnalysisState) -> dict:
    llm = get_llm()
    reqs = state.get("requirements", {})
    functional = reqs.get("functional", [])
    non_functional = reqs.get("non_functional", [])
    business_rules = reqs.get("business_rules", [])
    stakeholders = state.get("stakeholders", [])

    try:
        response = llm.invoke(PROMPT.format(
            title=state.get("title", "Unknown"),
            total_reqs=len(functional) + len(non_functional) + len(business_rules),
            functional_count=len(functional),
            nonfunctional_count=len(non_functional),
            stakeholders=json.dumps([s.get("name", "") for s in stakeholders]),
            ambiguity_count=len(state.get("ambiguities", [])),
            missing_count=len(state.get("missing", [])),
            conflict_count=len(state.get("conflicts", [])),
            dependency_count=len(state.get("dependencies", [])),
            document_text=state.get("document_text", "")[:2000],
        ))
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {"summary": result}
    except Exception as e:
        return {"summary": {"executive_summary": "", "developer_summary": "", "business_summary": "", "quality_score": 0}, "errors": [f"SummaryGenerator: {e}"]}
