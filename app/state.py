from typing import TypedDict, Annotated
from operator import add
from langgraph.graph.message import add_messages


class AnalysisState(TypedDict, total=False):
    # Input
    job_id: str
    project_id: str
    document_text: str          # Full markdown from Docling
    title: str
    chunks: list[str]           # Sections split for analysis

    # Agent 1 conversation (Analysis ReAct loop)
    messages: Annotated[list, add_messages]

    # Agent 2 conversation (Validation ReAct loop)
    validation_messages: Annotated[list, add_messages]

    # Agent 3 conversation (Synthesis loop)
    synth_messages: Annotated[list, add_messages]

    # Agent 1 outputs
    requirements: dict          # Functional / Non-Functional / Business Rules
    user_stories: list[dict]
    stakeholders: list[dict]
    priorities: list[dict]

    # Agent 2 outputs
    ambiguities: list[dict]
    missing: list[dict]
    conflicts: list[dict]
    dependencies: list[dict]
    summary: dict
    final_output: dict          # Assembled complete result

    # Meta
    errors: Annotated[list[str], add]
