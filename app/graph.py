"""LangGraph workflow — wires all 10 agents into a sequential analysis pipeline."""
from langgraph.graph import StateGraph, END
from app.state import AnalysisState
from app.agents.requirement_extractor import extract_requirements
from app.agents.user_story_generator import generate_user_stories
from app.agents.stakeholder_detector import detect_stakeholders
from app.agents.priority_classifier import classify_priorities
from app.agents.ambiguity_checker import check_ambiguities
from app.agents.missing_requirement_detector import detect_missing_requirements
from app.agents.conflict_detector import detect_conflicts
from app.agents.dependency_finder import find_dependencies
from app.agents.summary_generator import generate_summary
from app.agents.json_formatter import format_json
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from app.config import MONGODB_URL

# Synchronous client for LangGraph checkpointer (runs in to_thread)
_mongo_client = MongoClient(MONGODB_URL)
_checkpointer = MongoDBSaver(_mongo_client)


def build_analysis_graph() -> StateGraph:
    """Build and compile the LangGraph analysis pipeline."""
    graph = StateGraph(AnalysisState)

    # Add all agent nodes
    graph.add_node("extract_requirements", extract_requirements)
    graph.add_node("detect_stakeholders", detect_stakeholders)
    graph.add_node("generate_user_stories", generate_user_stories)
    graph.add_node("classify_priorities", classify_priorities)
    graph.add_node("check_ambiguities", check_ambiguities)
    graph.add_node("detect_missing", detect_missing_requirements)
    graph.add_node("detect_conflicts", detect_conflicts)
    graph.add_node("find_dependencies", find_dependencies)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("format_json", format_json)

    # Define sequential flow
    graph.set_entry_point("extract_requirements")
    graph.add_edge("extract_requirements", "detect_stakeholders")
    graph.add_edge("detect_stakeholders", "generate_user_stories")
    graph.add_edge("generate_user_stories", "classify_priorities")
    graph.add_edge("classify_priorities", "check_ambiguities")
    graph.add_edge("check_ambiguities", "detect_missing")
    graph.add_edge("detect_missing", "detect_conflicts")
    graph.add_edge("detect_conflicts", "find_dependencies")
    graph.add_edge("find_dependencies", "generate_summary")
    graph.add_edge("generate_summary", "format_json")
    graph.add_edge("format_json", END)

    return graph.compile(checkpointer=_checkpointer)


# Pre-compiled graph instance
analysis_pipeline = build_analysis_graph()
