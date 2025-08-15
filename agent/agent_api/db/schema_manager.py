import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages database schema creation and updates.
    Follows Single Responsibility Principle - only handles schema operations.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def ensure_tables_exist(self):
        """Creates the necessary tables if they do not exist."""
        logger.info("Ensuring database tables exist.")
        async with self.pool.acquire() as conn:
            # Enable UUID generation if not already enabled
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            
            await self._create_agents_table(conn)
            await self._create_tools_table(conn)
            await self._create_agent_tool_association_table(conn)
            await self._create_chat_sessions_table(conn)
            await self._create_chat_messages_table(conn)
            await self._create_chat_summaries_table(conn)

    async def ensure_schema_is_up_to_date(self):
        """Checks for and adds missing columns and updates types if needed."""
        logger.info("Ensuring database schema is up to date.")
        async with self.pool.acquire() as conn:
            await self._update_agents_schema(conn)
            await self._update_tools_schema(conn)
            await self._update_agent_tool_association_schema(conn)
            await self._update_chat_sessions_schema(conn)
            await self._update_chat_messages_schema(conn)
            await self._update_chat_summaries_schema(conn)

    async def _create_agents_table(self, conn: asyncpg.Connection):
        """Creates the agents table."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                model_provider TEXT NOT NULL,
                settings JSONB NOT NULL,
                system TEXT,
                bio JSONB,
                lore JSONB,
                knowledge JSONB,
                -- Added the missing column for allowed tool names
                allowed_tool_names JSONB,
                last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                total_sessions INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        logger.info("Ensured 'agents' table exists in PostgreSQL.")

    async def _create_tools_table(self, conn: asyncpg.Connection):
        """Creates the tools table."""
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

    async def _create_agent_tool_association_table(self, conn: asyncpg.Connection):
        """Creates the agent_tool_association table."""
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

    async def _create_chat_sessions_table(self, conn: asyncpg.Connection):
        """Creates the chat_sessions table."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
                title TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        logger.info("Ensured 'chat_sessions' table exists in PostgreSQL.")

    async def _create_chat_messages_table(self, conn: asyncpg.Connection):
        """Creates the chat_messages table."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
                sender_type TEXT NOT NULL,
                content JSONB NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_partial BOOLEAN DEFAULT FALSE,
                message_type TEXT NOT NULL DEFAULT 'ai'
            );
        """)
        logger.info("Ensured 'chat_messages' table exists in PostgreSQL.")

    async def _create_chat_summaries_table(self, conn: asyncpg.Connection):
        """Creates the chat_summaries table."""
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

    async def _column_exists(self, conn: asyncpg.Connection, table_name: str, column_name: str) -> bool:
        """Helper to check if a column exists."""
        return await conn.fetchval(f"""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """)

    async def _get_column_type(self, conn: asyncpg.Connection, table_name: str, column_name: str) -> Optional[str]:
        """Helper to check column type."""
        return await conn.fetchval(f"""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """)

    async def _update_agents_schema(self, conn: asyncpg.Connection):
        """Updates agents table schema."""
        # Add missing columns
        columns_to_add = [
            ('last_used', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('total_sessions', 'INTEGER DEFAULT 0'),
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            # Added the new column for allowed tool names
            ('allowed_tool_names', 'JSONB')
        ]
        
        for column_name, column_def in columns_to_add:
            if not await self._column_exists(conn, 'agents', column_name):
                logger.warning(f"Column '{column_name}' not found. Adding it to 'agents' table.")
                await conn.execute(f"ALTER TABLE agents ADD COLUMN {column_name} {column_def};")
                logger.info(f"Added '{column_name}' column to 'agents' table.")

        # Ensure JSONB types
        jsonb_columns = ['settings', 'bio', 'lore', 'knowledge']
        for col in jsonb_columns:
            col_type = await self._get_column_type(conn, 'agents', col)
            if col_type and col_type.lower() == 'text':
                logger.warning(f"Column '{col}' is of type TEXT. Altering to JSONB.")
                await conn.execute(f"UPDATE agents SET {col} = to_jsonb({col}) WHERE {col} IS NOT NULL;")
                await conn.execute(f"ALTER TABLE agents ALTER COLUMN {col} TYPE JSONB USING {col}::jsonb;")
                logger.info(f"Altered '{col}' column to JSONB.")

    async def _update_tools_schema(self, conn: asyncpg.Connection):
        """Updates tools table schema."""
        columns_to_add = [
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
        ]
        
        for column_name, column_def in columns_to_add:
            if not await self._column_exists(conn, 'tools', column_name):
                logger.warning(f"Column '{column_name}' not found. Adding it to 'tools' table.")
                await conn.execute(f"ALTER TABLE tools ADD COLUMN {column_name} {column_def};")
                logger.info(f"Added '{column_name}' column to 'tools' table.")

    async def _update_agent_tool_association_schema(self, conn: asyncpg.Connection):
        """Updates agent_tool_association table schema."""
        columns_to_add = [
            ('is_enabled', 'BOOLEAN NOT NULL DEFAULT TRUE'),
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
        ]
        
        for column_name, column_def in columns_to_add:
            if not await self._column_exists(conn, 'agent_tool_association', column_name):
                logger.warning(f"Column '{column_name}' not found. Adding it to 'agent_tool_association' table.")
                await conn.execute(f"ALTER TABLE agent_tool_association ADD COLUMN {column_name} {column_def};")
                logger.info(f"Added '{column_name}' column to 'agent_tool_association' table.")

    async def _update_chat_sessions_schema(self, conn: asyncpg.Connection):
        """Updates chat_sessions table schema."""
        columns_to_add = [
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('title', 'TEXT')
        ]
        
        for column_name, column_def in columns_to_add:
            if not await self._column_exists(conn, 'chat_sessions', column_name):
                logger.warning(f"Column '{column_name}' not found. Adding it to 'chat_sessions' table.")
                await conn.execute(f"ALTER TABLE chat_sessions ADD COLUMN {column_name} {column_def};")
                logger.info(f"Added '{column_name}' column to 'chat_sessions' table.")

    async def _update_chat_messages_schema(self, conn: asyncpg.Connection):
        """Updates chat_messages table schema."""
        # Check and update content column to JSONB
        content_type = await self._get_column_type(conn, 'chat_messages', 'content')
        if content_type and content_type.lower() == 'text':
            logger.warning("Column 'content' in 'chat_messages' is TEXT. Altering to JSONB.")
            await conn.execute("""
                UPDATE chat_messages
                SET content = to_jsonb(content)
                WHERE content IS NOT NULL;
            """)
            await conn.execute("ALTER TABLE chat_messages ALTER COLUMN content TYPE JSONB USING content::jsonb;")
            logger.info("Altered 'content' column in 'chat_messages' to JSONB.")

        columns_to_add = [
            ('is_partial', 'BOOLEAN DEFAULT FALSE'),
            ('message_type', 'TEXT NOT NULL DEFAULT \'ai\''),
            ('timestamp', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()')
        ]
        
        for column_name, column_def in columns_to_add:
            if not await self._column_exists(conn, 'chat_messages', column_name):
                logger.warning(f"Column '{column_name}' not found. Adding it to 'chat_messages' table.")
                await conn.execute(f"ALTER TABLE chat_messages ADD COLUMN {column_name} {column_def};")
                logger.info(f"Added '{column_name}' column to 'chat_messages' table.")

    async def _update_chat_summaries_schema(self, conn: asyncpg.Connection):
        """Updates chat_summaries table schema."""
        columns_to_add = [
            ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('updated_at', 'TIMESTAMP WITH TIME ZONE DEFAULT NOW()'),
            ('message_count', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_def in columns_to_add:
            if not await self._column_exists(conn, 'chat_summaries', column_name):
                logger.warning(f"Column '{column_name}' not found. Adding it to 'chat_summaries' table.")
                await conn.execute(f"ALTER TABLE chat_summaries ADD COLUMN {column_name} {column_def};")
                logger.info(f"Added '{column_name}' column to 'chat_summaries' table.")

        # Ensure summary_text is TEXT, not JSONB
        summary_text_type = await self._get_column_type(conn, 'chat_summaries', 'summary_text')
        if summary_text_type and summary_text_type.lower() == 'jsonb':
            logger.warning("Column 'summary_text' in 'chat_summaries' is JSONB. Altering to TEXT.")
            await conn.execute("ALTER TABLE chat_summaries ALTER COLUMN summary_text TYPE TEXT USING summary_text::text;")
            logger.info("Altered 'summary_text' column in 'chat_summaries' to TEXT.")
