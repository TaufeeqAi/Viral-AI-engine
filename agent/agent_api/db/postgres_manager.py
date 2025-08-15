# agent/agent-api/db/postgres_manager.py

import json, uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import asyncpg
from pydantic import ValidationError

from ..models.agent_config import AgentConfig, AgentTool, Settings, AgentSecrets, Tool
from ..models.chat_models import ChatSession, ChatMessage, ChatSummary, MessageContent # Assuming these models exist

logger = logging.getLogger(__name__)


class PostgresManager:
    """
    Manages all database interactions with PostgreSQL.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        logger.info("PostgresManager initialized.")

    async def connect(self):
        """Initializes the connection pool and ensures tables exist and are properly structured."""
        logger.info("Attempting to connect to PostgreSQL and create connection pool.")
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=1,
                max_size=10,
                timeout=60,
                command_timeout=60
            )
            logger.info("PostgreSQL connection pool created successfully.")
            await self._ensure_tables_exist()
            await self._ensure_schema_is_up_to_date()
            logger.info("PostgreSQL tables and schema are up to date.")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise

    async def close(self):
        """Closes the connection pool."""
        logger.info("Attempting to close PostgreSQL connection pool.")
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL connection pool closed.")
        else:
            logger.info("No PostgreSQL connection pool to close.")

    async def _ensure_tables_exist(self):
        """Creates the necessary tables if they do not exist."""
        logger.info("Ensuring database tables exist.")
        async with self.pool.acquire() as conn:
            # Enable UUID generation if not already enabled (for gen_random_uuid())
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

            # Table for Agents
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL UNIQUE, -- Added UNIQUE constraint for name
                    model_provider TEXT NOT NULL,
                    settings JSONB NOT NULL,
                    system TEXT,
                    bio JSONB,
                    lore JSONB,
                    knowledge JSONB,
                    message_examples JSONB,
                    style JSONB,
                    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    total_sessions INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            logger.info("Ensured 'agents' table exists in PostgreSQL.")

            # Table for Tools
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    config JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            logger.info("Ensured 'tools' table exists in PostgreSQL.")

            # Association table for agents and tools (many-to-many relationship)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_tool_association (
                    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
                    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
                    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (agent_id, tool_id)
                );
            """)
            logger.info("Ensured 'agent_tool_association' table exists in PostgreSQL.")
            
            # Table for Chat Sessions 
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Use gen_random_uuid() for default
                    user_id TEXT NOT NULL, -- Changed to TEXT for consistency with SYSTEM_USER_ID
                    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
                    title TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            logger.info("Ensured 'chat_sessions' table exists in PostgreSQL.")
            
            # Table for Chat Messages (MODIFIED: content to JSONB, added message_type)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    sender_type TEXT NOT NULL, -- 'user', 'ai', 'tool'
                    content JSONB NOT NULL, -- Changed to JSONB
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_partial BOOLEAN DEFAULT FALSE,
                    message_type TEXT NOT NULL DEFAULT 'ai' -- Added message_type
                );
            """)
            logger.info("Ensured 'chat_messages' table exists in PostgreSQL.")

            # Table for Chat Summaries
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_summaries (
                    session_id UUID PRIMARY KEY REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    summary_text TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            logger.info("Ensured 'chat_summaries' table exists in PostgreSQL.")
    
    async def _ensure_schema_is_up_to_date(self):
        """Checks for and adds missing columns and updates types if needed."""
        logger.info("Ensuring database schema is up to date.")
        async with self.pool.acquire() as conn:
            # Helper to check if a column exists
            async def column_exists(table_name, column_name):
                return await conn.fetchval(f"""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = '{column_name}'
                """)
            
            # Helper to check column type
            async def get_column_type(table_name, column_name):
                return await conn.fetchval(f"""
                    SELECT data_type FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND column_name = '{column_name}'
                """)

            # Agents table updates
            if not await column_exists('agents', 'last_used'):
                logger.warning("Column 'last_used' not found. Adding it to 'agents' table.")
                await conn.execute("ALTER TABLE agents ADD COLUMN last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'last_used' column to 'agents' table.")
            if not await column_exists('agents', 'total_sessions'):
                logger.warning("Column 'total_sessions' not found. Adding it to 'agents' table.")
                await conn.execute("ALTER TABLE agents ADD COLUMN total_sessions INTEGER DEFAULT 0;")
                logger.info("Added 'total_sessions' column to 'agents' table.")
            if not await column_exists('agents', 'created_at'):
                logger.warning("Column 'created_at' not found. Adding it to 'agents' table.")
                await conn.execute("ALTER TABLE agents ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'created_at' column to 'agents' table.")
            if not await column_exists('agents', 'updated_at'):
                logger.warning("Column 'updated_at' not found. Adding it to 'agents' table.")
                await conn.execute("ALTER TABLE agents ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'updated_at' column to 'agents' table.")
            
            # Ensure JSONB types for agents table
            jsonb_columns = ['settings', 'bio', 'lore', 'knowledge', 'message_examples', 'style']
            for col in jsonb_columns:
                col_type = await get_column_type('agents', col)
                if col_type and col_type.lower() == 'text':
                    logger.warning(f"Column '{col}' is of type TEXT. Altering to JSONB.")
                    # Use to_jsonb to safely convert existing TEXT data to JSONB
                    await conn.execute(f"UPDATE agents SET {col} = to_jsonb({col}) WHERE {col} IS NOT NULL;")
                    await conn.execute(f"ALTER TABLE agents ALTER COLUMN {col} TYPE JSONB USING {col}::jsonb;")
                    logger.info(f"Altered '{col}' column to JSONB.")
            
            # Tools table updates
            if not await column_exists('tools', 'created_at'):
                logger.warning("Column 'created_at' not found. Adding it to 'tools' table.")
                await conn.execute("ALTER TABLE tools ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'created_at' column to 'tools' table.")
            if not await column_exists('tools', 'updated_at'):
                logger.warning("Column 'updated_at' not found. Adding it to 'tools' table.")
                await conn.execute("ALTER TABLE tools ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'updated_at' column to 'tools' table.")

            # Agent_tool_association table updates
            if not await column_exists('agent_tool_association', 'is_enabled'):
                logger.warning("Column 'is_enabled' not found. Adding it to 'agent_tool_association' table.")
                await conn.execute("ALTER TABLE agent_tool_association ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT TRUE;")
                logger.info("Added 'is_enabled' column to 'agent_tool_association' table.")
            if not await column_exists('agent_tool_association', 'created_at'):
                logger.warning("Column 'created_at' not found. Adding it to 'agent_tool_association' table.")
                await conn.execute("ALTER TABLE agent_tool_association ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'created_at' column to 'agent_tool_association' table.")
            if not await column_exists('agent_tool_association', 'updated_at'):
                logger.warning("Column 'updated_at' not found. Adding it to 'agent_tool_association' table.")
                await conn.execute("ALTER TABLE agent_tool_association ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'updated_at' column to 'agent_tool_association' table.")

            # Chat_sessions table updates
            if not await column_exists('chat_sessions', 'created_at'):
                logger.warning("Column 'created_at' not found. Adding it to 'chat_sessions' table.")
                await conn.execute("ALTER TABLE chat_sessions ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'created_at' column to 'chat_sessions' table.")
            if not await column_exists('chat_sessions', 'updated_at'):
                logger.warning("Column 'updated_at' not found. Adding it to 'chat_sessions' table.")
                await conn.execute("ALTER TABLE chat_sessions ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'updated_at' column to 'chat_sessions' table.")
            if not await column_exists('chat_sessions', 'is_active'):
                logger.warning("Column 'is_active' not found. Adding it to 'chat_sessions' table.")
                await conn.execute("ALTER TABLE chat_sessions ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
                logger.info("Added 'is_active' column to 'chat_sessions' table.")
            if not await column_exists('chat_sessions', 'title'):
                logger.warning("Column 'title' not found. Adding it to 'chat_sessions' table.")
                await conn.execute("ALTER TABLE chat_sessions ADD COLUMN title TEXT;")
                logger.info("Added 'title' column to 'chat_sessions' table.")


            # Chat_messages table updates
            content_type = await get_column_type('chat_messages', 'content')
            if content_type and content_type.lower() == 'text':
                logger.warning("Column 'content' in 'chat_messages' is TEXT. Altering to JSONB.")
                # FIX: Use to_jsonb to safely convert existing TEXT data to JSONB
                await conn.execute("""
                    UPDATE chat_messages
                    SET content = to_jsonb(content)
                    WHERE content IS NOT NULL;
                """)
                await conn.execute("ALTER TABLE chat_messages ALTER COLUMN content TYPE JSONB USING content::jsonb;")
                logger.info("Altered 'content' column in 'chat_messages' to JSONB.")
            if not await column_exists('chat_messages', 'is_partial'):
                logger.warning("Column 'is_partial' not found. Adding it to 'chat_messages' table.")
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN is_partial BOOLEAN DEFAULT FALSE;")
                logger.info("Added 'is_partial' column to 'chat_messages' table.")
            if not await column_exists('chat_messages', 'message_type'):
                logger.warning("Column 'message_type' not found. Adding it to 'chat_messages' table.")
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN message_type TEXT NOT NULL DEFAULT 'ai';")
                logger.info("Added 'message_type' column to 'chat_messages' table.")
            if not await column_exists('chat_messages', 'timestamp'):
                logger.warning("Column 'timestamp' not found. Adding it to 'chat_messages' table.")
                await conn.execute("ALTER TABLE chat_messages ADD COLUMN timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'timestamp' column to 'chat_messages' table.")


            # Chat_summaries table updates
            if not await column_exists('chat_summaries', 'created_at'):
                logger.warning("Column 'created_at' not found. Adding it to 'chat_summaries' table.")
                await conn.execute("ALTER TABLE chat_summaries ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'created_at' column to 'chat_summaries' table.")
            if not await column_exists('chat_summaries', 'updated_at'):
                logger.warning("Column 'updated_at' not found. Adding it to 'chat_summaries' table.")
                await conn.execute("ALTER TABLE chat_summaries ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                logger.info("Added 'updated_at' column to 'chat_summaries' table.")
            if not await column_exists('chat_summaries', 'message_count'):
                logger.warning("Column 'message_count' not found. Adding it to 'chat_summaries' table.")
                await conn.execute("ALTER TABLE chat_summaries ADD COLUMN message_count INTEGER DEFAULT 0;")
                logger.info("Added 'message_count' column to 'chat_summaries' table.")
            if not await column_exists('chat_summaries', 'summary_text'): # Ensure summary is TEXT, not JSONB if it was
                summary_text_type = await get_column_type('chat_summaries', 'summary_text')
                if summary_text_type and summary_text_type.lower() == 'jsonb':
                    logger.warning("Column 'summary_text' in 'chat_summaries' is JSONB. Altering to TEXT.")
                    await conn.execute("ALTER TABLE chat_summaries ALTER COLUMN summary_text TYPE TEXT USING summary_text::text;")
                    logger.info("Altered 'summary_text' column in 'chat_summaries' to TEXT.")


    async def get_all_agent_configs(self) -> List[AgentConfig]:
        """Fetches all agent configurations, including associated tools."""
        logger.info("Fetching all agent configurations.")
        async with self.pool.acquire() as conn:
            records = await conn.fetch("""
                SELECT
                    a.id,
                    a.user_id,
                    a.name,
                    a.model_provider,
                    a.settings,
                    a.system,
                    a.bio,
                    a.lore,
                    a.knowledge,
                    a.message_examples,
                    a.style,
                    a.last_used,
                    a.total_sessions,
                    jsonb_agg(
                        jsonb_build_object(
                            'tool_id', t.id,
                            'is_enabled', ata.is_enabled,
                            'tool_details', jsonb_build_object(
                                'id', t.id,
                                'name', t.name,
                                'description', t.description,
                                'config', t.config
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
                    # Helper function to safely parse JSON if it's a string
                    def safe_json_parse(value):
                        if isinstance(value, str):
                            try:
                                return json.loads(value)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON string: {value[:100]}...")
                                return None
                        return value

                    # Parse all JSONB fields safely
                    settings_data = safe_json_parse(record["settings"])
                    bio_data = safe_json_parse(record["bio"])
                    lore_data = safe_json_parse(record["lore"])
                    knowledge_data = safe_json_parse(record["knowledge"])
                    message_examples_data = safe_json_parse(record["message_examples"])
                    style_data = safe_json_parse(record["style"])
                    tools_data = safe_json_parse(record["tools"]) if record["tools"] else []

                    agent_config_data = {
                        "id": str(record["id"]),
                        "user_id": record["user_id"],
                        "name": record["name"],
                        "modelProvider": record["model_provider"],
                        "settings": settings_data,
                        "system": record["system"],
                        "bio": bio_data,
                        "lore": lore_data,
                        "knowledge": knowledge_data,
                        "messageExamples": message_examples_data,
                        "style": style_data,
                        "tools": tools_data,
                        "lastUsed": record["last_used"],
                        "totalSessions": record["total_sessions"]
                    }
                    configs.append(AgentConfig(**agent_config_data))
                except (ValidationError, json.JSONDecodeError) as e:
                    logger.error(f"Validation or JSON decode error for agent {record['id']}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error processing agent {record['id']}: {e}", exc_info=True)

            logger.info(f"Fetched {len(configs)} agent configurations.")
            return configs


    async def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Fetches a single agent configuration by ID."""
        logger.info(f"Fetching agent configuration for ID: {agent_id}.")
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("""
                SELECT
                    a.id,
                    a.user_id, 
                    a.name,
                    a.model_provider,
                    a.settings,
                    a.system,
                    a.bio,
                    a.lore,
                    a.knowledge,
                    a.message_examples,
                    a.style,
                    a.last_used,
                    a.total_sessions,
                    jsonb_agg(
                        jsonb_build_object(
                            'tool_id', t.id,
                            'is_enabled', ata.is_enabled,
                            'tool_details', jsonb_build_object(
                                'id', t.id,
                                'name', t.name,
                                'description', t.description,
                                'config', t.config
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
                # Helper function to safely parse JSON if it's a string
                def safe_json_parse(value):
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON string: {value[:100]}...")
                            return None
                    return value

                # Parse all JSONB fields safely
                settings_data = safe_json_parse(record["settings"])
                bio_data = safe_json_parse(record["bio"])
                lore_data = safe_json_parse(record["lore"])
                knowledge_data = safe_json_parse(record["knowledge"])
                message_examples_data = safe_json_parse(record["message_examples"])
                style_data = safe_json_parse(record["style"])
                tools_data = safe_json_parse(record["tools"]) if record["tools"] else []

                agent_config_data = {
                    "id": str(record["id"]),
                    "user_id": record["user_id"],
                    "name": record["name"],
                    "modelProvider": record["model_provider"],
                    "settings": settings_data,
                    "system": record["system"],
                    "bio": bio_data,
                    "lore": lore_data,
                    "knowledge": knowledge_data,
                    "messageExamples": message_examples_data,
                    "style": style_data,
                    "tools": tools_data,
                    "lastUsed": record["last_used"],
                    "totalSessions": record["total_sessions"]
                }
                logger.info(f"Agent configuration for ID {agent_id} fetched successfully.")
                return AgentConfig(**agent_config_data)
            except (ValidationError, json.JSONDecodeError) as e:
                logger.error(f"Validation or JSON decode error for agent {record['id']}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error processing agent {record['id']}: {e}", exc_info=True)
            return None
    

    async def save_agent_config(self, config: AgentConfig) -> str:
        """Saves a new agent configuration to the database and returns its ID."""
        logger.info(f"Saving agent configuration for agent: {config.name}.")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Upsert tool metadata first
                tool_ids_map = {}
                if config.tools:
                    for agent_tool in config.tools:
                        tool = agent_tool.tool_details
                        if tool and tool.name:
                            tool_id = await self.upsert_tool(tool, conn=conn) 
                            tool_ids_map[tool.name] = tool_id
                
                # Use UPSERT with name conflict handling
                agent_id = await conn.fetchval("""
                    INSERT INTO agents (id, user_id, name, model_provider, settings, system, bio, lore, knowledge, message_examples, style, last_used, total_sessions, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7::jsonb, $8::jsonb, $9::jsonb, $10::jsonb, $11::jsonb, $12, $13, NOW(), NOW())
                    ON CONFLICT (name) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        model_provider = EXCLUDED.model_provider,
                        settings = EXCLUDED.settings,
                        system = EXCLUDED.system,
                        bio = EXCLUDED.bio,
                        lore = EXCLUDED.lore,
                        knowledge = EXCLUDED.knowledge,
                        message_examples = EXCLUDED.message_examples,
                        style = EXCLUDED.style,
                        last_used = EXCLUDED.last_used,
                        total_sessions = EXCLUDED.total_sessions,
                        updated_at = NOW()
                    RETURNING id;
                """,
                config.id,
                config.user_id,
                config.name,
                config.modelProvider,
                json.dumps(config.settings.model_dump(exclude_none=True)),
                config.system,
                json.dumps(config.bio) if config.bio else None,
                json.dumps(config.lore) if config.lore else None,
                json.dumps(config.knowledge) if config.knowledge else None,
                json.dumps(config.messageExamples) if config.messageExamples else None,
                json.dumps(config.style) if config.style else None,
                config.lastUsed,
                config.totalSessions
                )

                # Update agent-tool association table
                await conn.execute("DELETE FROM agent_tool_association WHERE agent_id = $1", agent_id)

                if config.tools:
                    for agent_tool in config.tools:
                        tool_name = agent_tool.tool_details.name if agent_tool.tool_details else None
                        if tool_name and tool_name in tool_ids_map:
                            tool_id = tool_ids_map[tool_name]
                            await self.add_tool_to_agent(str(agent_id), tool_id, agent_tool.is_enabled, conn=conn)

                logger.info(f"Agent configuration {agent_id} saved successfully.")
                return str(agent_id)
        
    async def update_agent_config(self, config: AgentConfig):
        """Updates an existing agent configuration in the database, including its tools."""
        logger.info(f"Updating agent configuration for agent: {config.name} (ID: {config.id}).")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Upsert tool metadata first (for any new tools or updated details)
                tool_ids_map = {}
                if config.tools:
                    for agent_tool in config.tools:
                        tool = agent_tool.tool_details
                        if tool and tool.name:
                            tool_id = await self.upsert_tool(tool, conn=conn)
                            tool_ids_map[tool.name] = tool_id

                # Update agent config
                await conn.execute("""
                    UPDATE agents SET
                        user_id = $2,
                        name = $3,
                        model_provider = $4,
                        settings = $5::jsonb,
                        system = $6,
                        bio = $7::jsonb,
                        lore = $8::jsonb,
                        knowledge = $9::jsonb,
                        message_examples = $10::jsonb,
                        style = $11::jsonb,
                        last_used = $12,
                        total_sessions = $13,
                        updated_at = NOW()
                    WHERE id = $1;
                """,
                config.id,
                config.user_id,
                config.name,
                config.modelProvider,
                json.dumps(config.settings.model_dump(exclude_none=True)),
                config.system,
                json.dumps(config.bio) if config.bio else None,
                json.dumps(config.lore) if config.lore else None,
                json.dumps(config.knowledge) if config.knowledge else None,
                json.dumps(config.messageExamples) if config.messageExamples else None,
                json.dumps(config.style) if config.style else None,
                config.lastUsed,
                config.totalSessions
                )
                logger.info(f"Agent config '{config.name}' (ID: {config.id}) updated in agents table.")

                # Update agent-tool association table
                # Delete all existing associations for this agent
                await conn.execute("DELETE FROM agent_tool_association WHERE agent_id = $1", config.id)
                logger.debug(f"Deleted existing tool associations for agent {config.id}.")

                # Insert new associations based on the updated config.tools list
                if config.tools:
                    for agent_tool in config.tools:
                        tool_name = agent_tool.tool_details.name if agent_tool.tool_details else None
                        if tool_name and tool_name in tool_ids_map:
                            tool_id = tool_ids_map[tool_name]
                            await self.add_tool_to_agent(str(config.id), tool_id, agent_tool.is_enabled, conn=conn)
                logger.info(f"Updated tool associations for agent {config.id}.")

    async def delete_agent_config(self, agent_id: str):
        """Deletes an agent and its associations."""
        logger.info(f"Deleting agent configuration for ID: {agent_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM agents WHERE id = $1", agent_id)
            logger.info(f"Agent {agent_id} and its tool associations deleted.")

    ## Tool specific crud
    async def upsert_tool(self, tool: Tool, conn: Optional[asyncpg.Connection] = None) -> str:
        """Inserts or updates tool metadata in the database. Can use an existing connection."""
        logger.info(f"Upserting tool: {tool.name}.")
        _conn = conn if conn else await self.pool.acquire()
        try:
            tool_id = await _conn.fetchval("""
                INSERT INTO tools (id, name, description, config, created_at, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW())
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    config = EXCLUDED.config,
                    updated_at = NOW()
                RETURNING id;
            """, tool.id or str(uuid.uuid4()), tool.name, tool.description, json.dumps(tool.config))
            logger.info(f"Tool {tool.name} upserted with ID: {tool_id}.")
            return tool_id
        finally:
            if conn is None: # Only release if we acquired it
                await _conn.release()

    async def get_tool_by_id(self, tool_id: str) -> Optional[Tool]:
        logger.info(f"Fetching tool by ID: {tool_id}.")
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("SELECT id, name, description, config FROM tools WHERE id = $1", tool_id)
            if record:
                logger.info(f"Tool {tool_id} found.")
                return Tool(id=str(record["id"]), name=record["name"], description=record["description"], config=record["config"])
            logger.info(f"Tool {tool_id} not found.")
        return None

    async def get_all_tool_metadata(self) -> List[Tool]:
        logger.info("Fetching all tool metadata.")
        async with self.pool.acquire() as conn:
            records = await conn.fetch("SELECT id, name, description, config FROM tools")
            logger.info(f"Fetched {len(records)} tool metadata records.")
            return [Tool(id=str(r["id"]), name=r["name"], description=r["description"], config=r["config"]) for r in records]

    async def delete_tool(self, tool_id: str):
        logger.info(f"Deleting tool with ID: {tool_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM tools WHERE id = $1", tool_id)
            logger.info(f"Tool {tool_id} deleted.")

    ##AgentTool Crud

    ## Add tool to agent
    async def add_tool_to_agent(self, agent_id: str, tool_id: str, is_enabled: bool = True, conn: Optional[asyncpg.Connection] = None):
        """Associates a tool with an agent. Can use an existing connection."""
        logger.info(f"Adding tool {tool_id} to agent {agent_id} (enabled: {is_enabled}).")
        _conn = conn if conn else await self.pool.acquire()
        try:
            await _conn.execute("""
                INSERT INTO agent_tool_association (agent_id, tool_id, is_enabled, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (agent_id, tool_id) DO UPDATE SET 
                    is_enabled = EXCLUDED.is_enabled,
                    updated_at = NOW();
            """, agent_id, tool_id, is_enabled)
            logger.info(f"Tool {tool_id} associated with agent {agent_id}.")
        finally:
            if conn is None:
                await _conn.release()

    ## delete a tool from agent
    async def remove_tool_from_agent(self, agent_id: str, tool_id: str):
        logger.info(f"Removing tool {tool_id} from agent {agent_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM agent_tool_association
                WHERE agent_id = $1 AND tool_id = $2
            """, agent_id, tool_id)
            logger.info(f"Tool {tool_id} removed from agent {agent_id}.")

    ## get tools of a agent
    async def get_tools_for_agent(self, agent_id: str) -> List[AgentTool]:
        logger.info(f"Fetching tools for agent: {agent_id}.")
        async with self.pool.acquire() as conn:
            records = await conn.fetch("""
                SELECT
                    ata.is_enabled,
                    t.id AS tool_id,
                    t.name,
                    t.description,
                    t.config
                FROM agent_tool_association ata
                JOIN tools t ON ata.tool_id = t.id
                WHERE ata.agent_id = $1
            """, agent_id)

            tools = []
            for record in records:
                tools.append(AgentTool(
                    tool_id=str(record["tool_id"]), # Ensure UUID is converted to str
                    is_enabled=record["is_enabled"],
                    tool_details=Tool(
                        id=str(record["tool_id"]),
                        name=record["name"],
                        description=record["description"],
                        config=record["config"]
                    )
                ))
            logger.info(f"Fetched {len(tools)} tools for agent {agent_id}.")
            return tools

    ##enable tool for a agent
    async def update_tool_enabled_status(self, agent_id: str, tool_id: str, is_enabled: bool):
        logger.info(f"Updating enabled status for tool {tool_id} for agent {agent_id} to {is_enabled}.")
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE agent_tool_association
                SET is_enabled = $3, updated_at = NOW()
                WHERE agent_id = $1 AND tool_id = $2
            """, agent_id, tool_id, is_enabled)
            if result == "UPDATE 0":
                logger.warning(f"No association found to update for agent {agent_id} and tool {tool_id}.")
            else:
                logger.info(f"Tool {tool_id} enabled status updated for agent {agent_id}.")


    # --- CHAT SESSION CRUD ---
    async def create_chat_session(self, user_id: str, agent_id: str, title: Optional[str] = None) -> str:
        """Creates a new chat session."""
        logger.info(f"Creating chat session for user {user_id} with agent {agent_id}.")
        async with self.pool.acquire() as conn:
            session_id = await conn.fetchval("""
                INSERT INTO chat_sessions (user_id, agent_id, title, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, TRUE, NOW(), NOW())
                RETURNING id;
            """, user_id, agent_id, title)
            session_id_str = str(session_id)
            logger.info(f"Chat session created: {session_id_str}")
            return session_id_str
    
    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieves a chat session by ID."""
        logger.info(f"Fetching chat session: {session_id}.")
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("""
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

    async def get_all_sessions_for_user(self, user_id: str) -> List[ChatSession]:
        """Retrieves all chat sessions for a given user."""
        logger.info(f"Fetching all chat sessions for user: {user_id}.")
        async with self.pool.acquire() as conn:
            records = await conn.fetch("""
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
            logger.info(f"Fetched {len(sessions)} chat sessions for user {user_id}.")
            return sessions

    async def update_chat_session(self, session_id: str, title: Optional[str] = None, is_active: Optional[bool] = None):
        """Updates a chat session's title or active status."""
        logger.info(f"Updating chat session {session_id}.")
        async with self.pool.acquire() as conn:
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
                logger.warning(f"No update data provided for session {session_id}.")
                return

            set_clauses.append(f"updated_at = NOW()")
            
            query = f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE id = ${param_idx}"
            params.append(session_id)

            await conn.execute(query, *params)
            logger.info(f"Chat session {session_id} updated.")


    async def delete_chat_session(self, session_id: str):
        """Deletes a chat session by ID."""
        logger.info(f"Deleting chat session: {session_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM chat_sessions WHERE id = $1", session_id)
            logger.info(f"Chat session {session_id} deleted.")

    # --- CHAT MESSAGE CRUD ---
    async def add_chat_message(self, message: ChatMessage) -> str:
        """Adds a new chat message to a session."""
        logger.info(f"Adding message {message.id} to session {message.session_id}.")
        async with self.pool.acquire() as conn:
            message_id = await conn.fetchval("""
                INSERT INTO chat_messages (id, session_id, sender_type, content, timestamp, is_partial, message_type)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
                RETURNING id;
            """,
            message.id,
            message.session_id,
            message.sender_type,
            json.dumps(message.content.model_dump(exclude_none=True)), # Ensure content is dumped to JSON string
            message.timestamp,
            message.is_partial,
            message.message_type
            )
            logger.info(f"Message {message_id} added to session {message.session_id}.")
            return str(message_id)

    async def get_chat_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Retrieves chat messages for a session, optionally with a limit."""
        logger.info(f"Fetching chat messages for session: {session_id} (limit: {limit}).")
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, session_id, sender_type, content, timestamp, is_partial, message_type
                FROM chat_messages WHERE session_id = $1 ORDER BY timestamp ASC
            """
            params = [session_id]
            if limit:
                query += " LIMIT $2"
                params.append(limit)
            
            records = await conn.fetch(query, *params)
            messages = []
            for record in records:
                try:
                    # Helper function to safely parse content
                    def safe_content_parse(content_value):
                        if isinstance(content_value, str):
                            try:
                                return json.loads(content_value)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse content JSON string: {content_value[:100]}...")
                                # If it's just a plain text string, wrap it in the expected format
                                return {"text": content_value}
                        elif isinstance(content_value, dict):
                            return content_value
                        else:
                            logger.warning(f"Unexpected content type: {type(content_value)}")
                            return {"text": str(content_value)}

                    content_data = safe_content_parse(record["content"])
                    
                    messages.append(ChatMessage(
                        id=str(record["id"]),
                        session_id=str(record["session_id"]),
                        sender_type=record["sender_type"],
                        content=MessageContent.model_validate(content_data),  # Now passing a dict
                        timestamp=record["timestamp"],
                        is_partial=record["is_partial"],
                        message_type=record["message_type"]
                    ))
                except Exception as e:
                    logger.error(f"Error processing message {record['id']}: {e}", exc_info=True)
                    # Skip this message and continue with others
                    continue
                    
            logger.info(f"Fetched {len(messages)} messages for session {session_id}.")
            return messages

    async def update_chat_message_content(self, message_id: str, new_content: MessageContent):
        """Updates the content of an existing chat message."""
        logger.info(f"Updating content for message: {message_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE chat_messages SET
                    content = $2::jsonb,
                    is_partial = FALSE,
                    timestamp = NOW()
                WHERE id = $1;
            """, message_id, json.dumps(new_content.model_dump(exclude_none=True)))
            logger.info(f"Message {message_id} content updated.")

    async def delete_chat_messages_for_session(self, session_id: str):
        """Deletes all chat messages for a given session."""
        logger.info(f"Deleting all messages for session: {session_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM chat_messages WHERE session_id = $1", session_id)
            logger.info(f"All messages for session {session_id} deleted.")

    # --- CHAT SUMMARY CRUD ---
    async def save_chat_summary(self, summary: ChatSummary):
        """Saves or updates a chat session summary."""
        logger.info(f"Saving/updating chat summary for session: {summary.session_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_summaries (session_id, summary_text, message_count, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    summary_text = EXCLUDED.summary_text,
                    message_count = EXCLUDED.message_count,
                    updated_at = NOW();
            """, summary.session_id, summary.summary_text, summary.message_count)
            logger.info(f"Chat summary for session {summary.session_id} saved/updated.")

    async def get_chat_summary(self, session_id: str) -> Optional[ChatSummary]:
        """Retrieves a chat session summary."""
        logger.info(f"Fetching chat summary for session: {session_id}.")
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow("""
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

    async def delete_chat_summary(self, session_id: str):
        """Deletes a chat session summary."""
        logger.info(f"Deleting chat summary for session: {session_id}.")
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM chat_summaries WHERE session_id = $1", session_id)
            logger.info(f"Chat summary for session {session_id} deleted.")
