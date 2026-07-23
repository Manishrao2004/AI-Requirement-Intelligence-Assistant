"""Agent 3 — Synthesis Agent (Structured Output).
Takes the validation messages and tool feedback, and writes the final summary JSON.
"""
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from typing import List
from app.state import AnalysisState
from app.agents.llm import get_llm
import json

class Ambiguity(BaseModel):
    requirement_id: str
    original_text: str
    issue: str
    suggestion: str

class MissingCategory(BaseModel):
    category: str
    suggestion: str
    reason: str

class Conflict(BaseModel):
    requirement_a_id: str
    requirement_a_text: str
    requirement_b_id: str
    requirement_b_text: str
    conflict_description: str

class Dependency(BaseModel):
    from_requirement: str
    to_requirement: str
    relationship: str

class SynthesisSummary(BaseModel):
    executive_summary: str
    developer_summary: str
    business_summary: str
    quality_score: int

class SynthesisOutput(BaseModel):
    ambiguities: List[Ambiguity]
    missing: List[MissingCategory]
    conflicts: List[Conflict]
    dependencies: List[Dependency]
    summary: SynthesisSummary

SYSTEM_PROMPT = """You are a senior software architect. 
The validation agent has run tools and generated feedback on the system requirements.

Based on the original requirements and the validation agent's feedback:
1. Identify all ambiguities (vague terms, missing acceptance criteria).
2. Identify missing critical categories (e.g. Authentication, Security).
3. Record any conflicts found.
4. Map requirement dependencies.
5. Provide executive, developer, and business summaries.
6. Calculate a quality score (start 100, -8 per ambiguity, -10 per missing category, -12 per conflict).

Output strictly according to the requested JSON schema."""

def synthesis_agent(state: AnalysisState) -> dict:
    """Synthesis agent node — uses structured output to generate final JSON."""
    synth_msgs = state.get("synth_messages", [])
    val_msgs = state.get("validation_messages", [])

    if not synth_msgs:
        reqs = state.get("requirements", {})
        
        # Build context from requirements and validation messages
        context = {
            "title": state.get("title", "Unknown"),
            "requirements": reqs,
            "validation_history": [
                f"[{type(m).__name__}]: {getattr(m, 'content', '')}"
                for m in val_msgs
            ]
        }
        initial_msgs = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Generate the final structured analysis based on this context:\n\n{json.dumps(context, indent=2)}"
            ),
        ]
        
        structured_llm = get_llm().with_structured_output(SynthesisOutput)
        
        try:
            parsed: SynthesisOutput = structured_llm.invoke(initial_msgs)
            from langchain_core.messages import AIMessage
            response = AIMessage(content=parsed.model_dump_json())
        except Exception as e:
            # Fallback if structured output fails
            from langchain_core.messages import AIMessage
            response = AIMessage(content="{}")
            
        return {"synth_messages": initial_msgs + [response]}

    return {"synth_messages": synth_msgs}


def format_output(state: AnalysisState) -> dict:
    """Parse the final synthesis agent message and assemble the complete final_output."""
    synth_msgs = state.get("synth_messages", [])
    
    _EMPTY_SYNTHESIS = {
        "ambiguities": [], "missing": [], "conflicts": [], "dependencies": [],
        "summary": {"executive_summary": "", "developer_summary": "", "business_summary": "", "quality_score": 0}
    }

    if synth_msgs:
        last_msg = synth_msgs[-1]
        content = getattr(last_msg, "content", "{}")
        try:
            data = json.loads(content)
        except Exception:
            data = {}
    else:
        data = {}

    summary = data.get("summary", _EMPTY_SYNTHESIS["summary"])
    ambiguities = data.get("ambiguities", [])
    missing = data.get("missing", [])
    conflicts = data.get("conflicts", [])
    dependencies = data.get("dependencies", [])

    if summary.get("quality_score", 0) == 100 and (ambiguities or missing or conflicts):
        deductions = len(ambiguities) * 8 + len(missing) * 10 + len(conflicts) * 12
        summary["quality_score"] = max(0, 100 - deductions)

    final_output = {
        "project_id": state.get("project_id", ""),
        "title": state.get("title", ""),
        "requirements": state.get("requirements", {}),
        "user_stories": state.get("user_stories", []),
        "stakeholders": state.get("stakeholders", []),
        "priorities": state.get("priorities", []),
        "ambiguities": ambiguities,
        "missing_requirements": missing,
        "conflicts": conflicts,
        "dependencies": dependencies,
        "summary": summary,
    }

    result: dict = {
        "ambiguities": ambiguities,
        "missing": missing,
        "conflicts": conflicts,
        "dependencies": dependencies,
        "summary": summary,
        "final_output": final_output,
    }
    return result
