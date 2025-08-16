import os
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, HttpUrl, Field
import praw
from praw.exceptions import RedditAPIException
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- PRAW Client Encapsulation ---
class RedditClient:
    """
    Manages the PRAW client, ensuring it's initialized with environment variables.
    Encapsulating the client allows for cleaner dependency management.
    """
    def __init__(self):
        self._reddit = self._initialize_client()

    def _initialize_client(self):
        """Initializes the PRAW client from environment variables with detailed logging."""
        try:
            # Log the start of the environment variable check
            logger.info("Attempting to load Reddit API environment variables...")

            client_id = os.getenv("REDDIT_CLIENT_ID")
            logger.debug(f"REDDIT_CLIENT_ID: {'Found' if client_id else 'Missing'}")

            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            logger.debug(f"REDDIT_CLIENT_SECRET: {'Found' if client_secret else 'Missing'}")

            user_agent = os.getenv("REDDIT_USER_AGENT")
            logger.debug(f"REDDIT_USER_AGENT: {'Found' if user_agent else 'Missing'}")
            
            username = os.getenv("REDDIT_USERNAME")
            logger.debug(f"REDDIT_USERNAME: {'Found' if username else 'Missing'}")
            
            password = os.getenv("REDDIT_PASSWORD")
            logger.debug(f"REDDIT_PASSWORD: {'Found' if password else 'Missing'}")

            if not all([client_id, client_secret, user_agent, username, password]):
                # Log a more specific error message when variables are missing
                missing_vars = [
                    name for name, val in {
                        "REDDIT_CLIENT_ID": client_id,
                        "REDDIT_CLIENT_SECRET": client_secret,
                        "REDDIT_USER_AGENT": user_agent,
                        "REDDIT_USERNAME": username,
                        "REDDIT_PASSWORD": password
                    }.items() if not val
                ]
                error_msg = f"Missing required Reddit API environment variables: {', '.join(missing_vars)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info("All required Reddit API environment variables found. Initializing PRAW client...")
            
            # Use await praw.Reddit for async operations
            return praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                username=username,
                password=password
            )
        except Exception as e:
            # The catch-all is still useful for unexpected errors, but the
            # specific `ValueError` should now provide a clearer message.
            logger.error(f"Failed to initialize PRAW client: {e}")
            return None
    
    @property
    def client(self):
        """Returns the initialized PRAW client."""
        if self._reddit is None:
            raise RuntimeError("Reddit client is not initialized. Check logs for API key errors.")
        return self._reddit

# Initialize the client globally for the module
try:
    reddit_manager = RedditClient()
    reddit_client = reddit_manager.client
except (ValueError, RuntimeError) as e:
    # This log is a good final check to see if the module failed to load.
    logger.error(f"Application cannot start without a working Reddit client: {e}")
    reddit_client = None  # Explicitly set to None if initialization fails

# --- Data Models for Input and Output ---
class UserDetails(BaseModel):
    name: str
    karma: int
    created_utc: float
    is_gold: bool

class PostDetails(BaseModel):
    id: str
    title: str
    score: int
    num_comments: int
    author: str
    created_utc: float
    url: HttpUrl

class SubredditStats(BaseModel):
    name: str
    subscribers: int
    active_users: int

class StrategicPost(BaseModel):
    id: str
    title: str
    url: HttpUrl

class ReplyResponse(BaseModel):
    status: str
    comment_id: str = Field(..., description="The ID of the newly created comment.")

# --- Tool Registration ---
def register_reddit_tools(mcp: FastMCP):
    """
    Registers all Reddit-related tools with the FastMCP instance.
    """
    if not reddit_client:
        logger.warning("Skipping Reddit tool registration due to PRAW client initialization failure.")
        return

    @mcp.tool()
    async def get_user_details(username: str) -> Dict[str, Any]:
        """
        Retrieves detailed information about a specific Reddit user.
        
        :param username: The username of the Redditor.
        :returns: A dictionary containing the user's name, karma, and other details.
        """
        logger.info(f"Tool 'get_user_details' called for username: {username}")
        try:
            redditor = await reddit_client.redditor(username)
            return UserDetails(
                name=redditor.name,
                karma=redditor.link_karma + redditor.comment_karma,
                created_utc=redditor.created_utc,
                is_gold=redditor.is_gold
            ).model_dump()
        except RedditAPIException as e:
            logger.error(f"Reddit API error for get_user_details: {e}")
            return {"error": "Reddit API error", "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in get_user_details: {e}")
            return {"error": "Internal server error", "message": str(e)}

    @mcp.tool()
    async def fetch_subreddit_posts(subreddit_name: str, post_count: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches the top posts from a specified subreddit.
        
        :param subreddit_name: The name of the subreddit (e.g., 'technology').
        :param post_count: The number of top posts to retrieve. Defaults to 10.
        :returns: A list of dictionaries, each representing a post.
        """
        logger.info(f"Tool 'fetch_subreddit_posts' called for r/{subreddit_name}, count: {post_count}")
        try:
            subreddit = await reddit_client.subreddit(subreddit_name)
            posts = [
                PostDetails(
                    id=post.id,
                    title=post.title,
                    score=post.score,
                    num_comments=post.num_comments,
                    author=post.author.name if post.author else "[deleted]",
                    created_utc=post.created_utc,
                    url=post.url
                ).model_dump() for post in subreddit.top(limit=post_count)
            ]
            return posts
        except RedditAPIException as e:
            logger.error(f"Reddit API error for fetch_subreddit_posts: {e}")
            return {"error": "Subreddit not found or invalid"}
        except Exception as e:
            logger.error(f"Unexpected error in fetch_subreddit_posts: {e}")
            return {"error": "Internal server error", "message": str(e)}

    @mcp.tool()
    async def get_subreddit_stats(subreddit_name: str) -> Dict[str, Any]:
        """
        Gets comprehensive statistics and health metrics for a subreddit.
        
        :param subreddit_name: The name of the subreddit.
        :returns: A dictionary with the subreddit's stats.
        """
        logger.info(f"Tool 'get_subreddit_stats' called for r/{subreddit_name}")
        try:
            subreddit = await reddit_client.subreddit(subreddit_name)
            return SubredditStats(
                name=subreddit.display_name,
                subscribers=subreddit.subscribers,
                active_users=subreddit.active_user_count
            ).model_dump()
        except RedditAPIException as e:
            logger.error(f"Reddit API error for get_subreddit_stats: {e}")
            return {"error": "Subreddit not found or invalid"}
        except Exception as e:
            logger.error(f"Unexpected error in get_subreddit_stats: {e}")
            return {"error": "Internal server error", "message": str(e)}

    @mcp.tool()
    async def get_trending_subreddits() -> List[str]:
        """
        Returns a list of currently trending subreddits based on 'popular' listing.
        
        :returns: A list of strings, where each string is a subreddit name.
        """
        logger.info("Tool 'get_trending_subreddits' called.")
        try:
            subreddits = [sub.display_name for sub in reddit_client.subreddits.popular(limit=10)]
            return subreddits
        except RedditAPIException as e:
            logger.error(f"Reddit API error for get_trending_subreddits: {e}")
            return {"error": "Reddit API error", "message": str(e)}

    @mcp.tool()
    async def create_strategic_post(subreddit_name: str, title: str, text: str) -> Dict[str, Any]:
        """
        Creates a new post.
        
        :param subreddit_name: The target subreddit.
        :param title: The title of the post.
        :param text: The body of the post.
        :returns: A dictionary confirming the post's creation and its ID.
        """
        logger.info(f"Tool 'create_strategic_post' called for r/{subreddit_name} with title: '{title}'")
        try:
            submission = await reddit_client.subreddit(subreddit_name).submit(title=title, selftext=text)
            return StrategicPost(
                id=submission.id,
                title=submission.title,
                url=f"https://www.reddit.com{submission.permalink}"
            ).model_dump()
        except RedditAPIException as e:
            logger.error(f"Reddit API error creating post: {e}")
            return {"error": "Failed to create post", "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in create_strategic_post: {e}")
            return {"error": "Internal server error", "message": str(e)}

    @mcp.tool()
    async def reply_to_post(post_id: str, reply_text: str) -> Dict[str, Any]:
        """
        Replies to a specific Reddit post or comment.
        
        :param post_id: The ID of the post or comment to reply to.
        :param reply_text: The text content of the reply.
        :returns: A dictionary confirming the reply.
        """
        logger.info(f"Tool 'reply_to_post' called for post ID: {post_id}")
        try:
            submission = await reddit_client.submission(post_id)
            comment = await submission.reply(reply_text)
            return ReplyResponse(status="Reply successful", comment_id=comment.id).model_dump()
        except RedditAPIException as e:
            logger.error(f"Reddit API error replying to post: {e}")
            return {"error": "Failed to reply", "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in reply_to_post: {e}")
            return {"error": "Internal server error", "message": str(e)}

    @mcp.tool()
    async def get_ai_insights(post_text: str) -> Dict[str, Any]:
        """
        Provides mock AI-driven insights on a given text. This would integrate with a separate LLM.
        
        :param post_text: The text to be analyzed.
        :returns: A dictionary with analysis, sentiment, and a recommendation.
        """
        logger.info("Tool 'get_ai_insights' called to analyze text.")
        # Placeholder logic: This would be a separate LLM call in a real application.
        # It's mocked here to make the tool functional.
        if "viral" in post_text.lower() or "trend" in post_text.lower():
            sentiment = "very positive"
            recommendation = "This is a high-potential topic. Promote it on other platforms."
        elif "problem" in post_text.lower() or "issue" in post_text.lower():
            sentiment = "negative"
            recommendation = "Address the issue directly and offer a solution."
        else:
            sentiment = "neutral"
            recommendation = "No specific action required. Monitor for changes."

        return {
            "sentiment": sentiment,
            "key_topics": ["sentiment analysis", "trend spotting"],
            "recommendation": recommendation
        }

    @mcp.tool()
    async def format_smart_response(original_text: str, metrics: Dict[str, Any]) -> str:
        """
        Formats a response with engagement metrics for a more impactful reply.
        
        :param original_text: The text of the reply.
        :param metrics: A dictionary of metrics to include (e.g., 'upvotes', 'comments').
        :returns: A string with the formatted response.
        """
        logger.info("Tool 'format_smart_response' called.")
        formatted_metrics = ", ".join([f"{k.capitalize()}: {v}" for k, v in metrics.items()])
        formatted_response = f"{original_text}\n\n---\n**Metrics:** {formatted_metrics}"
        return formatted_response

