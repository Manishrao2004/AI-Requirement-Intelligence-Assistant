"""LangGraph workflow — 3-Agent linear pipeline.

Architecture:
    analysis_agent 
        │
        ▼
    extract_analysis
        │
        ▼
    validation_agent -> [validation_tools] -> validation_agent  (Tool loop)
        |
        v
    synthesis_agent
        |
        v
    format_output -> END

Checkpointer: MemorySaver (in-process, per thread_id = job_id)
"""
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.state import AnalysisState

# Agent 1 (Analysis / Extraction)
from app.agents.analysis_agent import (
    analysis_agent,
    extract_analysis,
)

# Agent 2 (Validation / Tool Execution)
from app.agents.validation_agent import (
    validation_agent,
    route_validation,
    VALIDATION_TOOLS,
)

# Agent 3 (Synthesis / Output Formatting)
from app.agents.synthesis_agent import (
    synthesis_agent,
    format_output,
)

# In-process memory checkpointer
_checkpointer = MemorySaver()

def build_analysis_graph():
    """Build and compile the 3-agent LangGraph analysis pipeline."""
    graph = StateGraph(AnalysisState)

    # Nodes
    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("extract_analysis", extract_analysis)

    graph.add_node("validation_agent", validation_agent)
    graph.add_node("validation_tools", ToolNode(VALIDATION_TOOLS))

    graph.add_node("synthesis_agent", synthesis_agent)
    graph.add_node("format_output", format_output)

    # Edges
    graph.set_entry_point("analysis_agent")
    
    # 1. Analysis phase
    graph.add_edge("analysis_agent", "extract_analysis")
    graph.add_edge("extract_analysis", "validation_agent")

    # 2. Validation tool loop
    graph.add_conditional_edges(
        "validation_agent",
        route_validation,
        {
            "validation_tools": "validation_tools",
            "synthesis_agent": "synthesis_agent",
        },
    )
    graph.add_edge("validation_tools", "validation_agent")

    # 3. Synthesis phase
    graph.add_edge("synthesis_agent", "format_output")
    graph.add_edge("format_output", END)

    return graph.compile(checkpointer=_checkpointer)

# Pre-compiled graph instance (imported by routes.py)
analysis_pipeline = build_analysis_graph()
