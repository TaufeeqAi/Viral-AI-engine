import logging
from fastmcp import FastMCP
from pydantic import HttpUrl, PositiveInt
from typing import Dict, Any, List
from mcp_servers.crawler_mcp.core.crawler import ProductionCrawler
from mcp_servers.crawler_mcp.core.browser_manager import BrowserManager

logger = logging.getLogger(__name__)
browser_manager = BrowserManager()
crawler = ProductionCrawler(browser_manager)

def register_deep_crawling_tools(mcp: FastMCP):
    @mcp.tool()
    async def bfs_crawl(start_url: HttpUrl, max_depth: PositiveInt = 2) -> List[str]:
        """
        Performs a Breadth-First Search (BFS) to discover and map links from a starting URL.

        :param start_url: The URL to begin the crawl from.
        :param max_depth: The maximum link depth to explore.
        :returns: A list of discovered URLs.
        """
        logger.info(f"Deep crawling tool: bfs_crawl called for {start_url}")
        return await crawler.bfs_crawl(start_url, max_depth)

    @mcp.tool()
    async def dfs_crawl(start_url: HttpUrl, max_depth: PositiveInt = 2) -> List[str]:
        """
        Performs a Depth-First Search (DFS) to explore a website's links.

        :param start_url: The URL to begin the crawl from.
        :param max_depth: The maximum link depth to explore.
        :returns: A list of discovered URLs.
        """
        logger.info(f"Deep crawling tool: dfs_crawl called for {start_url}")
        return await crawler.dfs_crawl(start_url, max_depth)

    @mcp.tool()
    async def smart_scroll_and_crawl(url: HttpUrl, scroll_limit: PositiveInt = 5) -> List[Any]:
        """
        Crawls a page with infinite scrolling content by simulating realistic scrolling.

        :param url: The URL of the page with infinite scrolling.
        :param scroll_limit: The number of times to simulate scrolling.
        :returns: A list of extracted content after scrolling.
        """
        logger.info(f"Deep crawling tool: smart_scroll_and_crawl called for {url}")
        return await crawler.smart_scroll_and_crawl(url, scroll_limit)
