# agent/agent-api/db/repositories/chat_repository.py

import json
import logging
from typing import List, Optional

from ...models.chat_models import ChatSession, ChatMessage, ChatSummary, MessageContent
from ..base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ChatRepository(BaseRepository):
    """
    Repository for chat-related database operations.
    Follows Single Responsibility Principle - only handles chat data access.
    """

    # --- CHAT SESSION OPERATIONS ---
    async def create_session(self, user_id: str, agent_id: str, title: Optional[str] = None) -> str:
        """Creates a new chat session."""
        logger.info(f"Creating chat session for user {user_id} with agent {agent_id}")
        session_id = await self._fetch_value("""
            INSERT INTO chat_sessions (user_id, agent_id, title, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, TRUE, NOW(), NOW())
            RETURNING id;
        """, user_id, agent_id, title)
        session_id_str = str(session_id)
        logger.info(f"Chat session created: {session_id_str}")
        return session_id_str
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieves a chat session by ID."""
        logger.info(f"Fetching chat session: {session_id}")
        record = await self._fetch_one("""
            SELECT id, user_id, agent_id, title, is_active, created_at, updated_at
            FROM chat_sessions WHERE id = $1;
        """, session_id)
        if record:
            logger.info(f"Chat session {session_id} found.")
            return ChatSession(
                id=str(record["id"]),
                user_id=record["user_id"],
                agent_id=str(record["agent_id"]),
                title=record["title"],
                is_active=record["is_active"],
                created_at=record["created_at"],
                updated_at=record["updated_at"]
            )
        logger.info(f"Chat session {session_id} not found.")
        return None

    async def get_sessions_for_user(self, user_id: str) -> List[ChatSession]:
        """Retrieves all chat sessions for a given user."""
        logger.info(f"Fetching all chat sessions for user: {user_id}")
        records = await self._fetch_all("""
            SELECT id, user_id, agent_id, title, is_active, created_at, updated_at
            FROM chat_sessions WHERE user_id = $1 ORDER BY updated_at DESC;
        """, user_id)
        sessions = []
        for record in records:
            sessions.append(ChatSession(
                id=str(record["id"]),
                user_id=record["user_id"],
                agent_id=str(record["agent_id"]),
                title=record["title"],
                is_active=record["is_active"],
                created_at=record["created_at"],
                updated_at=record["updated_at"]
            ))
        logger.info(f"Fetched {len(sessions)} chat sessions for user {user_id}")
        return sessions

    async def update_session(self, session_id: str, title: Optional[str] = None, is_active: Optional[bool] = None):
        """Updates a chat session's title or active status."""
        logger.info(f"Updating chat session {session_id}")
        set_clauses = []
        params = []
        param_idx = 1

        if title is not None:
            set_clauses.append(f"title = ${param_idx}")
            params.append(title)
            param_idx += 1
        if is_active is not None:
            set_clauses.append(f"is_active = ${param_idx}")
            params.append(is_active)
            param_idx += 1
        
        if not set_clauses:
            logger.warning(f"No update data provided for session {session_id}")
            return

        set_clauses.append(f"updated_at = NOW()")
        
        query = f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE id = ${param_idx}"
        params.append(session_id)

        await self._execute_query(query, *params)
        logger.info(f"Chat session {session_id} updated.")

    async def delete_session(self, session_id: str):
        """Deletes a chat session by ID."""
        logger.info(f"Deleting chat session: {session_id}")
        await self._execute_query("DELETE FROM chat_sessions WHERE id = $1", session_id)
        logger.info(f"Chat session {session_id} deleted.")

    # --- CHAT MESSAGE OPERATIONS ---
    async def add_message(self, message: ChatMessage) -> str:
        """Adds a new chat message to a session."""
        logger.info(f"Adding message {message.id} to session {message.session_id}")
        message_id = await self._fetch_value("""
            INSERT INTO chat_messages (id, session_id, sender_type, content, timestamp, is_partial, message_type)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
            RETURNING id;
        """,
        message.id, message.session_id, message.sender_type,
        json.dumps(message.content.model_dump(exclude_none=True)),
        message.timestamp, message.is_partial, message.message_type
        )
        logger.info(f"Message {message_id} added to session {message.session_id}")
        return str(message_id)

    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Retrieves chat messages for a session, optionally with a limit."""
        logger.info(f"Fetching chat messages for session: {session_id} (limit: {limit})")
        query = """
            SELECT id, session_id, sender_type, content, timestamp, is_partial, message_type
            FROM chat_messages WHERE session_id = $1 ORDER BY timestamp ASC
        """
        params = [session_id]
        if limit:
            query += " LIMIT $2"
            params.append(limit)
        
        records = await self._fetch_all(query, *params)
        messages = []
        for record in records:
            try:
                content_data = self._safe_content_parse(record["content"])
                messages.append(ChatMessage(
                    id=str(record["id"]),
                    session_id=str(record["session_id"]),
                    sender_type=record["sender_type"],
                    content=MessageContent.model_validate(content_data),
                    timestamp=record["timestamp"],
                    is_partial=record["is_partial"],
                    message_type=record["message_type"]
                ))
            except Exception as e:
                logger.error(f"Error processing message {record['id']}: {e}", exc_info=True)
                continue
                
        logger.info(f"Fetched {len(messages)} messages for session {session_id}")
        return messages

    async def update_message_content(self, message_id: str, new_content: MessageContent):
        """Updates the content of an existing chat message."""
        logger.info(f"Updating content for message: {message_id}")
        await self._execute_query("""
            UPDATE chat_messages SET
                content = $2::jsonb,
                is_partial = FALSE,
                timestamp = NOW()
            WHERE id = $1;
        """, message_id, json.dumps(new_content.model_dump(exclude_none=True)))
        logger.info(f"Message {message_id} content updated.")

    async def delete_messages_for_session(self, session_id: str):
        """Deletes all chat messages for a given session."""
        logger.info(f"Deleting all messages for session: {session_id}")
        await self._execute_query("DELETE FROM chat_messages WHERE session_id = $1", session_id)
        logger.info(f"All messages for session {session_id} deleted.")

    # --- CHAT SUMMARY OPERATIONS ---
    async def save_summary(self, summary: ChatSummary):
        """Saves or updates a chat session summary."""
        logger.info(f"Saving/updating chat summary for session: {summary.session_id}")
        await self._execute_query("""
            INSERT INTO chat_summaries (session_id, summary_text, message_count, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            ON CONFLICT (session_id) DO UPDATE SET
                summary_text = EXCLUDED.summary_text,
                message_count = EXCLUDED.message_count,
                updated_at = NOW();
        """, summary.session_id, summary.summary_text, summary.message_count)
        logger.info(f"Chat summary for session {summary.session_id} saved/updated.")

    async def get_summary(self, session_id: str) -> Optional[ChatSummary]:
        """Retrieves a chat session summary."""
        logger.info(f"Fetching chat summary for session: {session_id}")
        record = await self._fetch_one("""
            SELECT session_id, summary_text, message_count, created_at, updated_at
            FROM chat_summaries WHERE session_id = $1;
        """, session_id)
        if record:
            logger.info(f"Chat summary for session {session_id} found.")
            return ChatSummary(
                session_id=str(record["session_id"]),
                summary_text=record["summary_text"],
                message_count=record["message_count"],
                created_at=record["created_at"],
                updated_at=record["updated_at"]
            )
        logger.info(f"Chat summary for session {session_id} not found.")
        return None

    async def delete_summary(self, session_id: str):
        """Deletes a chat session summary."""
        logger.info(f"Deleting chat summary for session: {session_id}")
        await self._execute_query("DELETE FROM chat_summaries WHERE session_id = $1", session_id)
        logger.info(f"Chat summary for session {session_id} deleted.")

    def _safe_content_parse(self, content_value):
        """Helper function to safely parse content."""
        if isinstance(content_value, str):
            try:
                return json.loads(content_value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse content JSON string: {content_value[:100]}...")
                return {"text": content_value}
        elif isinstance(content_value, dict):
            return content_value
        else:
            logger.warning(f"Unexpected content type: {type(content_value)}")
            return {"text": str(content_value)}