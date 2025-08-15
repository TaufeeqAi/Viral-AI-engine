import asyncio
from collections import deque
from playwright.async_api import Page, Locator
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def smart_scroll_strategy(page: Page, scroll_limit: int) -> List[Locator]:
    """
    Simulates human-like scrolling on a page to load dynamic content.
    """
    logger.info("Executing smart scroll strategy...")
    extracted_elements = []
    last_count = 0
    for i in range(scroll_limit):
        # This is where the real logic for "smart scroll physics" would go
        await page.mouse.wheel(0, 1000)
        await page.wait_for_timeout(1000) # Wait for content to load
        
        new_elements = await page.locator("article, div.post").all()
        if len(new_elements) > last_count:
            last_count = len(new_elements)
            extracted_elements.extend(new_elements)
        else:
            logger.info("No new content loaded, stopping scroll.")
            break
            
    return extracted_elements

async def bfs_crawl_strategy(page: Page, start_url: str, max_depth: int) -> List[str]:
    """
    Performs a Breadth-First Search to discover links.
    """
    logger.info("Executing BFS crawl strategy...")
    visited_urls = set()
    queue = deque([(start_url, 0)])
    discovered_urls = []

    while queue:
        url, depth = queue.popleft()
        if depth > max_depth or url in visited_urls:
            continue

        try:
            await page.goto(url, wait_until="domcontentloaded")
            visited_urls.add(url)
            discovered_urls.append(url)
            
            if depth < max_depth:
                links = await page.evaluate('''() => 
                    Array.from(document.querySelectorAll("a")).map(a => a.href)
                ''')
                for link in links:
                    if link.startswith(start_url) and link not in visited_urls:
                        queue.append((link, depth + 1))
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {e}")

    return discovered_urls

async def dfs_crawl_strategy(page: Page, start_url: str, max_depth: int) -> List[str]:
    """
    Performs a Depth-First Search to discover links.
    """
    logger.info("Executing DFS crawl strategy...")
    visited_urls = set()
    stack = [(start_url, 0)]
    discovered_urls = []

    while stack:
        url, depth = stack.pop()
        if depth > max_depth or url in visited_urls:
            continue

        try:
            await page.goto(url, wait_until="domcontentloaded")
            visited_urls.add(url)
            discovered_urls.append(url)
            
            if depth < max_depth:
                links = await page.evaluate('''() => 
                    Array.from(document.querySelectorAll("a")).map(a => a.href)
                ''')
                # Push links to stack in reverse to get proper DFS order
                for link in reversed(links):
                    if link.startswith(start_url) and link not in visited_urls:
                        stack.append((link, depth + 1))
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {e}")

    return discovered_urls