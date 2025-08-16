#mcp_servers\crawler_mcp\tools\advanced_tools.py
import logging
from fastmcp import FastMCP
from pydantic import HttpUrl
from typing import Dict, Any
from mcp_servers.crawler_mcp.core.crawler import ProductionCrawler
from mcp_servers.crawler_mcp.core.browser_manager import BrowserManager

logger = logging.getLogger(__name__)
browser_manager = BrowserManager()
crawler = ProductionCrawler(browser_manager)

def register_advanced_tools(mcp: FastMCP):
    @mcp.tool()
    async def perform_search(url: HttpUrl, query: str) -> Dict[str, Any]:
        """
        Navigates to a webpage, enters a query into a search bar, and submits the form,
        returning the results page's content.

        :param url: The URL of the page with a search bar.
        :param query: The search term.
        :returns: A dictionary with the search results.
        """
        logger.info(f"Advanced tool: perform_search called for {url} with query '{query}'")
        return await crawler.perform_search(url, query)

    @mcp.tool()
    async def interact_with_form(url: HttpUrl, form_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Fills out a form on a webpage with a given dictionary of data and submits it.

        :param url: The URL of the page with the form.
        :param form_data: A dictionary of form field names and their values.
        :returns: A dictionary confirming the successful submission.
        """
        logger.info(f"Advanced tool: interact_with_form called for {url}")
        return await crawler.interact_with_form(url, form_data)

    @mcp.tool()
    async def execute_js_snippet(url: HttpUrl, js_code: str) -> Dict[str, Any]:
        """
        Executes a custom JavaScript snippet on a webpage, which can be used to
        interact with the DOM or override client-side scripts.

        :param url: The URL of the page to execute JavaScript on.
        :param js_code: The JavaScript code as a string.
        :returns: A dictionary with the result of the JavaScript execution.
        """
        logger.info(f"Advanced tool: execute_js_snippet called for {url}")
        return await crawler.execute_js_snippet(url, js_code)
