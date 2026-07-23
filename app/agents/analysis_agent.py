"""Agent 1 — Analysis Agent (Extraction).
Extracts requirements, user stories, stakeholders, and priorities from the raw document.
Outputs structured JSON. Does not use tools.
"""
from langchain_core.messages import SystemMessage, HumanMessage
from app.state import AnalysisState
from app.agents.llm import get_llm
import json
import re

SYSTEM_PROMPT = """You are an expert software requirements analyst.
Extract all functional requirements, non-functional requirements, business rules, user stories, stakeholders, and priorities from the provided document.

CRITICAL: Output ONLY valid JSON. No markdown, no explanations, no preamble. Start with { and end with }.

{
  "requirements": {
    "functional": [{"id": "FR-1", "text": "...", "category": "functional"}],
    "non_functional": [{"id": "NFR-1", "text": "...", "category": "non_functional"}],
    "business_rules": [{"id": "BR-1", "text": "...", "category": "business_rule"}]
  },
  "user_stories": [
    {"requirement_id": "FR-1", "role": "...", "action": "...", "benefit": "...", "story": "As a ..."}
  ],
  "stakeholders": [{"name": "...", "role": "...", "description": "..."}],
  "priorities": [{"requirement_id": "FR-1", "text": "...", "priority": "must_have", "reason": "..."}]
}"""

EXTRACTION_PROMPT = """The analysis agent completed its work but returned text instead of JSON.
Re-analyze the original document below and return ONLY valid JSON with all requirements extracted.
No preamble, no markdown, no explanation — start with {{ and end with }}.

Required format:
{{
  "requirements": {{
    "functional": [{{"id": "FR-1", "text": "...", "category": "functional"}}],
    "non_functional": [{{"id": "NFR-1", "text": "...", "category": "non_functional"}}],
    "business_rules": [{{"id": "BR-1", "text": "...", "category": "business_rule"}}]
  }},
  "user_stories": [{{"requirement_id": "FR-1", "role": "...", "action": "...", "benefit": "...", "story": "As a ..."}}],
  "stakeholders": [{{"name": "...", "role": "...", "description": "..."}}],
  "priorities": [{{"requirement_id": "FR-1", "text": "...", "priority": "must_have", "reason": "..."}}]
}}

Original document:
{document_text}
"""

def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None

def analysis_agent(state: AnalysisState) -> dict:
    """Analysis agent node — extracts requirements using prompted JSON."""
    messages = state.get("messages", [])
    doc_text = state.get("document_text", "")

    if not messages:
        initial_msgs = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Analyze this requirements document:\n\n{doc_text}"),
        ]
        response = get_llm().invoke(initial_msgs)
        return {"messages": initial_msgs + [response]}
        
    return {"messages": messages}

def extract_analysis(state: AnalysisState) -> dict:
    """Parse the final analysis agent message into structured state fields."""
    messages = state.get("messages", [])
    
    last_content = ""
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if content:
            last_content = content
            break

    data = _extract_json(last_content)
    
    if data is None:
        try:
            doc_text = state.get("document_text", "")
            response = get_llm().invoke(EXTRACTION_PROMPT.format(document_text=doc_text))
            data = _extract_json(response.content)
        except Exception as e:
            pass
            
    if data is None:
        return {
            "requirements": {"functional": [], "non_functional": [], "business_rules": []},
            "user_stories": [], "stakeholders": [], "priorities": [],
            "errors": ["AnalysisAgent JSON parse error"],
        }
            
    return {
        "requirements": data.get("requirements", {"functional": [], "non_functional": [], "business_rules": []}),
        "user_stories": data.get("user_stories", []),
        "stakeholders": data.get("stakeholders", []),
        "priorities": data.get("priorities", [])
    }
