"""Search Tool — intelligent query-answering across document chunks."""
import json
from langchain_core.tools import tool
from app.agents.llm import get_llm


def get_search_tool(document_text: str):
    """Factory to create a search tool bound to a specific document text."""
    
    @tool
    def search_document(query: str) -> str:
        """Search the original requirement document for a specific topic or query.
        Use this tool when you need to verify if the document mentions a specific constraint, feature, or stakeholder.
        """
        llm = get_llm()
        prompt = f"""You are a Semantic Search Assistant.
Your job is to read the following document and answer the user's query based ONLY on the document text.
Extract the exact information requested and summarize it clearly. If the document does not contain the answer, say 'No information found'.

Query: "{query}"

Document Text:
{document_text[:8000]}  # Truncated for token limits if necessary

Return ONLY the extracted answer or 'No information found'.
"""
        try:
            response = llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            return f"Error performing search: {e}"
            
    return search_document
