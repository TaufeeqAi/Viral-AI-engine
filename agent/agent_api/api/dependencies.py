# api/dependencies.py
import os
import base64
import logging
from typing import Annotated, AsyncGenerator
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv

# --- New Imports for Database and User Lookup ---
from sqlalchemy.ext.asyncio import AsyncSession # Import AsyncSession
# CORRECTED IMPORT: Changed 'get_session' to 'get_db'
from agent.db_core.core import get_db as get_session_dependency # Renamed for clarity in this file
# Assuming your User ORM model is here
from agent.db_core.models.user import User 
# Assuming these are in your token_auth service
from agent.ws_api.services.token_auth import verify_token, get_user_by_username 

# Assuming these exist and are used for app.state
from agent.agent_api.db.postgres_manager import PostgresManager 
from ..core.agent_manager import AgentManager 


# --------- Load environment variables ---------
load_dotenv()

# --------- Logging Setup ---------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- JWT Configuration ---
# Ensure these environment variables are set in your .env file
SECRET_KEY = base64.b64decode(os.getenv("JWT_SECRET_KEY"))
ALGORITHM = "HS256"

# The OAuth2PasswordBearer class will handle token extraction from the header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/login")

# --- Database Session Dependency ---
# This dependency provides an AsyncSession to other dependencies/routes
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a SQLAlchemy AsyncSession."""
    # Use the renamed imported dependency
    async for session in get_session_dependency(): 
        yield session

# --- Current User Dependency (Returns User ID/UUID) ---
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)] # Inject the database session
) -> str: # This dependency will now return the user's UUID (as a string)
    """
    Dependency that validates a JWT token, fetches the user from the database,
    and returns the user's UUID (ID).
    """
    logger.info(f"🛡️ [Dependencies] Received Token for authentication.")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Use the verify_token function from your token_auth service
        # This function should decode the JWT and return a TokenData object (or similar)
        # that contains the 'sub' (username)
        token_data = verify_token(token, token_type="access")
        if token_data is None:
            logger.warning("📦 [Dependencies] Token verification failed (token_data is None).")
            raise credentials_exception
        
        logger.info(f"📦 [Dependencies] Decoded JWT Payload (bot-api): {token_data.dict()}")

        # Fetch the user from the database using the username from the token
        # This requires get_user_by_username to be available and accept AsyncSession
        user = await get_user_by_username(db_session, token_data.username)
        if user is None:
            logger.warning(f"📦 [Dependencies] User '{token_data.username}' not found in DB after token validation.")
            raise credentials_exception
        
        # Return the user's UUID (ID)
        logger.info(f"📦 [Dependencies] Authenticated user ID: {user.id}")
        return str(user.id) # Ensure it's returned as a string UUID

    except JWTError as e:
        logger.error(f"❌ [Dependencies] JWT Error during token decoding: {e}", exc_info=True)
        raise credentials_exception
    except Exception as e:
        logger.error(f"❌ [Dependencies] Unexpected error during authentication process: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication."
        )

# Type alias for easy use in route handlers
CurrentUser = Annotated[str, Depends(get_current_user)]

def get_db_manager(request: Request) -> PostgresManager: # Add type hint for clarity
    """Get the database manager from app state."""
    if not hasattr(request.app.state, "db_manager") or request.app.state.db_manager is None:
        logger.error("❌ [Dependencies] db_manager not found in app.state.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database manager not initialized."
        )
    return request.app.state.db_manager

def get_agent_manager(request: Request) -> AgentManager: # Add type hint for clarity
    """Get the agent manager from app state."""
    if not hasattr(request.app.state, "agent_manager") or request.app.state.agent_manager is None:
        logger.error("❌ [Dependencies] agent_manager not found in app.state.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent manager not initialized."
        )
    return request.app.state.agent_manager

def get_mcp_client(request: Request):
    """Get the MCP client from app state."""
    if not hasattr(request.app.state, "mcp_client") or request.app.state.mcp_client is None:
        logger.error("❌ [Dependencies] mcp_client not found in app.state.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MCP client not initialized."
        )
    return request.app.state.mcp_client
