import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.schemas import ParsedDocument, AnalysisJob
from app.parser import parse_document, chunk_document, SUPPORTED_EXTENSIONS
from app.graph import analysis_pipeline
from app.database import get_mongo_db, get_supabase

router = APIRouter()

# In-memory job store (backed by MongoDB and Supabase when available)
_jobs: dict[str, dict] = {}


async def _save_job(job_id: str, data: dict):
    """Persist job to MongoDB, Supabase, and in-memory cache."""
    _jobs[job_id] = data
    # 1. MongoDB (Document / Execution state)
    try:
        db = get_mongo_db()
        await db.jobs.update_one(
            {"job_id": job_id}, 
            {"$set": {
                "job_id": job_id,
                "project_id": data.get("project_id"),
                "result": data.get("result"),
                "errors": data.get("errors"),
                "error": data.get("error")
            }}, 
            upsert=True
        )
    except Exception:
        pass  # MongoDB optional — in-memory fallback

    # 2. Supabase (Relational job records)
    try:
        sb = get_supabase()
        if sb:
            sb.table("jobs").upsert({
                "job_id": job_id,
                "project_id": data.get("project_id"),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "completed_at": data.get("completed_at")
            }).execute()
    except Exception:
        pass  # Supabase optional — non-blocking fallback


async def _run_pipeline(job_id: str, project_id: str, parsed_doc: ParsedDocument):
    """Execute the LangGraph pipeline in background and store results."""
    await _save_job(job_id, {
        "job_id": job_id,
        "project_id": project_id,
        "status": "running",
        "created_at": datetime.utcnow().isoformat(),
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

        # Run LangGraph pipeline (sync graph in thread to not block event loop)
        result = await asyncio.to_thread(
            analysis_pipeline.invoke, 
            initial_state, 
            {"configurable": {"thread_id": job_id}}
        )

        final_output = result.get("final_output", {})
        await _save_job(job_id, {
            "job_id": job_id,
            "project_id": project_id,
            "status": "completed",
            "created_at": _jobs.get(job_id, {}).get("created_at", ""),
            "completed_at": datetime.utcnow().isoformat(),
            "result": final_output,
            "errors": result.get("errors", []),
        })

    except Exception as e:
        await _save_job(job_id, {
            "job_id": job_id,
            "project_id": project_id,
            "status": "failed",
            "error": str(e),
        })


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document, parse it with Docling, and return a project_id."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    project_id = str(uuid.uuid4())
    temp_path = Path(f"temp_{project_id}{file_ext}")

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        parsed_doc = parse_document(str(temp_path), file.filename)

        # Store parsed doc in memory for analysis
        _jobs[f"doc_{project_id}"] = parsed_doc.model_dump()

        # Store metadata in MongoDB (Heavy Document Payload)
        try:
            db = get_mongo_db()
            await db.documents.insert_one({
                "project_id": project_id,
                "parsed_doc": parsed_doc.model_dump(),
                "uploaded_at": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass  # MongoDB optional

        # Store metadata in Supabase (Relational project record)
        try:
            sb = get_supabase()
            if sb:
                sb.table("projects").upsert({
                    "project_id": project_id,
                    "filename": file.filename,
                    "title": parsed_doc.title,
                    "version": parsed_doc.version,
                    "section_count": len(parsed_doc.sections),
                    "uploaded_at": datetime.utcnow().isoformat(),
                }).execute()
        except Exception:
            pass  # Supabase optional

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
    """Trigger the LangGraph multi-agent analysis pipeline (async)."""
    # Try MongoDB first, fallback to memory
    doc_data = None
    try:
        db = get_mongo_db()
        doc_record = await db.documents.find_one({"project_id": project_id})
        if doc_record and "parsed_doc" in doc_record:
            doc_data = doc_record["parsed_doc"]
    except Exception:
        pass
    
    if not doc_data:
        doc_data = _jobs.get(f"doc_{project_id}")
        
    if not doc_data:
        raise HTTPException(status_code=404, detail="Project not found. Upload a document first.")

    parsed_doc = ParsedDocument(**doc_data)
    job_id = str(uuid.uuid4())

    await _save_job(job_id, {
        "job_id": job_id,
        "project_id": project_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    })

    background_tasks.add_task(_run_pipeline, job_id, project_id, parsed_doc)

    return {
        "job_id": job_id,
        "project_id": project_id,
        "status": "pending",
        "message": f"Analysis started. Poll GET /analysis/{job_id} for results.",
    }


@router.get("/analysis/{job_id}")
async def get_analysis(job_id: str):
    """Get the status and results of an analysis job."""
    job = _jobs.get(job_id)

    # Try MongoDB if not in memory
    if not job:
        try:
            db = get_mongo_db()
            job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        except Exception:
            pass

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return job


@router.get("/history")
async def get_history():
    """List all past analysis jobs."""
    # Try MongoDB first
    try:
        db = get_mongo_db()
        cursor = db.jobs.find({}, {"_id": 0}).sort("created_at", -1).limit(50)
        jobs = await cursor.to_list(length=50)
        if jobs:
            return jobs
    except Exception:
        pass

    # Fallback to in-memory
    return [v for k, v in _jobs.items() if not k.startswith("doc_") and isinstance(v, dict) and "job_id" in v]


@router.post("/compare")
async def compare_documents(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """Compare two requirement documents and return differences."""
    from app.agents.llm import get_llm
    import json

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

    from pydantic import BaseModel, Field

    class Modification(BaseModel):
        requirement: str = Field(description="The ID and name of the requirement")
        change: str = Field(description="A concise, 1-sentence summary of what changed. Do not ramble.")

    class ComparisonResult(BaseModel):
        added: list[str] = Field(description="List of requirement IDs added in Document B")
        removed: list[str] = Field(description="List of requirement IDs removed from Document A")
        modified: list[Modification] = Field(description="List of requirements that changed")
        summary: str = Field(description="A brief 1-sentence summary of the key differences")

    llm = get_llm()
    structured_llm = llm.with_structured_output(ComparisonResult)
    
    prompt = f"""Compare these two requirement documents and concisely identify what changed.

Document A ({docs[0].title}):
{docs[0].full_text[:3000]}

Document B ({docs[1].title}):
{docs[1].full_text[:3000]}
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
