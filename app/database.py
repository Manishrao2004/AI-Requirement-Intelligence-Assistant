"""Database layer — two separate stores.

MongoDB  (via motor)
- Flexible document storage
- Stores: large parsed document blobs, raw pipeline results
- Collection: documents, jobs

SQLAlchemy  (asyncpg for PostgreSQL / aiosqlite for SQLite)
- Structured relational data
- Stores: project metadata rows, job status/tracking rows
- Tables: projects, jobs  (see app/models.py)

LangGraph graph memory uses MemorySaver (in-process) — no DB needed.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import DATABASE_URL, MONGODB_URL, MONGODB_DB_NAME
from app.models import Base


def _normalise_db_url(url: str) -> str:
    """Ensure the URL uses an async driver prefix.

    Bare  postgresql://  → postgresql+asyncpg://
    Bare  sqlite://      → sqlite+aiosqlite://
    Already-prefixed URLs are returned unchanged.
    """
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


_ASYNC_DB_URL = _normalise_db_url(DATABASE_URL)
_IS_SQLITE = _ASYNC_DB_URL.startswith("sqlite")


# MongoDB

_mongo_client: AsyncIOMotorClient | None = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the Motor async database instance (lazy init)."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGODB_URL)
    return _mongo_client[MONGODB_DB_NAME]


async def close_mongo() -> None:
    """Close the MongoDB connection pool (call on app shutdown)."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None


# SQLAlchemy (relational)

_engine = create_async_engine(
    _ASYNC_DB_URL,
    echo=False,
    # pool_pre_ping not supported by SQLite's StaticPool
    pool_pre_ping=not _IS_SQLITE,
)

_AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all relational tables if they don't exist yet (idempotent)."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the SQLAlchemy connection pool (call on app shutdown)."""
    await _engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager — yields a SQLAlchemy session with auto commit/rollback."""
    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
