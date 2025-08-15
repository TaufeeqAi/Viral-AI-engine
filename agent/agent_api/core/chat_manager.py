from uuid import uuid4
from datetime import datetime, timezone 
from typing import List, Optional, Dict, Any, Union
import os
import httpx
import logging
import uuid

from agent.agent_api.models.chat_models import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatMessageCreate, # MODIFIED: ChatMessageCreate now has 'role'
    ChatSessionRead,
    ChatMessageRead,    # MODIFIED: ChatMessageRead now has 'role'
    ChatSession, 
    ChatMessage, 
    ChatSummary, 
    MessageContent 
)
from agent.agent_api.db.postgres_manager import PostgresManager 

logger = logging.getLogger(__name__)

WS_API_BASE_URL = os.getenv("WS_API_BASE_URL", "http://localhost:8002")

class ChatManager:
    """
    Manages chat sessions and messages with business logic
    implemented in the application layer, delegating database
    operations to PostgresManager.
    """
    def __init__(self, db_manager: PostgresManager): 
        self.db = db_manager
        self.ws_client = httpx.AsyncClient(base_url=WS_API_BASE_URL, timeout=10.0) 
        logger.info(f"ChatManager initialized. WS_API_BASE_URL: {WS_API_BASE_URL}")

    async def _broadcast_ws_event(self, event_type: str, payload: Dict[str, Any]):
        """Helper to send events to the WebSocket API for broadcasting."""
        logger.debug(f"Broadcasting WS event '{event_type}' with payload: {payload}")
        try:
            response = await self.ws_client.post(
                "/internal/broadcast",
                json={"type": event_type, "payload": payload}
            )
            response.raise_for_status()
            logger.debug(f"Successfully sent WS broadcast event '{event_type}' for session {payload.get('session_id')}")
        except httpx.RequestError as e:
            logger.error(f"Error sending WS broadcast event '{event_type}' to {WS_API_BASE_URL}/internal/broadcast: {e}", exc_info=True)
        except httpx.HTTPStatusError as e:
            logger.error(f"WS broadcast failed with status {e.response.status_code} for event '{event_type}': {e.response.text}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error during WS broadcast for event '{event_type}': {e}", exc_info=True)

    async def get_all_sessions_for_user(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100
    ) -> List[ChatSessionRead]:
        """Retrieves all chat sessions for a given user, with optional filters."""
        logger.info(f"ChatManager: Fetching all sessions for user '{user_id}'.")
        
        sessions_core = await self.db.get_all_sessions_for_user(user_id)

        filtered_sessions = []
        for session in sessions_core:
            if agent_id and str(session.agent_id) != agent_id:
                continue
            if active_only and not session.is_active:
                continue
            filtered_sessions.append(session)
        
        filtered_sessions.sort(key=lambda s: s.updated_at, reverse=True)
        final_sessions = filtered_sessions[:limit]

        logger.debug(f"ChatManager: Retrieved {len(final_sessions)} sessions from DB for user '{user_id}'.")
        return [ChatSessionRead.model_validate(s) for s in final_sessions]


    async def create_session(self, data: ChatSessionCreate) -> Optional[ChatSession]: 
        """
        Creates a new chat session and immediately updates the agent's stats.
        Operations are performed in a single transaction.
        Returns the created ChatSession object.
        """
        agent_id_str = str(data.agent_id)
        user_id_str = str(data.user_id)

        logger.info(f"ChatManager: Creating session for user '{user_id_str}' with agent '{agent_id_str}'.")
        
        try:
            session_id_from_db = await self.db.create_chat_session(
                user_id=user_id_str,
                agent_id=agent_id_str, 
                title=data.title
            )

            if not session_id_from_db:
                logger.error("ChatManager: Failed to get session ID from database after creation.")
                return None

            new_session = await self.db.get_chat_session(session_id_from_db)

            if not new_session:
                logger.error(f"ChatManager: Session {session_id_from_db} not found immediately after creation. This indicates a potential issue.")
                return None

            async with self.db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE agents
                    SET last_used = NOW(),
                        total_sessions = total_sessions + 1
                    WHERE id = $1
                """, agent_id_str)
            
            broadcast_payload = new_session.model_dump(mode='json')
            broadcast_payload["session_id"] = str(new_session.id) 

            await self._broadcast_ws_event(
                "session_created",
                broadcast_payload
            )
            logger.info(f"Chat session created: {new_session.id} and broadcasted.")
            return new_session 
        except Exception as e:
            logger.error(f"ChatManager: Error creating session for user '{user_id_str}': {e}", exc_info=True)
            raise

    async def add_message(self, session_id: str, data: ChatMessageCreate, is_partial: bool = False) -> str:
        """
        Adds a new message and handles all related trigger logic as fallbacks:
        - Updates the session's 'updated_at' timestamp.
        - Checks message count and generates/updates a summary every 10 messages.
        """
        message_id = str(uuid4())
        logger.info(f"ChatManager: Adding message {message_id} to session {session_id} (partial: {is_partial}).")
        
        if isinstance(data.content, str):
            content_obj = MessageContent(text=data.content)
        else: 
            content_obj = MessageContent(**data.content)

        # MODIFIED: Map role to sender_type and message_type
        sender_type_map = {
            "user": "user",
            "agent": "ai",
            "tool": "tool"
        }
        message_type_map = {
            "user": "human",
            "agent": "ai",
            "tool": "tool"
        }
        sender_type = sender_type_map.get(data.role, "unknown")
        message_type = message_type_map.get(data.role, "unknown")

        try:
            await self.db.add_chat_message(
                ChatMessage(
                    id=uuid.UUID(message_id),
                    session_id=uuid.UUID(session_id),
                    sender_type=sender_type, # MODIFIED: Use mapped sender_type
                    content=content_obj,
                    timestamp=datetime.now(timezone.utc), 
                    is_partial=is_partial,
                    message_type=message_type # MODIFIED: Use mapped message_type
                )
            )

            if not is_partial: 
                messages = await self.db.get_chat_messages(session_id)
                msg_count = len(messages)

                if msg_count > 0 and msg_count % 10 == 0:
                    summary_text = f"Auto-generated summary at {msg_count} messages for session {session_id}."
                    
                    summary_obj = ChatSummary(
                        session_id=uuid.UUID(session_id),
                        summary_text=summary_text,
                        message_count=msg_count
                    )
                    await self.db.save_chat_summary(summary_obj)
                    logger.info(f"ChatManager: Auto-generated summary for session {session_id} at {msg_count} messages.")
            
            event_type = "llm_stream_chunk" if is_partial else "message_created"
            
            # MODIFIED: Ensure 'role' is in the broadcast payload for ChatMessageRead consistency
            broadcast_payload = {
                "id": message_id,
                "session_id": session_id, 
                "role": data.role, # MODIFIED: Use 'role' for broadcast payload
                "content": data.content, 
                "timestamp": datetime.utcnow().isoformat(), 
                "is_partial": is_partial
            }
            logger.debug(f"ChatManager: Broadcasting message event '{event_type}' with content (first 50 chars): '{str(broadcast_payload['content'])[:50]}...'")
            logger.debug(f"ChatManager: Full broadcast payload: {broadcast_payload}")
            
            await self._broadcast_ws_event(
                event_type,
                broadcast_payload
            )
            logger.info(f"ChatManager: Message {message_id} added to session {session_id} and broadcasted (partial: {is_partial}).")
            return message_id
        except Exception as e:
            logger.error(f"ChatManager: Error adding message to session {session_id}: {e}", exc_info=True)
            raise

    async def get_session(self, session_id: str) -> Optional[ChatSessionRead]:
        """Retrieves a single session by its ID."""
        logger.info(f"ChatManager: Getting session {session_id}.")
        try:
            session_core = await self.db.get_chat_session(session_id)
            if session_core:
                logger.debug(f"ChatManager: Session {session_id} found.")
                return ChatSessionRead.model_validate(session_core)
            logger.warning(f"ChatManager: Session {session_id} not found.")
            return None
        except Exception as e:
            logger.error(f"ChatManager: Error getting session {session_id}: {e}", exc_info=True)
            raise
        
    async def get_messages(self, session_id: str) -> List[ChatMessageRead]:
        """
        Retrieves all messages for a session in chronological order.
        """
        logger.info(f"ChatManager: Getting messages for session {session_id}.")
        try:
            messages_core = await self.db.get_chat_messages(session_id)
            logger.debug(f"ChatManager: Retrieved {len(messages_core)} messages for session {session_id}.")
            
            # MODIFIED: Map ChatMessage core models to ChatMessageRead API models
            # The ChatMessageRead now expects 'role' instead of 'sender_type'
            mapped_messages = []
            for m in messages_core:
                # Determine the role for the API response based on internal sender_type
                api_role = "user"
                if m.sender_type == "ai":
                    api_role = "agent"
                elif m.sender_type == "tool":
                    api_role = "tool"

                mapped_messages.append(ChatMessageRead(
                    id=m.id,
                    session_id=m.session_id,
                    role=api_role, # MODIFIED: Use mapped API role
                    content=m.content,
                    timestamp=m.timestamp,
                    is_partial=m.is_partial
                ))
            return mapped_messages
        except Exception as e:
            logger.error(f"ChatManager: Error getting messages for session {session_id}: {e}", exc_info=True)
            raise

    async def update_session(self, session_id: str, update_data: ChatSessionUpdate):
        """Updates a session's title or active status."""
        logger.info(f"ChatManager: Updating session {session_id}.")
        logger.debug(f"ChatManager: Update data: {update_data.model_dump()}")
        try:
            await self.db.update_chat_session(
                session_id=session_id,
                title=update_data.title,
                is_active=update_data.is_active
            )
            
            updated_session_core = await self.db.get_chat_session(session_id)
            if updated_session_core:
                broadcast_payload = updated_session_core.model_dump(mode='json')
                broadcast_payload["session_id"] = str(updated_session_core.id) 

                await self._broadcast_ws_event(
                    "session_updated",
                    broadcast_payload
                )
                logger.info(f"ChatManager: Session {session_id} updated and broadcasted.")
            else:
                logger.warning(f"ChatManager: Could not find updated session {session_id} for broadcast.")
        except Exception as e:
            logger.error(f"ChatManager: Error updating session {session_id}: {e}", exc_info=True)
            raise
