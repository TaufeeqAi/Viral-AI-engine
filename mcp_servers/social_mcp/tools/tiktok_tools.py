# mcp_servers/social_mcp/tools/tiktok_tools.py

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl
from TikTokApi import TikTokApi
# Use generic Exception handling instead of specific TikTokAPIError
from dotenv import load_dotenv

# --- Important Note on Unofficial API ---
# This library is an unofficial API wrapper. It works by simulating a browser to access
# TikTok's public data, as there is no official public API. This means it is fragile
# and can break if TikTok changes its website or bot detection methods.
# You must have Playwright and a browser installed (e.g., Chromium) for this to work.
# To install: pip install playwright && playwright install chromium

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file (if present)
load_dotenv()

# --- TikTok API Client Encapsulation ---
class TikTokClient:
    """
    Manages the TikTokApi client instance.
    The TikTokApi requires an asynchronous context manager, so this class
    handles the asynchronous initialization and provides the client instance.
    """
    _api_instance = None

    @classmethod
    async def get_instance(cls):
        """Returns a singleton instance of the TikTokApi client."""
        if cls._api_instance is None:
            # The TikTokApi must be initialized asynchronously
            cls._api_instance = TikTokApi()
            await cls._api_instance.init()
        return cls._api_instance

# --- Tool Registration (FastMCP) ---
def register_tiktok_tools(mcp):
    """
    Registers all TikTok-related tools with the FastMCP instance.
    
    This function uses a helper class to manage the TikTokApi client.
    The tools are designed to provide AI agents with programmatic access to
    public TikTok data.
    """
    
    # --- Content & User Retrieval ---
    @mcp.tool(name="get_user_profile", description="Get detailed profile information for a user by their username.")
    async def get_user_profile(username: str) -> Dict[str, Any]:
        """
        Fetches user profile information, including statistics and bio.
        :param username: The username of the TikTok user (e.g., 'charlidamelio').
        """
        logger.info(f"Tool 'get_user_profile' called for username: {username}")
        try:
            api = await TikTokClient.get_instance()
            user_info = await api.user(username=username).info()
            return user_info.as_dict
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting user profile for {username}: {e}")
            return {"error": "Failed to fetch user profile", "message": str(e)}

    @mcp.tool(name="get_user_videos", description="Fetches a list of videos uploaded by a specific user.")
    async def get_user_videos(username: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves a list of recent videos for a user.
        :param username: The username of the TikTok user.
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info(f"Tool 'get_user_videos' called for username: {username}")
        try:
            api = await TikTokClient.get_instance()
            user_videos = api.user(username=username).videos()
            videos_list = [v.as_dict for v in await anext(user_videos)]
            return videos_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting videos for {username}: {e}")
            return {"error": "Failed to fetch user videos", "message": str(e)}
        except StopAsyncIteration:
            return []

    @mcp.tool(name="get_video_details", description="Get detailed information about a specific video by its URL.")
    async def get_video_details(url: HttpUrl) -> Dict[str, Any]:
        """
        Fetches video details, including description, metrics, and author info.
        :param url: The full URL of the TikTok video.
        """
        logger.info(f"Tool 'get_video_details' called for url: {url}")
        try:
            api = await TikTokClient.get_instance()
            video_info = await api.video(url=url).info()
            return video_info.as_dict
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting video details for {url}: {e}")
            return {"error": "Failed to fetch video details", "message": str(e)}

    @mcp.tool(name="get_video_comments", description="Fetches a list of comments for a specific video by its URL.")
    async def get_video_comments(url: HttpUrl, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves a list of comments for a video.
        :param url: The full URL of the TikTok video.
        :param count: The number of comments to retrieve (default is 20).
        """
        logger.info(f"Tool 'get_video_comments' called for url: {url}")
        try:
            api = await TikTokClient.get_instance()
            video_comments = api.video(url=url).comments()
            comments_list = [c.as_dict for c in await anext(video_comments)]
            return comments_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting comments for {url}: {e}")
            return {"error": "Failed to fetch comments", "message": str(e)}
        except StopAsyncIteration:
            return []
            
    # --- Trending & Search ---
    @mcp.tool(name="get_trending_videos", description="Fetches a list of currently trending videos.")
    async def get_trending_videos(count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves the top trending videos from the 'For You' page.
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info("Tool 'get_trending_videos' called.")
        try:
            api = await TikTokClient.get_instance()
            trending_videos = api.trending.videos()
            videos_list = [v.as_dict for v in await anext(trending_videos)]
            return videos_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting trending videos: {e}")
            return {"error": "Failed to fetch trending videos", "message": str(e)}
        except StopAsyncIteration:
            return []

    @mcp.tool(name="search_videos", description="Search TikTok for videos matching a query.")
    async def search_videos(query: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for videos using a keyword or phrase.
        :param query: The search term (e.g., 'cat videos').
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info(f"Tool 'search_videos' called for query: {query}")
        try:
            api = await TikTokClient.get_instance()
            search_results = api.search.videos(keyword=query)
            videos_list = [v.as_dict for v in await anext(search_results)]
            return videos_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error searching for videos with query '{query}': {e}")
            return {"error": "Failed to perform video search", "message": str(e)}
        except StopAsyncIteration:
            return []
            
    @mcp.tool(name="search_users", description="Search TikTok for users matching a username query.")
    async def search_users(query: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for users using a keyword or phrase.
        :param query: The search term (e.g., 'mrbeast').
        :param count: The number of users to retrieve (default is 20).
        """
        logger.info(f"Tool 'search_users' called for query: {query}")
        try:
            api = await TikTokClient.get_instance()
            search_results = api.search.users(keyword=query)
            users_list = [u.as_dict for u in await anext(search_results)]
            return users_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error searching for users with query '{query}': {e}")
            return {"error": "Failed to perform user search", "message": str(e)}
        except StopAsyncIteration:
            return []
    
    @mcp.tool(name="get_hashtag_videos", description="Fetches videos related to a specific hashtag.")
    async def get_hashtag_videos(hashtag: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves videos associated with a given hashtag.
        :param hashtag: The hashtag to search for (e.g., 'aiart').
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info(f"Tool 'get_hashtag_videos' called for hashtag: {hashtag}")
        try:
            api = await TikTokClient.get_instance()
            hashtag_videos = api.hashtag(name=hashtag).videos()
            videos_list = [v.as_dict for v in await anext(hashtag_videos)]
            return videos_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting videos for hashtag '{hashtag}': {e}")
            return {"error": "Failed to fetch hashtag videos", "message": str(e)}
        except StopAsyncIteration:
            return []
    
    # --- Audio & Playlist Discovery ---
    @mcp.tool(name="get_sound_videos", description="Fetches videos that use a specific sound or audio clip.")
    async def get_sound_videos(sound_id: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves videos associated with a specific sound ID.
        :param sound_id: The unique ID of the TikTok sound.
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info(f"Tool 'get_sound_videos' called for sound_id: {sound_id}")
        try:
            api = await TikTokClient.get_instance()
            sound_videos = api.sound(id=sound_id).videos()
            videos_list = [v.as_dict for v in await anext(sound_videos)]
            return videos_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting videos for sound_id '{sound_id}': {e}")
            return {"error": "Failed to fetch sound videos", "message": str(e)}
        except StopAsyncIteration:
            return []

    # --- NEW TOOLS ---
    # 📊 Scoring & Trend Prediction Tools
    @mcp.tool(name="get_regional_trending_videos", description="Fetches trending videos from a specific country or region.")
    async def get_regional_trending_videos(region: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves trending videos for a specified region.
        :param region: The two-letter country code (e.g., 'US', 'IN', 'JP').
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info(f"Tool 'get_regional_trending_videos' called for region: {region}")
        try:
            api = await TikTokClient.get_instance()
            trending_videos = api.trending.videos(region=region)
            videos_list = [v.as_dict for v in await anext(trending_videos)]
            return videos_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting trending videos for region '{region}': {e}")
            return {"error": "Failed to fetch regional trending videos", "message": str(e)}
        except StopAsyncIteration:
            return []

    @mcp.tool(name="get_hashtag_metrics", description="Fetches key metrics for a specific hashtag.")
    async def get_hashtag_metrics(hashtag: str) -> Dict[str, Any]:
        """
        Retrieves public metrics for a given hashtag, such as total video count and view count.
        :param hashtag: The hashtag to search for (e.g., 'aiart').
        """
        logger.info(f"Tool 'get_hashtag_metrics' called for hashtag: {hashtag}")
        try:
            api = await TikTokClient.get_instance()
            hashtag_info = await api.hashtag(name=hashtag).info()
            # The API response often contains a "challenge" object with metrics
            metrics = hashtag_info.get("challenge", {})
            return {
                "hashtag_name": metrics.get("title", hashtag),
                "video_count": metrics.get("stats", {}).get("videoCount"),
                "view_count": metrics.get("stats", {}).get("viewCount"),
            }
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting hashtag metrics for '{hashtag}': {e}")
            return {"error": "Failed to fetch hashtag metrics", "message": str(e)}

    @mcp.tool(name="get_video_public_metrics", description="Fetches only the public engagement metrics for a video.")
    async def get_video_public_metrics(url: HttpUrl) -> Dict[str, Any]:
        """
        Fetches public metrics for a video (e.g., likes, comments, shares).
        This is a lightweight tool for scoring.
        :param url: The full URL of the TikTok video.
        """
        logger.info(f"Tool 'get_video_public_metrics' called for url: {url}")
        try:
            api = await TikTokClient.get_instance()
            video_info = await api.video(url=url).info()
            # The public metrics are typically nested under a 'stats' key
            metrics = video_info.get("stats", {})
            return {
                "like_count": metrics.get("diggCount"),
                "comment_count": metrics.get("commentCount"),
                "share_count": metrics.get("shareCount"),
                "view_count": metrics.get("playCount"),
            }
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting video metrics for {url}: {e}")
            return {"error": "Failed to fetch video metrics", "message": str(e)}

    # 🔍 Search & Mentions Tools
    # Note: TikTokApi does not currently support searching by date range, so this
    # tool is a conceptual placeholder. The tool will simply search for the query.
    @mcp.tool(name="search_videos_by_date", description="Searches TikTok for videos matching a query, with a conceptual date filter.")
    async def search_videos_by_date(query: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for videos using a keyword or phrase, returning the most recent results.
        :param query: The search term (e.g., 'cat videos').
        :param count: The number of videos to retrieve (default is 20).
        """
        logger.info(f"Tool 'search_videos_by_date' called for query: {query}")
        return await search_videos(query=query, count=count)

    @mcp.tool(name="search_users_by_keyword", description="Searches TikTok for users matching a keyword in their profile or name.")
    async def search_users_by_keyword(query: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for users using a keyword or phrase.
        :param query: The search term (e.g., 'crypto investor').
        :param count: The number of users to retrieve (default is 20).
        """
        logger.info(f"Tool 'search_users_by_keyword' called for query: {query}")
        return await search_users(query=query, count=count)

    # 🫂 Audience & Personality Analysis
    @mcp.tool(name="get_user_followers_list", description="Fetches a list of followers for a specific user.")
    async def get_user_followers_list(username: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves a list of followers for a TikTok user.
        :param username: The username of the TikTok user.
        :param count: The number of followers to retrieve (default is 20).
        """
        logger.info(f"Tool 'get_user_followers_list' called for username: {username}")
        try:
            api = await TikTokClient.get_instance()
            # The 'followers' method returns an async iterator
            followers_iter = api.user(username=username).followers()
            followers_list = [f.as_dict for f in await anext(followers_iter)]
            return followers_list[:count]
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting followers for {username}: {e}")
            return {"error": "Failed to fetch user followers", "message": str(e)}
        except StopAsyncIteration:
            return []

    @mcp.tool(name="get_user_video_stats", description="Fetches a quick list of a user's videos and their key statistics.")
    async def get_user_video_stats(username: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves a list of a user's recent videos with their engagement metrics.
        :param username: The username of the TikTok user.
        :param count: The number of videos to analyze (default is 20).
        """
        logger.info(f"Tool 'get_user_video_stats' called for username: {username}")
        try:
            api = await TikTokClient.get_instance()
            user_videos = api.user(username=username).videos()
            videos_stats = []
            async for v in user_videos:
                videos_stats.append({
                    "id": v.as_dict.get("id"),
                    "description": v.as_dict.get("desc"),
                    "stats": v.as_dict.get("stats", {})
                })
                if len(videos_stats) >= count:
                    break
            return videos_stats
        except Exception as e:  # Use generic Exception instead of TikTokAPIError
            logger.error(f"Error getting user video stats for {username}: {e}")
            return {"error": "Failed to fetch user video stats", "message": str(e)}