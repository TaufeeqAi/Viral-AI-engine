# api/utils/agent_selector.py
import logging

logger = logging.getLogger(__name__)

def get_agent_by_bot_id(agent_manager, incoming_bot_id: str, platform: str):
    """
    Helper function to find an agent based on its platform-specific bot ID.
    
    Args:
        agent_manager: The agent manager instance
        incoming_bot_id: The bot ID from the incoming message
        platform: The platform name ('discord' or 'telegram')
    
    Returns:
        dict: Agent info if found, None otherwise
    """
    for agent_id, agent_info in agent_manager.get_all_initialized_agents().items():
        if agent_info["name"] == "DefaultBot":
            continue
        
        cached_bot_id = agent_info.get(f"{platform}_bot_id")
        
        # Check if agent has the required tool and matching bot ID
        tool_name = "send_message" if platform == "discord" else f"send_message_{platform}"
        has_tool = agent_info["mcp_client"].tools.get(tool_name) is not None
        
        if has_tool and str(cached_bot_id) == str(incoming_bot_id):
            logger.info(f"Selected agent '{agent_info['name']}' (ID: {agent_id}) for {platform} webhook.")
            return agent_info
    
    logger.warning(f"No suitable agent found with {platform} API keys matching bot ID '{incoming_bot_id}'.")
    return None