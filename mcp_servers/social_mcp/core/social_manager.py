import logging
from fastmcp import FastMCP
from mcp_servers.social_mcp.tools.reddit_tools import register_reddit_tools
from mcp_servers.social_mcp.tools.tiktok_tools import register_tiktok_tools
from mcp_servers.social_mcp.tools.twitter_tools import register_twitter_tools

logger = logging.getLogger(__name__)

class SocialManager:
    """
    Manages the registration and lifecycle of all social media tools.

    This class centralizes the logic for initializing and registering
    the Reddit, TikTok, and Twitter toolsets, making the main application file
    cleaner and more organized.
    """
    def __init__(self, mcp_instance: FastMCP):
        self.mcp_instance = mcp_instance

    def register_social_tools(self):
        """
        Registers all available social media tools with the FastMCP instance.
        
        Each tool registration is wrapped in a try/except block to ensure
        that a failure in one tool (e.g., due to missing API keys) does not
        prevent the other tools from being loaded and the server from running.
        """
        logger.info("Starting tool registration for Social MCP.")
        
        # Register Reddit tools
        try:
            register_reddit_tools(self.mcp_instance)
            logger.info("Successfully registered Reddit tools.")
        except Exception as e:
            logger.error(f"Failed to register Reddit tools: {e}")

        # Register TikTok tools
        try:
            register_tiktok_tools(self.mcp_instance)
            logger.info("Successfully registered TikTok tools.")
        except Exception as e:
            logger.error(f"Failed to register TikTok tools: {e}")
            
        # Register Twitter tools
        try:
            register_twitter_tools(self.mcp_instance)
            logger.info("Successfully registered Twitter tools.")
        except Exception as e:
            logger.error(f"Failed to register Twitter tools: {e}")
            
        logger.info("Tool registration complete.")

