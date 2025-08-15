import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables

load_dotenv()

# Database URL from environment variable
DATABASE_URL = "postgresql+asyncpg://cyrene:taufeeq@127.0.0.1:5433/cyrene_auth"

# Create engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# Base class for models - ALL models in the project will inherit from this
Base = declarative_base()

# ✅ Dependency to get an async DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ✅ Async create_tables function
async def create_tables():
    """Create all tables defined in Base.metadata."""
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            print("[DB] Tables checked/created successfully (async).")
        except Exception as e:
            print(f"[DB] Table creation failed (async): {e}")