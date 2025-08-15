# agent/agent-api/db/database_connection.py

import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Manages database connection pool and basic connection operations.
    Follows Single Responsibility Principle - only handles connections.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        logger.info("DatabaseConnection initialized.")

    async def connect(self):
        """Initializes the connection pool."""
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

    def get_pool(self) -> asyncpg.Pool:
        """Returns the connection pool."""
        if not self.pool:
            raise RuntimeError("Database connection pool not initialized. Call connect() first.")
        return self.pool