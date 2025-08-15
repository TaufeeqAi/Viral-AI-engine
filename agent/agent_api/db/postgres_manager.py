# agent/agent-api/db/postgres_manager.py

import logging
from typing import List, Optional

from ..models.agent_config import AgentConfig, AgentTool, Tool
from ..models.chat_models import ChatSession, ChatMessage, ChatSummary

from .database_connection import DatabaseConnection
from .schema_manager import SchemaManager
from .repositories.agent_repository import AgentRepository
from .repositories.tool_repository import ToolRepository
from .repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class PostgresManager:
    """
    Main database manager that coordinates all database operations.
    Follows Facade pattern - provides a simplified interface to the complex subsystem.
    Follows Dependency Inversion Principle - depends on abstractions (repositories).
    """

    def __init__(self, dsn: str):
        self.db_connection = DatabaseConnection(dsn)
        self.schema_manager = None
        self.agent_repo = None
        self.tool_repo = None
        self.chat_repo = None
        logger.info("PostgresManager initialized.")

    async def connect(self):
        """Initializes the connection and sets up repositories."""
        await self.db_connection.connect()
        pool = self.db_connection.get_pool()
        
        # Initialize schema manager and ensure schema is up to date
        self.schema_manager = SchemaManager(pool)
        await self.schema_manager.ensure_tables_exist()
        await self.schema_manager.ensure_schema_is_up_to_date()
        
        # Initialize repositories
        self.agent_repo = AgentRepository(pool)
        self.tool_repo = ToolRepository(pool)
        self.chat_repo = ChatRepository(pool)
        
        logger.info("PostgresManager connected and repositories initialized.")

    async def close(self):
        """Closes the database connection."""
        await self.db_connection.close()
        logger.info("PostgresManager connection closed.")

    # --- AGENT OPERATIONS (Delegate to AgentRepository) ---
    async def get_agent_config_by_name(self, agent_name: str) -> Optional[AgentConfig]:
        """Fetches a single agent configuration by name."""
        return await self.agent_repo.get_by_name(agent_name)

    async def get_all_agent_configs(self) -> List[AgentConfig]:
        """Fetches all agent configurations."""
        return await self.agent_repo.get_all()

    async def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Fetches a single agent configuration by ID."""
        return await self.agent_repo.get_by_id(agent_id)

    async def save_agent_config(self, config: AgentConfig) -> str:
        """Saves a new agent configuration."""
        # Upsert tools first
        tool_ids_map = {}
        if config.tools:
            for agent_tool in config.tools:
                tool = agent_tool.tool_details
                if tool and tool.name:
                    tool_id = await self.tool_repo.upsert(tool)
                    tool_ids_map[tool.name] = tool_id
        
        return await self.agent_repo.save(config, tool_ids_map)

    async def update_agent_config(self, config: AgentConfig):
        """Updates an existing agent configuration."""
        # Upsert tools first
        tool_ids_map = {}
        if config.tools:
            for agent_tool in config.tools:
                tool = agent_tool.tool_details
                if tool and tool.name:
                    tool_id = await self.tool_repo.upsert(tool)
                    tool_ids_map[tool.name] = tool_id
        
        await self.agent_repo.update(config, tool_ids_map)

    async def delete_agent_config(self, agent_id: str):
        """Deletes an agent configuration."""
        await self.agent_repo.delete(agent_id)

    async def get_tools_for_agent(self, agent_id: str) -> List[AgentTool]:
        """Gets tools associated with an agent."""
        return await self.agent_repo.get_tools_for_agent(agent_id)

    async def add_tool_to_agent(self, agent_id: str, tool_id: str, is_enabled: bool = True):
        """Associates a tool with an agent."""
        await self.agent_repo.add_tool_to_agent(agent_id, tool_id, is_enabled)

    async def remove_tool_from_agent(self, agent_id: str, tool_id: str):
        """Removes a tool association from an agent."""
        await self.agent_repo.remove_tool_from_agent(agent_id, tool_id)

    async def update_tool_enabled_status(self, agent_id: str, tool_id: str, is_enabled: bool):
        """Updates tool enabled status for an agent."""
        await self.agent_repo.update_tool_enabled_status(agent_id, tool_id, is_enabled)

    # --- TOOL OPERATIONS (Delegate to ToolRepository) ---
    async def upsert_tool(self, tool: Tool) -> str:
        """Inserts or updates a tool."""
        return await self.tool_repo.upsert(tool)

    async def get_tool_by_id(self, tool_id: str) -> Optional[Tool]:
        """Gets a tool by ID."""
        return await self.tool_repo.get_by_id(tool_id)

    async def get_all_tool_metadata(self) -> List[Tool]:
        """Gets all tool metadata."""
        return await self.tool_repo.get_all()

    async def delete_tool(self, tool_id: str):
        """Deletes a tool."""
        await self.tool_repo.delete(tool_id)

    # --- CHAT OPERATIONS (Delegate to ChatRepository) ---
    async def create_chat_session(self, user_id: str, agent_id: str, title: Optional[str] = None) -> str:
        """Creates a new chat session."""
        return await self.chat_repo.create_session(user_id, agent_id, title)

    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Gets a chat session by ID."""
        return await self.chat_repo.get_session(session_id)

    async def get_all_sessions_for_user(self, user_id: str) -> List[ChatSession]:
        """Gets all chat sessions for a user."""
        return await self.chat_repo.get_sessions_for_user(user_id)

    async def update_chat_session(self, session_id: str, title: Optional[str] = None, is_active: Optional[bool] = None):
        """Updates a chat session."""
        await self.chat_repo.update_session(session_id, title, is_active)

    async def delete_chat_session(self, session_id: str):
        """Deletes a chat session."""
        await self.chat_repo.delete_session(session_id)

    async def add_chat_message(self, message: ChatMessage) -> str:
        """Adds a chat message."""
        return await self.chat_repo.add_message(message)

    async def get_chat_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Gets chat messages for a session."""
        return await self.chat_repo.get_messages(session_id, limit)

    async def update_chat_message_content(self, message_id: str, new_content):
        """Updates chat message content."""
        await self.chat_repo.update_message_content(message_id, new_content)

    async def delete_chat_messages_for_session(self, session_id: str):
        """Deletes all messages for a session."""
        await self.chat_repo.delete_messages_for_session(session_id)

    async def save_chat_summary(self, summary: ChatSummary):
        """Saves a chat summary."""
        await self.chat_repo.save_summary(summary)

    async def get_chat_summary(self, session_id: str) -> Optional[ChatSummary]:
        """Gets a chat summary."""
        return await self.chat_repo.get_summary(session_id)

    async def delete_chat_summary(self, session_id: str):
        """Deletes a chat summary."""
        await self.chat_repo.delete_summary(session_id)