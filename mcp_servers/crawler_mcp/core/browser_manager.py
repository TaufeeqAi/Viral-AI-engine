import asyncio
from playwright.async_api import async_playwright, Browser, Playwright
import logging

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages a pool of Playwright browser instances for concurrent crawling tasks.
    """
    def __init__(self, pool_size: int = 5, headless: bool = True):
        self._pool_size = pool_size
        self._headless = headless
        self._playwright = None
        self._browsers = asyncio.Queue()
        self._lock = asyncio.Semaphore(pool_size)

    async def initialize(self):
        """Initializes the Playwright browsers and populates the pool."""
        logger.info(f"Initializing a pool of {self._pool_size} Playwright browsers (headless={self._headless}).")
        self._playwright = await async_playwright().start()
        for _ in range(self._pool_size):
            browser = await self._playwright.chromium.launch(headless=self._headless)
            await self._browsers.put(browser)

    async def get_browser(self) -> Browser:
        """Acquires a browser instance from the pool."""
        await self._lock.acquire()
        return await self._browsers.get()

    async def release_browser(self, browser: Browser):
        """Releases a browser instance back to the pool."""
        await self._browsers.put(browser)
        self._lock.release()

    async def close(self):
        """Closes all browsers and the Playwright instance."""
        while not self._browsers.empty():
            browser = await self._browsers.get()
            await browser.close()
        await self._playwright.stop()
        logger.info("Playwright browser pool has been closed.")

