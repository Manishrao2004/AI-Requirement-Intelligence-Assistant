"""API routes — uses MongoDB for document blobs and SQLAlchemy for relational records.

Storage split:
- MongoDB: documents collection (large parsed-doc JSON), jobs collection (raw pipeline result JSON)
- SQLAlchemy: projects table (project metadata), jobs table (job status tracking)
"""
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy import select

from app.schemas import ParsedDocument
from app.parser import parse_document, SUPPORTED_EXTENSIONS
from app.database import get_mongo_db, get_session
from app.models import Project, Job
from app.services import _mem, _now_iso, save_job, run_pipeline

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document, parse it with Docling, and return a project_id."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    project_id = str(uuid.uuid4())
    temp_path = Path(f"temp_{project_id}{file_ext}")

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        parsed_doc = parse_document(str(temp_path), file.filename)
        doc_dict = parsed_doc.model_dump()

        # In-memory fallback cache
        _mem[f"doc_{project_id}"] = doc_dict

        # SQLAlchemy: project metadata row
        try:
            async with get_session() as session:
                project = Project(
                    project_id=project_id,
                    filename=file.filename,
                    title=parsed_doc.title,
                    version=parsed_doc.version,
                    section_count=len(parsed_doc.sections),
                    uploaded_at=datetime.now(timezone.utc),
                )
                session.add(project)
        except Exception:
            pass  # Non-blocking

        # MongoDB: full document blob
        try:
            db = get_mongo_db()
            await db.documents.update_one(
                {"project_id": project_id},
                {"$set": {
                    "project_id": project_id,
                    "parsed_doc": doc_dict,
                    "uploaded_at": _now_iso(),
                }},
                upsert=True,
            )
        except Exception:
            pass  # Non-blocking

        return {
            "project_id": project_id,
            "title": parsed_doc.title,
            "version": parsed_doc.version,
            "sections": len(parsed_doc.sections),
            "message": f"Document parsed successfully. Use POST /analyze/{project_id} to start analysis.",
        }

    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.post("/analyze/{project_id}")
async def analyze_document(project_id: str, background_tasks: BackgroundTasks):
    """Trigger the LangGraph multi-agent analysis pipeline (async background job)."""
    doc_data = None

    # 1. Skip SQLAlchemy since parsed_doc is stored in MongoDB/memory

    # 2. Fallback to MongoDB
    if not doc_data:
        try:
            db = get_mongo_db()
            doc_record = await db.documents.find_one({"project_id": project_id})
            if doc_record and "parsed_doc" in doc_record:
                doc_data = doc_record["parsed_doc"]
        except Exception:
            pass

    # 3. Fallback to in-memory
    if not doc_data:
        doc_data = _mem.get(f"doc_{project_id}")

    if not doc_data:
        raise HTTPException(status_code=404, detail="Project not found. Upload a document first.")

    parsed_doc = ParsedDocument(**doc_data)
    job_id = str(uuid.uuid4())

    await save_job(job_id, project_id, {
        "job_id": job_id,
        "project_id": project_id,
        "status": "pending",
        "created_at": _now_iso(),
    })

    background_tasks.add_task(run_pipeline, job_id, project_id, parsed_doc)

    return {
        "job_id": job_id,
        "project_id": project_id,
        "status": "pending",
        "message": f"Analysis started. Poll GET /analysis/{job_id} for results.",
    }


@router.get("/analysis/{job_id}")
async def get_analysis(job_id: str):
    """Get the status and results of an analysis job."""
    # 1. In-memory (fastest)
    if job := _mem.get(job_id):
        return job

    # 2. SQLAlchemy
    try:
        async with get_session() as session:
            result = await session.execute(select(Job).where(Job.job_id == job_id))
            job_row = result.scalar_one_or_none()
            if job_row:
                return job_row.to_dict()
    except Exception:
        pass

    # 3. MongoDB (full result blob)
    try:
        db = get_mongo_db()
        job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        if job:
            return job
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Job not found.")


@router.get("/history")
async def get_history():
    """List all past analysis jobs (most recent first)."""
    # 1. SQLAlchemy
    try:
        async with get_session() as session:
            result = await session.execute(
                select(Job).order_by(Job.created_at.desc()).limit(50)
            )
            rows = result.scalars().all()
            if rows:
                return [r.to_dict() for r in rows]
    except Exception:
        pass

    # 2. MongoDB fallback
    try:
        db = get_mongo_db()
        cursor = db.jobs.find({}, {"_id": 0}).sort("created_at", -1).limit(50)
        jobs = await cursor.to_list(length=50)
        if jobs:
            return jobs
    except Exception:
        pass

    # 3. In-memory fallback
    return [
        v for k, v in _mem.items()
        if not k.startswith("doc_") and isinstance(v, dict) and "job_id" in v
    ]


@router.post("/compare")
async def compare_documents(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    """Compare two requirement documents and return a structured diff."""
    from app.agents.llm import get_llm
    from pydantic import BaseModel, Field

    docs = []
    for f in [file_a, file_b]:
        ext = Path(f.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {f.filename}")
        temp = Path(f"temp_cmp_{f.filename}")
        try:
            content = await f.read()
            with open(temp, "wb") as fh:
                fh.write(content)
            docs.append(parse_document(str(temp), f.filename))
        finally:
            if temp.exists():
                temp.unlink()

    class Modification(BaseModel):
        requirement: str = Field(description="The ID and name of the requirement")
        change: str = Field(description="A concise 1-sentence summary of what changed")

    class ComparisonResult(BaseModel):
        added: list[str] = Field(description="Requirement IDs added in Document B")
        removed: list[str] = Field(description="Requirement IDs removed from Document A")
        modified: list[Modification] = Field(description="Requirements that changed")
        summary: str = Field(description="Brief 1-sentence summary of the key differences")

    llm = get_llm()
    structured_llm = llm.with_structured_output(ComparisonResult)

    prompt = f"""Compare these two requirement documents and identify what changed.

Document A ({docs[0].title}):
{docs[0].full_text}

Document B ({docs[1].title}):
{docs[1].full_text}
"""
    try:
        result = structured_llm.invoke(prompt)
        return {
            "document_a": docs[0].title,
            "document_b": docs[1].title,
            "comparison": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")
