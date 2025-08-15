# agent/agent-api/db/repositories/tool_repository.py

import json
import uuid
import logging
from typing import List, Optional

import asyncpg

from ...models.agent_config import Tool
from ..base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ToolRepository(BaseRepository):
    """
    Repository for tool-related database operations.
    Follows Single Responsibility Principle - only handles tool data access.
    """

    async def upsert(self, tool: Tool, conn: Optional[asyncpg.Connection] = None) -> str:
        """Inserts or updates tool metadata in the database."""
        logger.info(f"Upserting tool: {tool.name}")
        tool_id = await self._fetch_value("""
            INSERT INTO tools (id, name, description, config, created_at, updated_at)
            VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW())
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                config = EXCLUDED.config,
                updated_at = NOW()
            RETURNING id;
        """, tool.id or str(uuid.uuid4()), tool.name, tool.description, json.dumps(tool.config), conn=conn)
        logger.info(f"Tool {tool.name} upserted with ID: {tool_id}")
        return tool_id

    async def get_by_id(self, tool_id: str) -> Optional[Tool]:
        """Fetches a tool by its ID."""
        logger.info(f"Fetching tool by ID: {tool_id}")
        record = await self._fetch_one("SELECT id, name, description, config FROM tools WHERE id = $1", tool_id)
        if record:
            logger.info(f"Tool {tool_id} found.")
            return Tool(
                id=str(record["id"]), 
                name=record["name"], 
                description=record["description"], 
                config=record["config"]
            )
        logger.info(f"Tool {tool_id} not found.")
        return None

    async def get_all(self) -> List[Tool]:
        """Fetches all tool metadata."""
        logger.info("Fetching all tool metadata.")
        records = await self._fetch_all("SELECT id, name, description, config FROM tools")
        logger.info(f"Fetched {len(records)} tool metadata records.")
        return [
            Tool(
                id=str(r["id"]), 
                name=r["name"], 
                description=r["description"], 
                config=r["config"]
            ) for r in records
        ]

    async def delete(self, tool_id: str):
        """Deletes a tool by its ID."""
        logger.info(f"Deleting tool with ID: {tool_id}")
        await self._execute_query("DELETE FROM tools WHERE id = $1", tool_id)
        logger.info(f"Tool {tool_id} deleted.")

