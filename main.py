from dotenv import load_dotenv
load_dotenv(override=True)  # .env takes precedence over system env vars

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.database import init_db, close_db, close_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — create relational tables (idempotent, non-fatal)
    try:
        await init_db()
    except Exception as e:
        print(f"[WARNING] Could not initialise relational DB: {e}")
        print("[WARNING] App will still start — DB features may be unavailable.")
    yield
    # Shutdown — close all connection pools
    await close_db()
    await close_mongo()


app = FastAPI(
    title="AI Requirement Intelligence Assistant",
    description="Multi-agent requirement analysis powered by LangGraph + Groq llama-3.3-70b",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}