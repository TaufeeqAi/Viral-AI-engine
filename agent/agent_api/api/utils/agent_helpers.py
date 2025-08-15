# api/utils/agent_helpers.py
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

async def get_and_initialize_agent(db_manager, agent_manager, agent_id: str):
    """
    Helper function to get an agent from the cache or initialize it from the database.
    """
    agent_info = agent_manager.get_initialized_agent(agent_id)
    if agent_info:
        return agent_info

    agent_config = await db_manager.get_agent_config(agent_id)
    if not agent_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Agent with ID '{agent_id}' not found."
        )

    try:
        from ..lifespan import LOCAL_MODE
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
        logger.info(f"Agent '{agent_config.name}' (ID: {agent_config.id}) re-initialized and added to cache.")
        return agent_manager.get_initialized_agent(agent_id)
    except Exception as e:
        logger.error(f"Failed to re-initialize agent '{agent_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to initialize agent '{agent_id}': {e}"
        )