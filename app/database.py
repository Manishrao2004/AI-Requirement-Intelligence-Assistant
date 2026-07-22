from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from supabase import create_client, Client as SupabaseClient
from app.config import MONGODB_URL, MONGODB_DB_NAME, SUPABASE_URL, SUPABASE_KEY

# MongoDB (async via motor)
_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None

def get_mongo_db() -> AsyncIOMotorDatabase:
    global _mongo_client, _mongo_db
    if _mongo_db is None:
        _mongo_client = AsyncIOMotorClient(MONGODB_URL)
        _mongo_db = _mongo_client[MONGODB_DB_NAME]
    return _mongo_db

async def close_mongo():
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None

# Supabase
_supabase_client: SupabaseClient | None = None

def get_supabase() -> SupabaseClient | None:
    global _supabase_client
    if _supabase_client is None and SUPABASE_URL and SUPABASE_KEY:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client
