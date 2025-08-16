import os
import asyncpg
import asyncio
from dotenv import load_dotenv
from typing import Dict

from fastmcp.utilities.logging import get_logger
from .constants import TOPICS

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

logger = get_logger(__name__)

# PostgreSQL connection details
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# Embedding dimensions based on the chosen model.
# Google's gemini-embedding-001 can be truncated. We are using 768.
# See: https://ai.google.dev/gemini-api/docs/embeddings#controlling_embedding_size
EMBEDDING_DIM = 768

# Dictionary to store connection pools, keyed by the event loop they belong to.
_pools: Dict[asyncio.AbstractEventLoop, asyncpg.Pool] = {}

async def get_db_pool() -> asyncpg.Pool:
    """Initializes and returns a singleton PostgreSQL connection pool for the current event loop."""
    global _pools
    loop = asyncio.get_running_loop()
    
    # Get the pool for the current event loop
    pool = _pools.get(loop)
    
    # If the pool doesn't exist for this loop, or it's closing, create a new one.
    if pool is None or pool.is_closing():
        if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
            raise ValueError("PostgreSQL connection details are not configured in the environment.")

        logger.info(f"Initializing PostgreSQL connection pool for db: {POSTGRES_DB} on event loop {id(loop)}.")
        pool = await asyncpg.create_pool(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        _pools[loop] = pool # Store the new pool in the dictionary
    else:
        logger.debug(f"Returning existing PostgreSQL connection pool for event loop {id(loop)}.")
    return pool

async def close_db_pool_for_loop(loop: asyncio.AbstractEventLoop):
    """Closes the connection pool associated with a specific event loop and removes it from the global dict."""
    global _pools
    pool = _pools.pop(loop, None)
    if pool:
        if not pool.is_closing():
            logger.info(f"Closing PostgreSQL pool for event loop {id(loop)}.")
            await pool.close()
        else:
            logger.debug(f"Pool for event loop {id(loop)} was already closing.")

async def close_db_pool():
    """Closes all PostgreSQL connection pools managed by this module."""
    global _pools
    if _pools:
        logger.info("Closing all PostgreSQL connection pools.")
        # Iterate over a copy of items to safely modify the dictionary during iteration
        for loop, pool in list(_pools.items()):
            if not pool.is_closing():
                await pool.close()
            # Remove the pool from the dictionary after closing
            del _pools[loop]
    else:
        logger.debug("No PostgreSQL connection pools to close.")

async def setup_database():
    """Ensures all necessary tables, indexes, and static data are created in the database."""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        logger.info("Acquired DB connection for database setup.")
        async with connection.transaction():
            logger.info("Setting up PostgreSQL database schema...")

            await connection.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL
                );
            """)

            await connection.execute(f"""
                CREATE TABLE IF NOT EXISTS facts (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBEDDING_DIM}),
                    source TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
                );
            """)

            # This ensures the vector dimension is up-to-date with the model configuration.
            await connection.execute(f"""
                ALTER TABLE facts ALTER COLUMN embedding TYPE VECTOR({EMBEDDING_DIM});
            """)

            await connection.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                   NEW.updated_at = NOW();
                   RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)

            await connection.execute("""
                DROP TRIGGER IF EXISTS update_facts_updated_at ON facts;
                CREATE TRIGGER update_facts_updated_at
                BEFORE UPDATE ON facts
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """)

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS fact_topics (
                    fact_id INTEGER NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
                    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                    PRIMARY KEY (fact_id, topic_id)
                );
            """)

            logger.info("Creating indexes...")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_user_id ON facts (user_id);")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_user_id_source ON facts (user_id, source);")
            await connection.execute(f"CREATE INDEX IF NOT EXISTS idx_facts_embedding_cos ON facts USING hnsw (embedding vector_cosine_ops);")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_expires_at ON facts (expires_at) WHERE expires_at IS NOT NULL;")

            logger.info("Populating topics table...")
            for topic in TOPICS:
                await connection.execute("""
                    INSERT INTO topics (name, description)
                    VALUES ($1, $2)
                    ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;
                """, topic['name'], topic['description'])

            logger.info("Database setup complete.")