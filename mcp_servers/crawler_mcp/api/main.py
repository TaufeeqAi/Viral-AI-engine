#mcp_servers\crawler_mcp\api\main.py
import os
import logging
from fastapi import FastAPI
from fastmcp import FastMCP
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from mcp_servers.crawler_mcp.core.browser_manager import BrowserManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import tool registration functions
from mcp_servers.crawler_mcp.tools.general_tools import register_general_tools
from mcp_servers.crawler_mcp.tools.specialized_tools import register_specialized_tools
from mcp_servers.crawler_mcp.tools.deep_crawling_tools import register_deep_crawling_tools
from mcp_servers.crawler_mcp.tools.advanced_tools import register_advanced_tools

# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes and shuts down the browser pool."""
    logger.info("Initializing the browser pool on application startup.")
    browser_manager = BrowserManager()
    await browser_manager.initialize()
    app.state.browser_manager = browser_manager
    
    # Yield control to the application to handle requests
    yield
    
    # This code runs after the application shuts down
    logger.info("Closing the browser pool gracefully on shutdown.")
    await app.state.browser_manager.close()

# Define the FastMCP server with a unique name
mcp = FastMCP(name="playwright_crawl_mcp")

# Register all the tools from the different modules
register_general_tools(mcp)
register_specialized_tools(mcp)
register_deep_crawling_tools(mcp)
register_advanced_tools(mcp)

# Mount the MCP server to a FastAPI app
http_mcp = mcp.http_app(transport="streamable-http")
app = FastAPI(lifespan=http_mcp.router.lifespan_context)
app.mount("/", http_mcp)


@app.get("/health")
async def health_check():
    """A simple health check endpoint."""
    return {"status": "ok", "service": "playwright_crawl_mcp"}
