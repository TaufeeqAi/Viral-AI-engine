import logging
from fastmcp import FastMCP
from pydantic import HttpUrl
from mcp_servers.crawler_mcp.core.crawler import ProductionCrawler, ExtractedPost
from mcp_servers.crawler_mcp.core.browser_manager import BrowserManager

logger = logging.getLogger(__name__)
browser_manager = BrowserManager()
crawler = ProductionCrawler(browser_manager)

def register_general_tools(mcp: FastMCP):
    @mcp.tool()
    async def crawl_and_extract(url: HttpUrl) -> ExtractedPost:
        """
        Crawls a dynamic webpage and extracts a single, normalized post or mention.
        This is a versatile tool for general-purpose data extraction from various sources.

        :param url: The URL of the page to crawl.
        :returns: A structured ExtractedPost object.
        """
        logger.info(f"General tool: crawl_and_extract called for {url}")
        # This function is now a high-level tool that uses other more specific crawlers
        # We'll use the social media crawler as a generic example here
        posts = await crawler.crawl_social_media_posts(url, 1)
        return posts[0] if posts else None