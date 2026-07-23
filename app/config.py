import os
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

# Resolve the .env file relative to this project root
_ENV_FILE = Path(__file__).parent.parent / ".env"

# override=True: .env values win over any pre-existing system env vars
# (prevents stale CI/system vars like a old DATABASE_URL from interfering)
load_dotenv(dotenv_path=_ENV_FILE, override=True)

# Read .env values directly so we can use them as authoritative defaults
_env = dotenv_values(_ENV_FILE)


def _get(key: str, default: str = "") -> str:
    """Return .env value first, then os env, then default."""
    return _env.get(key) or os.getenv(key, default)


GROQ_API_KEY: str = _get("GROQ_API_KEY")
GROQ_MODEL: str = "llama-3.3-70b-versatile"

# MongoDB (document storage: parsed docs, pipeline results)
MONGODB_URL: str = _get("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME: str = _get("MONGODB_DB_NAME", "requirement_intelligence")

# SQLAlchemy (relational tracking: project metadata, job status)
# PostgreSQL : postgresql+asyncpg://user:password@host:5432/dbname
# SQLite dev : sqlite+aiosqlite:///./requirement_intelligence.db
DATABASE_URL: str = _get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./requirement_intelligence.db",
)
