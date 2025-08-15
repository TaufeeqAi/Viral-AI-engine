from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

# ─── Core Models (for internal database/logic use) ──────────────────────────

class MessageContent(BaseModel):
    """
    Represents the content of a chat message, which can be text or tool calls.
    This corresponds to the JSONB 'content' column in the chat_messages table.
    """
    text: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="List of tool calls made by the AI.")
    tool_output: Optional[Any] = Field(None, description="Output from a tool call.")

class ChatSession(BaseModel):
    """Core model representing a chat session as stored in the database."""
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    agent_id: UUID
    title: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "from_attributes": True
    }

class ChatMessage(BaseModel):
    """Core model representing a chat message as stored in the database."""
    id: UUID = Field(default_factory=uuid.uuid4)
    session_id: UUID
    sender_type: str = Field(..., description="'user', 'ai', 'tool'") # Retained for internal logic/DB
    content: MessageContent # Use the nested MessageContent model
    timestamp: datetime = Field(default_factory=datetime.now)
    is_partial: bool = False
    message_type: str = Field(..., description="Corresponds to LangChain's message types: 'human', 'ai', 'tool'") # Retained for internal logic/DB

    model_config = {
        "from_attributes": True
    }

class ChatSummary(BaseModel):
    """Core model representing a chat session summary as stored in the database."""
    session_id: UUID
    summary_text: str
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "from_attributes": True
    }

# ─── API Schemas (for request/response validation) ──────────────────────────

class ChatSessionCreate(BaseModel):
    user_id: str
    agent_id: UUID
    title: str = Field(..., max_length=255)

class ChatSessionRead(BaseModel):
    id: UUID
    user_id: str
    agent_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {
        "from_attributes": True
    }

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool]

class ChatMessageCreate(BaseModel):
    # MODIFIED: Changed 'sender_type' to 'role' for API input
    role: str = Field(..., pattern="^(user|agent|tool)$", description="Role of the message sender: 'user', 'agent', or 'tool'")
    content: Union[str, Dict[str, Any]] # Allow string or dict for content
    is_partial: bool = Field(False, description="Indicates if this is a partial message for streaming.")
    # Removed message_type from API input, will be derived in ChatManager

class ChatMessageRead(BaseModel):
    id: UUID
    session_id: UUID
    # MODIFIED: Changed 'sender_type' to 'role' for API output consistency
    role: str # The role of the sender (user, ai, tool)
    content: Union[str, Dict[str, Any]] # Content can be text or structured JSON
    timestamp: datetime
    is_partial: bool

    model_config = {
        "from_attributes": True
    }
