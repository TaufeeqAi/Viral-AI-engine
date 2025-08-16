import json
import uuid
import logging
from typing import List, Optional, Any, Dict

import asyncpg
from pydantic import ValidationError

from ...models.agent_config import AgentConfig, AgentTool, Tool
from ..base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AgentRepository(BaseRepository):
    """
    Repository for agent-related database operations.
    Follows Single Responsibility Principle - only handles agent data access.
    """

    async def get_by_name(self, agent_name: str) -> Optional[AgentConfig]:
        """Fetches a single agent configuration from the database by its name."""
        logger.info(f"Fetching agent configuration for name: {agent_name}")
        record = await self._fetch_one("""
            SELECT
                a.id, a.user_id, a.name, a.model_provider, a.settings,
                a.system, a.bio, a.lore, a.knowledge, a.last_used, a.total_sessions,
                a.allowed_tool_names,
                jsonb_agg(
                    jsonb_build_object(
                        'tool_id', t.id,
                        'is_enabled', ata.is_enabled,
                        'tool_details', jsonb_build_object(
                            'id', t.id, 'name', t.name,
                            'description', t.description, 'config', t.config
                        )
                    )
                ) FILTER (WHERE t.id IS NOT NULL) AS tools
            FROM agents a
            LEFT JOIN agent_tool_association ata ON a.id = ata.agent_id
            LEFT JOIN tools t ON ata.tool_id = t.id
            WHERE a.name = $1
            GROUP BY a.id
        """, agent_name)

        if not record:
            logger.info(f"Agent configuration for name {agent_name} not found.")
            return None
        
        try:
            agent_config_data = self._build_agent_config_data(record)
            logger.info(f"Agent configuration for name {agent_name} fetched successfully.")
            return AgentConfig(**agent_config_data)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"Error processing agent {record['id']}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error processing agent {record['id']}: {e}", exc_info=True)
        return None

    async def get_all(self) -> List[AgentConfig]:
        """Fetches all agent configurations, including associated tools."""
        logger.info("Fetching all agent configurations.")
        records = await self._fetch_all("""
            SELECT
                a.id, a.user_id, a.name, a.model_provider, a.settings,
                a.system, a.bio, a.lore, a.knowledge, a.last_used, a.total_sessions,
                a.allowed_tool_names,
                jsonb_agg(
                    jsonb_build_object(
                        'tool_id', t.id,
                        'is_enabled', ata.is_enabled,
                        'tool_details', jsonb_build_object(
                            'id', t.id, 'name', t.name,
                            'description', t.description, 'config', t.config
                        )
                    )
                ) FILTER (WHERE t.id IS NOT NULL) AS tools
            FROM agents a
            LEFT JOIN agent_tool_association ata ON a.id = ata.agent_id
            LEFT JOIN tools t ON ata.tool_id = t.id
            GROUP BY a.id
        """)
        
        configs = []
        for record in records:
            try:
                agent_config_data = self._build_agent_config_data(record)
                configs.append(AgentConfig(**agent_config_data))
            except (ValidationError, json.JSONDecodeError) as e:
                logger.error(f"Error processing agent {record['id']}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error processing agent {record['id']}: {e}", exc_info=True)

        logger.info(f"Fetched {len(configs)} agent configurations.")
        return configs

    async def get_by_id(self, agent_id: str) -> Optional[AgentConfig]:
        """Fetches a single agent configuration by ID."""
        logger.info(f"Fetching agent configuration for ID: {agent_id}")
        record = await self._fetch_one("""
            SELECT
                a.id, a.user_id, a.name, a.model_provider, a.settings,
                a.system, a.bio, a.lore, a.knowledge, a.last_used, a.total_sessions,
                a.allowed_tool_names,
                jsonb_agg(
                    jsonb_build_object(
                        'tool_id', t.id,
                        'is_enabled', ata.is_enabled,
                        'tool_details', jsonb_build_object(
                            'id', t.id, 'name', t.name,
                            'description', t.description, 'config', t.config
                        )
                    )
                ) FILTER (WHERE t.id IS NOT NULL) AS tools
            FROM agents a
            LEFT JOIN agent_tool_association ata ON a.id = ata.agent_id
            LEFT JOIN tools t ON ata.tool_id = t.id
            WHERE a.id = $1
            GROUP BY a.id
        """, agent_id)
        
        if not record:
            logger.info(f"Agent configuration for ID {agent_id} not found.")
            return None
        
        try:
            agent_config_data = self._build_agent_config_data(record)
            logger.info(f"Agent configuration for ID {agent_id} fetched successfully.")
            return AgentConfig(**agent_config_data)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"Error processing agent {record['id']}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error processing agent {record['id']}: {e}", exc_info=True)
        return None

    async def save(self, config: AgentConfig, tool_ids_map: dict = None) -> str:
        """
        Saves a new agent configuration to the database and returns its ID.
        This method is now a temporary wrapper for the new upsert method.
        """
        logger.warning("The 'save' method is deprecated. Please use 'upsert_agent_config' instead.")
        return await self.upsert_agent_config(config, tool_ids_map)

    async def update(self, config: AgentConfig, tool_ids_map: dict = None):
        """
        Updates an existing agent configuration in the database.
        This method is now a temporary wrapper for the new upsert method.
        """
        logger.warning("The 'update' method is deprecated. Please use 'upsert_agent_config' instead.")
        await self.upsert_agent_config(config, tool_ids_map)

    async def upsert_agent_config(self, config: AgentConfig, tool_ids_map: dict = None) -> str:
        """
        Creates or updates an agent and its associated tools in the database.
        This operation is done within a transaction to ensure data consistency.
        This method combines the functionality of save() and update().
        """
        logger.info(f"Upserting agent configuration for agent: {config.name}")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. Upsert agent configuration
                # Use a new UUID for a new agent, otherwise use the existing ID.
                agent_id = str(uuid.uuid4()) if not config.id else config.id
                
                # Check for an existing agent by name to get its ID for the upsert operation.
                # This handles the unique constraint on 'name' correctly.
                existing_agent = await self.get_by_name(config.name)
                if existing_agent:
                    agent_id = existing_agent.id
                    logger.info(f"Agent with name '{config.name}' already exists. Using ID: {agent_id}")

                allowed_tool_names_json = json.dumps(config.allowed_tool_names) if config.allowed_tool_names is not None else '[]'

                await conn.execute("""
                    INSERT INTO agents (id, user_id, name, model_provider, settings, system, bio, lore, knowledge, last_used, total_sessions, allowed_tool_names, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7::jsonb, $8::jsonb, $9::jsonb, $10, $11, $12::jsonb, NOW(), NOW())
                    ON CONFLICT (name) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        name = EXCLUDED.name,
                        model_provider = EXCLUDED.model_provider,
                        settings = EXCLUDED.settings,
                        system = EXCLUDED.system,
                        bio = EXCLUDED.bio,
                        lore = EXCLUDED.lore,
                        knowledge = EXCLUDED.knowledge,
                        last_used = EXCLUDED.last_used,
                        total_sessions = EXCLUDED.total_sessions,
                        allowed_tool_names = EXCLUDED.allowed_tool_names,
                        updated_at = NOW()
                    RETURNING id;
                    """,
                    agent_id, config.user_id, config.name, config.modelProvider,
                    json.dumps(config.settings.model_dump(exclude_none=True)), config.system,
                    json.dumps(config.bio) if config.bio else None,
                    json.dumps(config.lore) if config.lore else None,
                    json.dumps(config.knowledge) if config.knowledge else None,
                    config.lastUsed, config.totalSessions,
                    allowed_tool_names_json
                )
                
                # 2. Update agent-tool associations
                await self._update_agent_tools(conn, agent_id, config.tools, tool_ids_map)
            
            logger.info(f"Agent configuration {agent_id} upserted successfully.")
            return agent_id
    
    # -----------------------------------------------------------
    # CORRECTED METHOD to fix the TypeError
    # -----------------------------------------------------------
    async def update_agent_config_and_tools(self, agent_id: str, agent_config: Dict[str, Any], tool_names: List[str]) -> bool:
        """
        Updates an agent's configuration and associates it with a new set of tools.
        
        Args:
            agent_id (str): The ID of the agent to update.
            agent_config (Dict[str, Any]): The new configuration for the agent.
            tool_names (List[str]): A list of tool names to associate with the agent.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # 1. Update the agent config
                    config_json = json.dumps(agent_config)
                    update_query = """
                        UPDATE agents
                        SET config = $1, updated_at = NOW()
                        WHERE id = $2;
                    """
                    await conn.execute(update_query, config_json, uuid.UUID(agent_id))

                    # 2. Delete existing tool associations
                    delete_query = """
                        DELETE FROM agent_tool_association
                        WHERE agent_id = $1;
                    """
                    await conn.execute(delete_query, uuid.UUID(agent_id))

                    # 3. Insert new tool associations
                    tool_ids = await self._get_tool_ids_by_names(conn, tool_names)
                    if tool_ids:
                        values = [(uuid.UUID(agent_id), uuid.UUID(tool_id)) for tool_id in tool_ids]
                        insert_query = """
                            INSERT INTO agent_tool_association (agent_id, tool_id)
                            VALUES ($1, $2);
                        """
                        await conn.executemany(insert_query, values)
                    
                    logger.info(f"Agent {agent_id} updated with new config and tools successfully.")
                    return True
                except Exception as e:
                    logger.error(f"Error updating agent config and tools: {e}")
                    raise
    
    async def _get_tool_ids_by_names(self, conn, tool_names: List[str]) -> List[str]:
        """
        Helper method to get tool IDs from tool names.
        """
        if not tool_names:
            return []
            
        placeholders = ', '.join([f'${i+1}' for i in range(len(tool_names))])
        query = f"SELECT id FROM tools WHERE name IN ({placeholders});"
        
        rows = await conn.fetch(query, *tool_names)
        return [str(row['id']) for row in rows]
    # -----------------------------------------------------------
    
    async def delete(self, agent_id: str):
        """Deletes an agent and its associations."""
        logger.info(f"Deleting agent configuration for ID: {agent_id}")
        await self._execute_query("DELETE FROM agents WHERE id = $1", uuid.UUID(agent_id))
        logger.info(f"Agent {agent_id} and its tool associations deleted.")

    async def get_tools_for_agent(self, agent_id: str) -> List[AgentTool]:
        """Fetches tools associated with an agent."""
        logger.info(f"Fetching tools for agent: {agent_id}")
        records = await self._fetch_all("""
            SELECT ata.is_enabled, t.id AS tool_id, t.name, t.description, t.config
            FROM agent_tool_association ata
            JOIN tools t ON ata.tool_id = t.id
            WHERE ata.agent_id = $1
        """, uuid.UUID(agent_id))

        tools = []
        for record in records:
            tools.append(AgentTool(
                tool_id=str(record["tool_id"]),
                is_enabled=record["is_enabled"],
                tool_details=Tool(
                    id=str(record["tool_id"]), name=record["name"],
                    description=record["description"], config=record["config"]
                )
            ))
        logger.info(f"Fetched {len(tools)} tools for agent {agent_id}")
        return tools

    async def add_tool_to_agent(self, agent_id: str, tool_id: str, is_enabled: bool = True, conn: Optional[asyncpg.Connection] = None):
        """Associates a tool with an agent."""
        logger.info(f"Adding tool {tool_id} to agent {agent_id} (enabled: {is_enabled})")
        await self._execute_query("""
            INSERT INTO agent_tool_association (agent_id, tool_id, is_enabled, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            ON CONFLICT (agent_id, tool_id) DO UPDATE SET 
                is_enabled = EXCLUDED.is_enabled, updated_at = NOW();
        """, uuid.UUID(agent_id), uuid.UUID(tool_id), is_enabled, conn=conn)
        logger.info(f"Tool {tool_id} associated with agent {agent_id}")

    async def remove_tool_from_agent(self, agent_id: str, tool_id: str):
        """Removes a tool association from an agent."""
        logger.info(f"Removing tool {tool_id} from agent {agent_id}")
        await self._execute_query("""
            DELETE FROM agent_tool_association WHERE agent_id = $1 AND tool_id = $2
        """, uuid.UUID(agent_id), uuid.UUID(tool_id))
        logger.info(f"Tool {tool_id} removed from agent {agent_id}")

    async def update_tool_enabled_status(self, agent_id: str, tool_id: str, is_enabled: bool):
        """Updates the enabled status of a tool for an agent."""
        logger.info(f"Updating enabled status for tool {tool_id} for agent {agent_id} to {is_enabled}")
        result = await self._execute_query("""
            UPDATE agent_tool_association
            SET is_enabled = $3, updated_at = NOW()
            WHERE agent_id = $1 AND tool_id = $2
        """, uuid.UUID(agent_id), uuid.UUID(tool_id), is_enabled)
        
        if result == "UPDATE 0":
            logger.warning(f"No association found to update for agent {agent_id} and tool {tool_id}")
        else:
            logger.info(f"Tool {tool_id} enabled status updated for agent {agent_id}")

    def _safe_json_parse(self, value: Any) -> Any:
        """Helper function to safely parse JSON if it's a string."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON string: {value[:100]}...")
                return None
        return value

    def _build_agent_config_data(self, record: dict) -> dict:
        """Builds agent config data from database record."""
        settings_data = self._safe_json_parse(record["settings"])
        bio_data = self._safe_json_parse(record["bio"])
        lore_data = self._safe_json_parse(record["lore"])
        knowledge_data = self._safe_json_parse(record["knowledge"])
        allowed_tool_names_data = self._safe_json_parse(record.get("allowed_tool_names", "[]"))
        tools_data = self._safe_json_parse(record["tools"]) if record["tools"] else []

        return {
            "id": str(record["id"]),
            "user_id": record["user_id"],
            "name": record["name"],
            "modelProvider": record["model_provider"],
            "settings": settings_data,
            "system": record["system"],
            "bio": bio_data,
            "lore": lore_data,
            "knowledge": knowledge_data,
            "tools": tools_data,
            "allowed_tool_names": allowed_tool_names_data,
            "lastUsed": record["last_used"],
            "totalSessions": record["total_sessions"]
        }

    async def _update_agent_tools(self, conn: asyncpg.Connection, agent_id: str, tools: List[AgentTool], tool_ids_map: Dict[str, str]):
        """Updates agent-tool associations."""
        await conn.execute("DELETE FROM agent_tool_association WHERE agent_id = $1", uuid.UUID(agent_id))

        if tools and tool_ids_map:
            insert_query = """
                INSERT INTO agent_tool_association (agent_id, tool_id, is_enabled)
                VALUES ($1, $2, $3)
            """
            rows = [
                (uuid.UUID(agent_id), uuid.UUID(tool_ids_map[agent_tool.tool_details.name]), agent_tool.is_enabled)
                for agent_tool in tools
                if agent_tool.tool_details and agent_tool.tool_details.name in tool_ids_map
            ]
            if rows:
                await conn.executemany(insert_query, rows)

