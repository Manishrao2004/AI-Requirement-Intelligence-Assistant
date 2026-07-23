"""Service layer for business logic, background tasks, and database writes."""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.schemas import ParsedDocument
from app.graph import analysis_pipeline
from app.database import get_mongo_db, get_session
from app.models import Job

# In-memory fallback cache
_mem: dict[str, dict] = {}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def _upsert_job_sql(job_id: str, project_id: str, data: dict) -> None:
    """Create or update a job row in the relational database (SQLAlchemy)."""
    try:
        async with get_session() as session:
            result = await session.execute(select(Job).where(Job.job_id == job_id))
            job = result.scalar_one_or_none()

            if job is None:
                job = Job(job_id=job_id, project_id=project_id)
                session.add(job)

            job.status = data.get("status", job.status)
            if data.get("completed_at"):
                job.completed_at = datetime.fromisoformat(data["completed_at"])
    except Exception:
        pass  # Non-blocking; in-memory fallback still holds state

async def save_job(job_id: str, project_id: str, data: dict) -> None:
    """Persist job state to in-memory cache + SQLAlchemy + MongoDB."""
    _mem[job_id] = data

    # SQLAlchemy (structured relational record)
    await _upsert_job_sql(job_id, project_id, data)

    # MongoDB (full result JSON for fast retrieval)
    try:
        db = get_mongo_db()
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "job_id": job_id,
                "project_id": project_id,
                "status": data.get("status"),
                "result": data.get("result"),
                "errors": data.get("errors"),
                "error": data.get("error"),
            }},
            upsert=True,
        )
    except Exception:
        pass  # MongoDB optional — non-blocking

async def run_pipeline(job_id: str, project_id: str, parsed_doc: ParsedDocument) -> None:
    """Execute the LangGraph pipeline in a background thread and store results."""
    from app.parser import chunk_document
    
    await save_job(job_id, project_id, {
        "job_id": job_id,
        "project_id": project_id,
        "status": "running",
        "created_at": _now_iso(),
    })

    try:
        chunks = chunk_document(parsed_doc)
        initial_state = {
            "job_id": job_id,
            "project_id": project_id,
            "document_text": parsed_doc.full_text,
            "title": parsed_doc.title,
            "chunks": chunks,
            "errors": [],
        }

        # LangGraph is synchronous — run in thread to avoid blocking the event loop
        result = await asyncio.to_thread(
            analysis_pipeline.invoke,
            initial_state,
            {"configurable": {"thread_id": job_id}},
        )

        final_output = result.get("final_output", {})
        await save_job(job_id, project_id, {
            "job_id": job_id,
            "project_id": project_id,
            "status": "completed",
            "created_at": _mem.get(job_id, {}).get("created_at", _now_iso()),
            "completed_at": _now_iso(),
            "result": final_output,
            "errors": result.get("errors", []),
        })

    except Exception as e:
        await save_job(job_id, project_id, {
            "job_id": job_id,
            "project_id": project_id,
            "status": "failed",
            "error": str(e),
        })
