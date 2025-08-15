import logging
from fastmcp import FastMCP
from pydantic import HttpUrl, PositiveInt
from typing import List, Dict, Any
from mcp_servers.crawler_mcp.core.crawler import ProductionCrawler, ExtractedPost, ExtractedProduct
from mcp_servers.crawler_mcp.core.browser_manager import BrowserManager

logger = logging.getLogger(__name__)
browser_manager = BrowserManager()
crawler = ProductionCrawler(browser_manager)

def register_specialized_tools(mcp: FastMCP):
    @mcp.tool()
    async def crawl_social_media_posts(url: HttpUrl, post_count: PositiveInt = 5) -> List[ExtractedPost]:
        """
        Optimized to crawl and extract a specific number of recent posts from social media feeds
        (e.g., X, Reddit).

        :param url: The URL of the social media page.
        :param post_count: The number of posts to retrieve.
        :returns: A list of structured ExtractedPost objects.
        """
        logger.info(f"Specialized tool: crawl_social_media_posts called for {url}")
        return await crawler.crawl_social_media_posts(url, post_count)

    @mcp.tool()
    async def extract_product_info(url: HttpUrl) -> ExtractedProduct:
        """
        Extracts structured product information (title, price, rating, reviews)
        from a product page on an e-commerce site.

        :param url: The URL of the product page.
        :returns: A structured ExtractedProduct object.
        """
        logger.info(f"Specialized tool: extract_product_info called for {url}")
        return await crawler.extract_product_info(url)

    @mcp.tool()
    async def extract_comments(url: HttpUrl, post_id: str) -> List[Dict[str, Any]]:
        """
        Designed to go deep into a specific post and extract all associated comments.

        :param url: The base URL of the site.
        :param post_id: The ID of the post to extract comments from.
        :returns: A list of dictionaries, each representing a comment.
        """
        logger.info(f"Specialized tool: extract_comments called for {url} and post ID {post_id}")
        return await crawler.extract_comments(url, post_id)
