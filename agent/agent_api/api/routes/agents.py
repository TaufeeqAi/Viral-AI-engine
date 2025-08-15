# api/routes/agents.py
import logging
import uuid
from typing import List, Dict, Any, Optional # MODIFIED: Added Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, ValidationError

from ...models.agent_config import AgentConfig, AgentSecrets, Settings, AgentTool
from ..dependencies import get_current_user, get_db_manager, get_agent_manager

logger = logging.getLogger(__name__)

router = APIRouter()

class CreateAgentRequest(BaseModel):
    """Pydantic model for the agent creation request body."""
    name: str = "NewBot"
    modelProvider: str = "groq"
    settings: Dict[str, Any]
    system: str = ""
    bio: List[str] = []
    lore: List[str] = []
    knowledge: List[str] = []
    messageExamples: Optional[List[Dict[str, str]]] = None # MODIFIED: Added Optional
    style: Optional[str] = None # MODIFIED: Added Optional
    tools: List[AgentTool] = []

@router.post("/create", response_model=AgentConfig, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_request: CreateAgentRequest,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager),
    agent_manager=Depends(get_agent_manager)
):
    """Create a new agent for the authenticated user."""
    logger.info(f"User '{current_user}' is creating a new agent.")
    
    try:
        # Parse secrets and settings
        secrets_from_json = agent_request.settings.get("secrets", {})
        voice_settings = agent_request.settings.get("voice", {})

        agent_secrets_instance = AgentSecrets(**secrets_from_json)
        logger.debug(f"Parsed AgentSecrets: {agent_secrets_instance.model_dump_json(exclude_none=True)}")

        settings_instance = Settings(
            model=agent_request.settings.get("model", "llama3-8b-8192"),
            temperature=agent_request.settings.get("temperature", 0.7),
            maxTokens=agent_request.settings.get("maxTokens", 8192),
            secrets=agent_secrets_instance,
            voice=voice_settings if voice_settings else None
        )

        # Create agent config
        agent_config = AgentConfig(
            id=str(uuid.uuid4()),
            user_id=current_user,
            name=agent_request.name,
            modelProvider=agent_request.modelProvider,
            settings=settings_instance,
            system=agent_request.system,
            bio=agent_request.bio,
            lore=agent_request.lore,
            knowledge=agent_request.knowledge,
            messageExamples=agent_request.messageExamples,
            style=agent_request.style,
            tools=agent_request.tools
        )

        # Save to database
        agent_id = await db_manager.save_agent_config(agent_config)
        agent_config.id = agent_id

        # Initialize agent instance
        from ..lifespan import LOCAL_MODE
        # MODIFIED: The create_dynamic_agent_instance method in agent_manager.py
        # MUST return a tuple of exactly 4 elements:
        # (executor, mcp_client, discord_bot_id, telegram_bot_id)
        # If a bot ID is not applicable, it should return None for that position.
        executor, mcp_client, discord_bot_id, telegram_bot_id = \
            await agent_manager.create_dynamic_agent_instance(agent_config, LOCAL_MODE)
        
        agent_manager.add_initialized_agent(
            agent_config.id,
            agent_config.name,
            executor,
            mcp_client,
            discord_bot_id=discord_bot_id,
            telegram_bot_id=telegram_bot_id
        )
        
        logger.info(f"Agent '{agent_config.name}' (ID: {agent_config.id}) created and initialized by user '{current_user}'.")
        return agent_config
        
    except ValidationError as e:
        logger.error(f"Validation Error creating agent: {e.errors()}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid agent configuration: {e.errors()}"
        )
    except Exception as e:
        logger.error(f"Error creating agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to create agent: {e}"
        )

@router.get("/list", response_model=List[AgentConfig])
async def list_agents(
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager)
):
    """List all agents for the authenticated user."""
    logger.info(f"User '{current_user}' is listing all agents.")
    
    try:
        configs = await db_manager.get_all_agent_configs()
        return configs
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to list agents: {e}"
        )
    
##get agent by id
@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent_detail(agent_id: str, current_user = Depends(get_current_user), db_manager=Depends(get_db_manager)):
    logger.info(f"User '{current_user}' is Fetching agent by its ID.")
    try:
        agent = await db_manager.get_agent_config(agent_id)
        # Add authorization check
        if not agent or agent.user_id != current_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found or unauthorized.")
        return agent
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Error fetching agent by its Id: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to get agent by its Id: {e}"
        )
    

# NOTE: The update_agent route was commented out in your provided code.
# If you uncomment it, ensure it also handles the 4-tuple return from create_dynamic_agent_instance
# and includes proper authorization checks.

@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
async def delete_agent(
    agent_id: str,
    current_user: str = Depends(get_current_user),
    db_manager=Depends(get_db_manager),
    agent_manager=Depends(get_agent_manager)
):
    """Delete an agent owned by the authenticated user."""
    logger.info(f"User '{current_user}' is deleting agent '{agent_id}'.")
    
    # Check if agent exists and user has permission
    agent_config_from_db = await db_manager.get_agent_config(agent_id)
    if not agent_config_from_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Agent with ID {agent_id} not found."
        )

    if agent_config_from_db.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You are not authorized to delete this agent."
        )

    try:
        await agent_manager.shutdown_specific_agent(agent_id)
        await db_manager.delete_agent_config(agent_id)
        
        return {"message": f"Agent '{agent_id}' deleted successfully by user '{current_user}'."}
    except Exception as e:
        logger.error(f"Failed to delete agent '{agent_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to delete agent: {e}"
        )
