import os
import logging
from fastapi import FastAPI
from fastmcp import FastMCP
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import tool registration functions
from mcp_servers.social_mcp.tools.reddit_tools import register_reddit_tools
from mcp_servers.social_mcp.tools.tiktok_tools import register_tiktok_tools
from mcp_servers.social_mcp.tools.twitter_tools import register_twitter_tools

# Define the FastMCP server with a unique name
mcp = FastMCP(name="social_mcp")

# Register all the tools from the different modules
register_reddit_tools(mcp)
register_tiktok_tools(mcp)
register_twitter_tools(mcp)

# Mount the MCP server to a FastAPI app
http_mcp = mcp.http_app(transport="streamable-http")
app = FastAPI()
app.mount("/", http_mcp)

@app.get("/health")
async def health_check():
    """A simple health check endpoint."""
    return {"status": "ok", "service": "social_mcp"}