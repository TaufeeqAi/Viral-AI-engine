# agent/agent-api/db/base_repository.py

import asyncpg
from abc import ABC
from typing import Optional


class BaseRepository(ABC):
    """
    Base repository class providing common database operations.
    Follows Dependency Inversion Principle - depends on abstractions, not concretions.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _execute_query(self, query: str, *args, conn: Optional[asyncpg.Connection] = None):
        """Execute a query with optional existing connection."""
        if conn:
            return await conn.execute(query, *args)
        else:
            async with self.pool.acquire() as connection:
                return await connection.execute(query, *args)

    async def _fetch_one(self, query: str, *args, conn: Optional[asyncpg.Connection] = None):
        """Fetch a single row with optional existing connection."""
        if conn:
            return await conn.fetchrow(query, *args)
        else:
            async with self.pool.acquire() as connection:
                return await connection.fetchrow(query, *args)

    async def _fetch_all(self, query: str, *args, conn: Optional[asyncpg.Connection] = None):
        """Fetch all rows with optional existing connection."""
        if conn:
            return await conn.fetch(query, *args)
        else:
            async with self.pool.acquire() as connection:
                return await connection.fetch(query, *args)

    async def _fetch_value(self, query: str, *args, conn: Optional[asyncpg.Connection] = None):
        """Fetch a single value with optional existing connection."""
        if conn:
            return await conn.fetchval(query, *args)
        else:
            async with self.pool.acquire() as connection:
                return await connection.fetchval(query, *args)