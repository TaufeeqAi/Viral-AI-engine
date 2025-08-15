# agent/ws_api/models/chat_event.py

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel

class ChatEventType(str, Enum):
    """
    Defines the types of real-time chat events that can be broadcast.
    """
    SESSION_CREATED = "session_created"
    MESSAGE_CREATED = "message_created"
    SESSION_UPDATED = "session_updated"
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    ERROR = "error" # For broadcasting error messages to clients

class ChatEvent(BaseModel):
    """
    Represents a standardized chat event for WebSocket communication.
    """
    type: ChatEventType
    channel: str # The specific channel this event is intended for (e.g., "chat-session-{session_id}")
    data: Dict[str, Any] # The actual payload of the event, containing relevant data
