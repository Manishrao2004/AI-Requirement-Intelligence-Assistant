from typing import TypedDict, Annotated
from operator import add


class AnalysisState(TypedDict, total=False):
    # Input
    job_id: str
    project_id: str
    document_text: str  # Full markdown from Docling
    title: str
    chunks: list[str]  # Sections split for analysis

    # Agent outputs
    requirements: dict          # Agent 1 - extracted requirements
    user_stories: list[dict]    # Agent 2
    stakeholders: list[dict]    # Agent 3
    priorities: list[dict]      # Agent 4
    ambiguities: list[dict]     # Agent 5
    missing: list[dict]         # Agent 6
    conflicts: list[dict]       # Agent 7
    dependencies: list[dict]    # Agent 8
    summary: dict               # Agent 9
    final_output: dict          # Agent 10

    # Meta
    errors: Annotated[list[str], add]
