# api/routes/webhooks.py
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException,status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from langchain_core.messages import HumanMessage, AIMessage

from ..dependencies import get_agent_manager
from ..utils.agent_selector import get_agent_by_bot_id

logger = logging.getLogger(__name__)

router = APIRouter()

class ReceiveDiscordMessageRequest(BaseModel):
    """Pydantic model for Discord message webhook payload."""
    content: str
    channel_id: str
    author_id: str
    author_name: str
    message_id: str
    timestamp: str
    guild_id: Optional[str] = None
    bot_id: str

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook messages."""
    try:
        data = await request.json()
        logger.info(f"Received Telegram webhook data: {json.dumps(data, indent=2)}")

        # Parse message data
        message = data.get("message")
        if not message:
            # Handle forwarded payloads from external services
            chat_id = data.get("chat_id")
            user_message = data.get("content")
            incoming_bot_id = data.get("bot_id")
        else:
            # Handle direct Telegram webhook payloads
            chat_id = message.get("chat", {}).get("id")
            user_message = message.get("text")
            incoming_bot_id = data.get("bot_id")

        if not all([chat_id, user_message, incoming_bot_id]):
            logger.warning(f"Missing essential Telegram message data. Details: chat_id={chat_id}, user_message={user_message}, bot_id={incoming_bot_id}")
            return JSONResponse(
                status_code=200, 
                content={"status": "ignored", "detail": "Missing essential data."}
            )

        # Get agent manager from app state
        from fastapi import Request
        agent_manager = request.app.state.agent_manager

        # Find appropriate agent
        selected_agent_info = get_agent_by_bot_id(agent_manager, incoming_bot_id, "telegram")
        if not selected_agent_info:
            return JSONResponse(
                status_code=200, 
                content={"status": "ignored", "detail": f"No agent for bot ID {incoming_bot_id}."}
            )
        
        # Process message with agent
        agent_executor = selected_agent_info["executor"]
        agent_mcp_client = selected_agent_info["mcp_client"]

        logger.info(f"Invoking agent '{selected_agent_info['name']}' with Telegram message...")
        initial_state = {"messages": [HumanMessage(content=user_message)]}
        agent_output = await agent_executor.ainvoke(initial_state)

        # Extract response
        final_message_content = "I'm sorry, I couldn't process that."
        if "messages" in agent_output and agent_output["messages"]:
            last_message = agent_output["messages"][-1]
            if isinstance(last_message, AIMessage):
                final_message_content = last_message.content
            else:
                final_message_content = str(last_message)

        # Send response via Telegram
        telegram_tool = agent_mcp_client.tools.get("send_message_telegram")
        if telegram_tool:
            logger.info(f"Using agent '{selected_agent_info['name']}'s Telegram tool to send reply.")
            await telegram_tool.ainvoke({"chat_id": str(chat_id), "message": final_message_content})
            logger.info("Telegram reply sent successfully.")
        else:
            logger.error(f"Selected agent '{selected_agent_info['name']}' unexpectedly lacks 'send_message_telegram' tool.")

        return JSONResponse(status_code=200, content={"status": "ok"})

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discord/receive_message")
async def receive_discord_message(payload: ReceiveDiscordMessageRequest, request: Request):
    """Handle incoming Discord webhook messages."""
    try:
        channel_id = payload.channel_id
        author_name = payload.author_name
        message_content = payload.content
        incoming_bot_id = payload.bot_id

        logger.info(f"Received Discord message from {author_name} via bot {incoming_bot_id} in channel {channel_id}: {message_content}")

        # Get agent manager from app state
        agent_manager = request.app.state.agent_manager

        # Find appropriate agent
        selected_agent_info = get_agent_by_bot_id(agent_manager, incoming_bot_id, "discord")
        if not selected_agent_info:
            return JSONResponse(
                status_code=200, 
                content={"status": "ignored", "detail": f"No agent for bot ID {incoming_bot_id}."}
            )

        # Process message with agent
        agent_executor = selected_agent_info["executor"]
        agent_mcp_client = selected_agent_info["mcp_client"]

        logger.info(f"Invoking agent '{selected_agent_info['name']}' with Discord message...")
        initial_state = {"messages": [HumanMessage(content=message_content)]}
        agent_output = await agent_executor.ainvoke(initial_state)

        # Extract response
        final_message_content = "I'm sorry, I couldn't process that."
        if "messages" in agent_output and agent_output["messages"]:
            last_message = agent_output["messages"][-1]
            if isinstance(last_message, AIMessage):
                final_message_content = last_message.content
            else:
                final_message_content = str(last_message)

        # Send response via Discord
        discord_tool = agent_mcp_client.tools.get("send_message")
        if discord_tool:
            logger.info(f"Using agent '{selected_agent_info['name']}'s Discord tool to send reply.")
            await discord_tool.ainvoke({"channel_id": str(channel_id), "message": final_message_content})
            logger.info("Discord reply sent successfully.")
        else:
            logger.error(f"Selected agent '{selected_agent_info['name']}' unexpectedly lacks 'send_message' tool.")

        return JSONResponse(status_code=200, content={"status": "ok"})

    except ValidationError as e:
        logger.warning(f"Discord message validation failed: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid Discord message payload: {e.errors()}"
        )
    except Exception as e:
        logger.error(f"Error processing received Discord message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))