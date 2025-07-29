import os
import logging
import asyncpg
from dotenv import load_dotenv

from .constants import TOPICS

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

# PostgreSQL connection details
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# Embedding dimensions based on the chosen model.
# BAAI/bge-small-en-v1.5 has 384 dimensions.
# Note: The plan mentions 1536, which is for models like OpenAI's text-embedding-ada-002.
# Adjust EMBEDDING_DIM if you change the embedding model.
EMBEDDING_DIM = 384

_pool: asyncpg.Pool = None

async def get_db_pool() -> asyncpg.Pool:
    """Initializes and returns a singleton PostgreSQL connection pool."""
    global _pool
    if _pool is None:
        if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
            raise ValueError("PostgreSQL connection details are not configured in the environment.")
        logger.info(f"Initializing PostgreSQL connection pool for db: {POSTGRES_DB}")
        _pool = await asyncpg.create_pool(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
    return _pool

async def close_db_pool():
    """Closes the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing PostgreSQL connection pool.")
        await _pool.close()
        _pool = None

async def setup_database():
    """Ensures all necessary tables, indexes, and static data are created in the database."""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
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

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS subtopics (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                    UNIQUE(name, topic_id)
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
                CREATE TABLE IF NOT EXISTS fact_subtopics (
                    fact_id INTEGER NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
                    subtopic_id INTEGER NOT NULL REFERENCES subtopics(id) ON DELETE CASCADE,
                    PRIMARY KEY (fact_id, subtopic_id)
                );
            """)

            logger.info("Creating indexes...")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_user_id ON facts (user_id);")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_user_id_source ON facts (user_id, source);")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_facts_user_id_source ON facts (user_id, source);")
            await connection.execute("CREATE INDEX IF NOT EXISTS idx_subtopics_topic_id ON subtopics (topic_id);")
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