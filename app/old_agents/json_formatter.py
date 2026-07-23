"""Agent 10 — JSON Formatter: Assemble all agent outputs into the final structured result."""
from app.state import AnalysisState


def format_json(state: AnalysisState) -> dict:
    final = {
        "project_id": state.get("project_id", ""),
        "title": state.get("title", ""),
        "requirements": state.get("requirements", {}),
        "user_stories": state.get("user_stories", []),
        "stakeholders": state.get("stakeholders", []),
        "priorities": state.get("priorities", []),
        "ambiguities": state.get("ambiguities", []),
        "missing_requirements": state.get("missing", []),
        "conflicts": state.get("conflicts", []),
        "dependencies": state.get("dependencies", []),
        "summary": state.get("summary", {}),
    }
    return {"final_output": final}
