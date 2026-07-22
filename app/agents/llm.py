from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, GROQ_MODEL

def get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0,
    )
