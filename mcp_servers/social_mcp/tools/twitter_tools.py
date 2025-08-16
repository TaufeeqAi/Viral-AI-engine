import asyncio
import logging
import os
import warnings
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, HttpUrl
import tweepy

from tweepy.client import Response
from dotenv import load_dotenv

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress SyntaxWarning from Tweepy docstrings
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Load environment variables from .env file (if present)
load_dotenv()

# --- Twitter API Client Encapsulation ---
class TwitterClient:
    """
    Manages the Tweepy clients, ensuring they are initialized with
    environment variables and are ready for use.
    """
    _v2_client = None
    _v1_api = None

    def __init__(self):
        try:
            self._initialize_clients()
        except EnvironmentError as e:
            logger.error(f"Failed to initialize Twitter clients: {e}")

    def _initialize_clients(self):
        """Initializes both Twitter API v2 and v1.1 clients with detailed logging."""
        logger.info("Attempting to load Twitter API environment variables...")
        required_env_vars = [
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
            "TWITTER_BEARER_TOKEN",
        ]
        
        missing_vars = []
        for var in required_env_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
                logger.debug(f"{var}: Missing")
            else:
                logger.debug(f"{var}: Found")

        if missing_vars:
            error_msg = f"Missing one or more required Twitter API environment variables: {', '.join(missing_vars)}."
            logger.error(error_msg)
            raise EnvironmentError(error_msg)

        logger.info("All required Twitter API environment variables found. Initializing Tweepy clients...")

        self._v2_client = tweepy.Client(
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN")
        )

        auth = tweepy.OAuth1UserHandler(
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )
        self._v1_api = tweepy.API(auth)
        logger.info("Twitter API clients initialized successfully.")

    @property
    def v2(self) -> tweepy.Client:
        if self._v2_client is None:
            raise RuntimeError("Twitter v2 client is not initialized.")
        return self._v2_client

    @property
    def v1(self) -> tweepy.API:
        if self._v1_api is None:
            raise RuntimeError("Twitter v1.1 API is not initialized.")
        return self._v1_api

# Initialize the client globally for the module
twitter_manager = TwitterClient()

# --- Tool Registration (FastMCP) ---
def register_twitter_tools(mcp):
    """
    Registers all Twitter-related tools with the FastMCP instance.
    """
    # This check is not needed as the client initialization handles the failure.
    # The RuntimeError is now raised if a tool is called without a valid client.

    # --- User Management Tools ---
    @mcp.tool(name="get_twitter_user_profile", description="Get detailed profile information for a user by their user ID.")
    async def get_twitter_user_profile(user_id: str) -> Dict[str, Any]:
        """
        Fetches user profile by user ID.
        :param user_id: The ID of the user to look up.
        """
        logger.info(f"Tool 'get_twitter_user_profile' called for user_id: {user_id}")
        try:
            response: Response = twitter_manager.v2.get_user(
                id=user_id,
                user_fields=["id", "name", "username", "profile_image_url", "description", "public_metrics"]
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting user profile for user_id {user_id}: {e}")
            return {"error": "Failed to fetch user profile", "message": str(e)}

    @mcp.tool(name="get_user_by_screen_name", description="Fetches a user by their screen name (username).")
    async def get_user_by_screen_name(screen_name: str) -> Dict[str, Any]:
        """
        Fetches user by screen name.
        :param screen_name: The screen name/username of the user.
        """
        logger.info(f"Tool 'get_user_by_screen_name' called for screen_name: {screen_name}")
        try:
            response: Response = twitter_manager.v2.get_user(
                username=screen_name,
                user_fields=["id", "name", "username", "profile_image_url", "description", "public_metrics"]
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting user by screen name {screen_name}: {e}")
            return {"error": "Failed to fetch user", "message": str(e)}

    @mcp.tool(name="get_user_by_id", description="Fetches a user by their ID (same as get_twitter_user_profile).")
    async def get_user_by_id(user_id: str) -> Dict[str, Any]:
        """
        Fetches user by ID.
        :param user_id: The ID of the user to look up.
        """
        return await get_twitter_user_profile(user_id)

    @mcp.tool(name="get_user_followers", description="Retrieves a list of followers for a given user.")
    async def get_user_followers(user_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves a list of followers for a given user.
        :param user_id: The user ID whose followers are to be retrieved.
        :param count: The number of followers to retrieve per page. Max 100 for V2 API.
        """
        logger.info(f"Tool 'get_user_followers' called for user_id: {user_id}")
        try:
            response: Response = twitter_manager.v2.get_users_followers(
                id=user_id,
                max_results=min(count, 100),
                user_fields=["id", "name", "username"]
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting followers for user_id {user_id}: {e}")
            return {"error": "Failed to fetch followers", "message": str(e)}

    @mcp.tool(name="get_user_following", description="Retrieves users the given user is following.")
    async def get_user_following(user_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves a list of users whom the given user is following.
        :param user_id: The user ID whose following list is to be retrieved.
        :param count: The number of users to retrieve per page. Max 100 for V2 API.
        """
        logger.info(f"Tool 'get_user_following' called for user_id: {user_id}")
        try:
            response: Response = twitter_manager.v2.get_users_following(
                id=user_id,
                max_results=min(count, 100),
                user_fields=["id", "name", "username"]
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting users being followed for user_id {user_id}: {e}")
            return {"error": "Failed to fetch following list", "message": str(e)}

    # --- Tweet Management Tools ---
    @mcp.tool(name="post_tweet", description="Post a tweet with optional media and reply information.")
    async def post_tweet(text: str, reply_to_tweet_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Posts a tweet.
        :param text: The text content of the tweet. Max 280 characters.
        :param reply_to_tweet_id: The ID of the tweet to reply to.
        """
        logger.info(f"Tool 'post_tweet' called with text: '{text[:50]}...'")
        try:
            response: Response = twitter_manager.v2.create_tweet(
                text=text,
                in_reply_to_tweet_id=reply_to_tweet_id
            )
            return response.data
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return {"error": "Failed to post tweet", "message": str(e)}

    @mcp.tool(name="delete_tweet", description="Delete a tweet by its ID.")
    async def delete_tweet(tweet_id: str) -> Dict[str, Any]:
        """
        Deletes a tweet.
        :param tweet_id: The ID of the tweet to delete.
        """
        logger.info(f"Tool 'delete_tweet' called for tweet_id: {tweet_id}")
        try:
            response: Response = twitter_manager.v2.delete_tweet(id=tweet_id)
            return {"id": tweet_id, "deleted": response.data.get("deleted")}
        except Exception as e:
            logger.error(f"Error deleting tweet {tweet_id}: {e}")
            return {"error": "Failed to delete tweet", "message": str(e)}

    @mcp.tool(name="get_tweet_details", description="Get detailed information about a specific tweet.")
    async def get_tweet_details(tweet_id: str) -> Dict[str, Any]:
        """
        Fetches tweet details.
        :param tweet_id: The ID of the tweet to fetch.
        """
        logger.info(f"Tool 'get_tweet_details' called for tweet_id: {tweet_id}")
        try:
            response: Response = twitter_manager.v2.get_tweet(
                id=tweet_id,
                tweet_fields=["id", "text", "created_at", "author_id", "public_metrics"]
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting tweet details for tweet {tweet_id}: {e}")
            return {"error": "Failed to fetch tweet details", "message": str(e)}

    # --- Timeline & Search Tools ---
    @mcp.tool(name="fetch_user_tweets", description="Fetches a list of recent tweets from a user's timeline.")
    async def fetch_user_tweets(user_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches a list of recent tweets from a user's timeline.
        :param user_id: The ID of the user whose tweets are to be retrieved.
        :param count: Number of tweets to retrieve. Max 100 for V2 API.
        """
        logger.info(f"Tool 'fetch_user_tweets' called for user_id: {user_id}")
        try:
            response: Response = twitter_manager.v2.get_users_tweets(
                id=user_id,
                max_results=min(count, 100),
                tweet_fields=["id", "text", "created_at", "public_metrics"]
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return {"error": "Failed to fetch user tweets", "message": str(e)}

    @mcp.tool(name="search_twitter", description="Search Twitter for recent tweets matching a query.")
    async def search_twitter(query: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Searches Twitter for recent tweets.
        :param query: The search query. Supports operators like #hashtag, from:user, etc.
        :param count: Number of tweets to retrieve. Min 10, Max 100 for search_recent_tweets.
        """
        logger.info(f"Tool 'search_twitter' called with query: '{query}'")
        try:
            response: Response = twitter_manager.v2.search_recent_tweets(
                query=query,
                max_results=min(max(count, 10), 100),
                tweet_fields=["id", "text", "created_at", "public_metrics"]
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error searching Twitter for query '{query}': {e}")
            return {"error": "Failed to perform search", "message": str(e)}

    @mcp.tool(name="get_user_mentions", description="Get tweets mentioning a specific user.")
    async def get_user_mentions(user_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Fetches tweets mentioning a specific user.
        :param user_id: The ID of the user whose mentions are to be retrieved.
        :param count: Number of mentions to retrieve. Max 100 for get_users_mentions.
        """
        logger.info(f"Tool 'get_user_mentions' called for user_id: {user_id}")
        try:
            response: Response = twitter_manager.v2.get_users_mentions(
                id=user_id,
                max_results=min(count, 100),
                tweet_fields=["id", "text", "created_at", "public_metrics"]
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting mentions for user {user_id}: {e}")
            return {"error": "Failed to fetch mentions", "message": str(e)}

    @mcp.tool(name="get_tweet_engagement_metrics", description="Get engagement metrics for a specific tweet.")
    async def get_tweet_engagement_metrics(tweet_id: str) -> Dict[str, Any]:
        """
        Gets engagement metrics for a specific tweet.
        :param tweet_id: The ID of the tweet.
        """
        logger.info(f"Tool 'get_tweet_engagement_metrics' called for tweet_id: {tweet_id}")
        try:
            response: Response = twitter_manager.v2.get_tweet(
                id=tweet_id,
                tweet_fields=["public_metrics"]
            )
            if response.data and response.data.public_metrics:
                return response.data.public_metrics
            return {"message": "No public metrics available for this tweet."}
        except Exception as e:
            logger.error(f"Error getting engagement metrics for tweet {tweet_id}: {e}")
            return {"error": "Failed to get metrics", "message": str(e)}
