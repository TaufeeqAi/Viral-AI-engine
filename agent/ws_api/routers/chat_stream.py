# agent/ws_api/routers/chat_stream.py

import json
import logging
from typing import Dict, List, Any, Annotated
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Path, Depends
import asyncio
from ..utils.connection_manager import ConnectionManager
from ..services.token_auth import get_current_user_ws
from agent.ws_api.models.chat_event import ChatEvent, ChatEventType
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# The ConnectionManager instance should be shared across all WebSocket routers in ws_api
manager = ConnectionManager()

# Define event types for broadcasting
class WsEventType(BaseModel):
    type: str
    payload: Dict[str, Any]

router = APIRouter()

async def get_user_id_from_websocket(websocket: WebSocket):
    user_id_str = await get_current_user_ws(websocket)
    if not user_id_str:
        raise HTTPException(status_code=status.WS_1008_POLICY_VIOLATION, detail="Authentication failed")
    return user_id_str

@router.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Annotated[str, Path()],
    user_id: Annotated[str, Depends(get_user_id_from_websocket)]
):
    """
    WebSocket endpoint for real-time chat updates.
    Clients connect to this endpoint to receive updates for a specific chat session.
    """
    
    channel = f"chat-session-{session_id}"
    
    await manager.connect(websocket, user_id, session_id, channel)
    logger.info(f"WebSocket connected: user_id={user_id}, session_id={session_id}, channel={channel}")

    try:
        while True:
            message = await websocket.receive_text()
            logger.debug(f"Received message from client on channel {channel}: {message}")
            # You can add logic here to process client-sent messages if needed
            # For instance, if the client is sending "user_message" events:
            # try:
            #     parsed_message = json.loads(message)
            #     if parsed_message.get("type") == ChatEventType.MESSAGE_CREATED.value:
            #         logger.info(f"Client sent message: {parsed_message.get('payload', {}).get('content')}")
            #         # Here you would typically pass this message to your agent processing logic
            #         # For testing, let's echo it back as an assistant message
            #         response_event = ChatEvent(
            #             type=ChatEventType.MESSAGE_CREATED,
            #             channel=channel,
            #             data={
            #                 "role": "assistant",
            #                 "content": f"Echo from server: {parsed_message.get('payload', {}).get('content')}"
            #             }
            #         )
            #         await manager.broadcast(channel, json.dumps(response_event.model_dump()))
            # except json.JSONDecodeError:
            #     logger.error(f"Invalid JSON received from client: {message}")
            #     await websocket.send_text(json.dumps({"error": "Invalid JSON format from client"}))
            # except Exception as e:
            #     logger.error(f"Error processing client message: {e}", exc_info=True)
            #     await websocket.send_text(json.dumps({"error": f"Server error processing client message: {e}"}))

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket for session: {session_id}, user_id={user_id}")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}, user_id={user_id}: {e}", exc_info=True)
        manager.disconnect(websocket)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except RuntimeError:
            pass


@router.post("/internal/broadcast")
async def internal_broadcast(event: WsEventType):
    """
    Internal endpoint for the agent-api to trigger WebSocket broadcasts.
    This endpoint should only be accessible internally (e.g., within Docker network).
    """
    session_id = event.payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id is required in payload for broadcast.")
    
    channel = f"chat-session-{session_id}"
    logger.info(f"Received internal broadcast request for channel {channel}, type: {event.type}")
    
    json_message_to_broadcast = json.dumps(event.model_dump())
    logger.debug(f"Broadcasting JSON message to channel '{channel}': {json_message_to_broadcast}") # Added logging here
    
    await manager.broadcast(channel, json_message_to_broadcast)
    return {"status": "success", "message": "Broadcast initiated."}

