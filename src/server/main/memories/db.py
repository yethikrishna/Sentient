import os
import logging
import asyncpg
from dotenv import load_dotenv

# This is a simplified version of the db setup from the memory MCP
# to be used by the main server for read-only memory access.

logger = logging.getLogger(__name__)

# --- Environment Loading ---
# This ensures that when this module is imported, it uses the same env config as the main app
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    server_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dotenv_local_path = os.path.join(server_root, '.env.local')
    dotenv_path = os.path.join(server_root, '.env')
    load_path = dotenv_local_path if os.path.exists(dotenv_local_path) else dotenv_path
    if os.path.exists(load_path):
        load_dotenv(dotenv_path=load_path)
elif ENVIRONMENT == 'selfhost':
    server_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dotenv_path = os.path.join(server_root, '.env.selfhost')
    load_dotenv(dotenv_path=dotenv_path)

# --- PostgreSQL Connection Details ---
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

_pool: asyncpg.Pool = None

async def get_db_pool() -> asyncpg.Pool:
    """Initializes and returns a singleton PostgreSQL connection pool."""
    global _pool
    if _pool is None:
        if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
            raise ValueError("PostgreSQL connection details are not configured in the environment.")
        logger.info(f"Initializing PostgreSQL connection pool for memories API...")
        try:
            _pool = await asyncpg.create_pool(
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
            )
            logger.info("PostgreSQL connection pool for memories API initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}", exc_info=True)
            raise
    return _pool

async def close_db_pool():
    """Closes the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing PostgreSQL connection pool for memories API.")
        await _pool.close()
        _pool = None