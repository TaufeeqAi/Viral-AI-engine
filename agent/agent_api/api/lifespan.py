# api/lifespan.py
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from ..db.postgres_manager import PostgresManager
from ..core.agent_manager import AgentManager
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

# --------- Configuration ---------
LOCAL_MODE = True
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://cyrene:taufeeq@127.0.0.1:5433/cyrene_auth")

if not POSTGRES_DSN:
    logger.error("POSTGRES_DSN environment variable not set. Application cannot connect to database.")
    raise ValueError("POSTGRES_DSN environment variable not set.")

logger.info(f"Running in LOCAL_MODE: {LOCAL_MODE}")
logger.info(f"[DEBUG] JWT_SECRET_KEY:{os.getenv('JWT_SECRET_KEY')}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for initializing and cleaning up resources.
    Initializes the PostgreSQL database connection pool and agents.
    """
    logger.info("Agent app startup: Initializing global resources...")

    # Initialize database manager
    db_manager_instance = PostgresManager(POSTGRES_DSN)
    await db_manager_instance.connect()
    app.state.db_manager = db_manager_instance
    logger.info("PostgreSQL connection pool initialized and stored in app state.")
    
    # Initialize agent manager
    agent_manager_instance = AgentManager(db_manager_instance)
    app.state.agent_manager = agent_manager_instance

    # Initialize MCP client
    try:
        mcp_client_instance = MultiServerMCPClient()
        app.state.mcp_client = mcp_client_instance
        logger.info("MCP client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}", exc_info=True)
        app.state.mcp_client = None

    # Initialize all agents from database
    try:
        await app.state.agent_manager.initialize_all_agents_from_db(LOCAL_MODE)
        logger.info("All agents initialized from the database on startup.")
    except Exception as e:
        logger.error(f"Failed to initialize agents on startup: {e}", exc_info=True)

    logger.info("Agent app startup complete. Agent is ready.")
    yield

    # Shutdown
    logger.info("Agent app shutdown.")
    await app.state.agent_manager.shutdown_all_agents()
    await app.state.db_manager.close()
    logger.info("PostgreSQL connection pool closed.")