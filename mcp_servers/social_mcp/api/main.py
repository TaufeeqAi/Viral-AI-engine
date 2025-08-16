import logging
from fastapi import FastAPI
from fastmcp import FastMCP
from dotenv import load_dotenv

# Import the new SocialManager class
from mcp_servers.social_mcp.core.social_manager import SocialManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define the FastMCP server with a unique name
mcp = FastMCP(
    name="social_mcp",
)

# Initialize and register tools using the new manager class
social_manager = SocialManager(mcp_instance=mcp)
social_manager.register_social_tools()

# Mount the MCP server
http_mcp = mcp.http_app(transport="streamable-http")
app = FastAPI(lifespan=http_mcp.router.lifespan_context)
app.mount("/", http_mcp)

@app.get("/health")
async def health_check():
    """A simple health check endpoint."""
    return {"status": "ok", "service": "social_mcp"}
