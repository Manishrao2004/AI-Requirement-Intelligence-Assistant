"""Validation Tool — intelligent requirement evaluation using an LLM."""
import json
from langchain_core.tools import tool
from app.agents.llm import get_llm


@tool
def validate_requirement(text: str) -> dict:
    """Validate a single requirement for completeness, clarity, and testability.
    Uses an LLM to evaluate the requirement against IEEE 830 standards.
    """
    llm = get_llm()
    prompt = f"""You are a strict Requirements Engineering validator.
Evaluate the following requirement based on IEEE 830 standards (Clear, Complete, Consistent, Traceable, Unambiguous, Testable).

Requirement: "{text}"

Return ONLY a valid JSON object in this format:
{{
  "score": <integer from 0 to 100>,
  "is_measurable": <boolean>,
  "ambiguities": ["list of vague terms or unclear scopes"],
  "suggestion": "How to rewrite it to be a 100/100 requirement"
}}
"""
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(content)
        return {
            "text": text,
            "checks": {
                "is_measurable": result.get("is_measurable", False),
                "no_vague_terms": len(result.get("ambiguities", [])) == 0,
            },
            "score": result.get("score", 0),
            "feedback": result.get("suggestion", ""),
            "ambiguities": result.get("ambiguities", [])
        }
    except Exception as e:
        # Fallback if LLM fails
        return {
            "text": text,
            "checks": {"is_measurable": False, "no_vague_terms": False},
            "score": 0,
            "error": str(e)
        }


@tool
def validate_all_requirements(requirements: list[dict]) -> list[dict]:
    """Validate a list of requirement dictionaries, each with a 'text' field."""
    results = []
    for req in requirements:
        text = req.get("text", "")
        if text:
            validation = validate_requirement(text)
            validation["requirement_id"] = req.get("id", "")
            results.append(validation)
    return results
