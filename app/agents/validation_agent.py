"""Agent 2 — Validation Agent (Tool Execution).
Takes the extracted requirements and uses tools to validate them.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.state import AnalysisState
from app.agents.llm import get_llm
from app.tools.requirement_tools import validate_requirement, check_conflict, find_coverage_gaps

VALIDATION_TOOLS = [validate_requirement, check_conflict, find_coverage_gaps]

SYSTEM_PROMPT = """You are a meticulous validation agent. Your ONLY job is to execute tools to validate the provided requirements.

CRITICAL INSTRUCTION: You MUST call exactly ONE tool per response. Do NOT attempt to call multiple tools at once. Wait for the tool feedback before calling the next tool!

1. Call `validate_requirement` on a few key requirements one by one.
2. Call `check_conflict` on any suspect pairs.
3. Call `find_coverage_gaps` exactly ONCE.

Do NOT output a final JSON summary. Your job is complete when you have executed these tools and reviewed their feedback."""

def validation_agent(state: AnalysisState) -> dict:
    """Validation agent node — invokes the LLM with tools."""
    val_msgs = state.get("validation_messages", [])
    
    if not val_msgs:
        reqs = state.get("requirements", {})
        all_reqs = reqs.get("functional", []) + reqs.get("non_functional", []) + reqs.get("business_rules", [])
        
        context = {
            "title": state.get("title", "Unknown"),
            "total_requirements": len(all_reqs),
            "requirements": reqs,
        }
        initial_msgs = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Review these extracted requirements and run the validation tools.\n\n{json.dumps(context, indent=2)}"
            ),
        ]
        llm = get_llm().bind_tools(VALIDATION_TOOLS, tool_choice="any", parallel_tool_calls=False)
        response = llm.invoke(initial_msgs)
        return {"validation_messages": initial_msgs + [response]}

    llm = get_llm().bind_tools(VALIDATION_TOOLS, parallel_tool_calls=False)
    response = llm.invoke(val_msgs)
    return {"validation_messages": [response]}

def route_validation(state: AnalysisState) -> str:
    """Conditional edge — route to tool execution or proceed to synthesis."""
    val_msgs = state.get("validation_messages", [])
    if val_msgs and hasattr(val_msgs[-1], "tool_calls") and val_msgs[-1].tool_calls:
        return "validation_tools"
    return "synthesis_agent"
