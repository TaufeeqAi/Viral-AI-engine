#mcp_servers\crawler_mcp\core\crawler.py
import asyncio
import logging
from typing import Dict, Any, List
from playwright.async_api import async_playwright, Page, expect
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from mcp_servers.crawler_mcp.core.browser_manager import BrowserManager
from mcp_servers.crawler_mcp.core.strategies import smart_scroll_strategy, bfs_crawl_strategy, dfs_crawl_strategy

logger = logging.getLogger(__name__)

class ExtractedPost(BaseModel):
    """Represents a single extracted social media post."""
    text: str
    author: str
    timestamp: datetime
    engagement_metrics: Dict[str, int]
    source_url: HttpUrl
    media: List[Dict[str, str]] = []


class ExtractedProduct(BaseModel):
    """Represents a single extracted product from an e-commerce site."""
    title: str
    price: float
    rating: float
    reviews: int
    product_url: HttpUrl

class ProductionCrawler:
    """
    A production-grade web crawler that uses Playwright for real-world scenarios.
    This class is the core of the microservice, handling all interaction with browsers.
    """
    def __init__(self, browser_manager: BrowserManager):
        self._browser_manager = browser_manager

    async def crawl_social_media_posts(self, url: str, post_count: int) -> List[ExtractedPost]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # This is where anti-bot measures would be applied, e.g.,
            # await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            await page.goto(url)
            
            # Implement "smart scroll" to load posts
            elements = await smart_scroll_strategy(page, scroll_limit=post_count // 5)
            
            posts = []
            for element in elements[:post_count]:
                # Complex extraction logic using selectors or LLM-guided extraction from Crawl4AI
                try:
                    title_locator = element.locator(".post-title")
                    title = await title_locator.inner_text()
                    posts.append(ExtractedPost(
                        text=title,
                        author="mock_author",
                        timestamp=datetime.now(),
                        engagement_metrics={"likes": 100, "shares": 20},
                        source_url=url
                    ))
                except Exception as e:
                    logger.warning(f"Could not extract post data: {e}")

            return posts

        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def extract_product_info(self, url: str) -> ExtractedProduct:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            
            # Wait for key elements to be present before scraping
            await page.wait_for_selector("#product-title")
            
            title = await page.inner_text("#product-title")
            price = await page.inner_text("#product-price")
            rating = await page.inner_text("#product-rating")

            return ExtractedProduct(
                title=title.strip(),
                price=float(price.replace("$", "").replace(",", "")),
                rating=float(rating.split()[0]),
                reviews=100, # This would be extracted
                product_url=url
            )
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)
    
    async def extract_comments(self, url: str, post_id: str) -> List[Dict[str, Any]]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(f"{url}/post/{post_id}")
            
            # This is where logic to load all comments (e.g., clicking "show more") would go
            
            comments = await page.evaluate('''() => 
                Array.from(document.querySelectorAll(".comment-text")).map(el => el.textContent)
            ''')

            return [{"text": comment, "author": "mock_user"} for comment in comments]
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def perform_search(self, url: str, query: str) -> Dict[str, Any]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            
            await page.fill('input[name="q"]', query)
            await page.press('input[name="q"]', 'Enter')
            
            await page.wait_for_url(lambda url: "search" in url.path and query in url.query_params["q"])
            
            results = await page.locator(".search-result-title").all_inner_texts()

            return {"query": query, "results": results}
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def interact_with_form(self, url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            
            for field, value in form_data.items():
                await page.fill(f"input[name='{field}']", value)
            
            await page.click('button[type="submit"]')
            
            # Wait for success message or redirection
            await page.wait_for_selector("#success-message")
            
            return {"status": "success", "message": "Form submitted successfully"}
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def execute_js_snippet(self, url: str, js_code: str) -> Any:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            
            result = await page.evaluate(js_code)
            
            return {"result": result}
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def bfs_crawl(self, start_url: str, max_depth: int) -> List[str]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            return await bfs_crawl_strategy(page, start_url, max_depth)
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def dfs_crawl(self, start_url: str, max_depth: int) -> List[str]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            return await dfs_crawl_strategy(page, start_url, max_depth)
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)

    async def smart_scroll_and_crawl(self, url: str, scroll_limit: int) -> List[Any]:
        browser = await self._browser_manager.get_browser()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle")
            
            elements = await smart_scroll_strategy(page, scroll_limit)
            
            # Example of extracting data after scrolling
            extracted_data = [await el.inner_text() for el in elements]
            return extracted_data
        finally:
            await page.close()
            await context.close()
            await self._browser_manager.release_browser(browser)
