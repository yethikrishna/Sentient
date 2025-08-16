import os
import asyncio
import asyncpg
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# This script is designed to be run from the `src/server` directory.
# It will load your existing .env file to get the PostgreSQL connection details.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded environment variables from: {dotenv_path}")
else:
    logging.warning(f".env file not found at {dotenv_path}. Relying on shell environment variables.")

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

async def clear_memory_database():
    """Connects to PostgreSQL and truncates memory-related tables after user confirmation."""
    if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
        logging.error("PostgreSQL connection details are not fully configured in your .env file.")
        return

    print("\n" + "="*80)
    print("⚠️  DANGER: DESTRUCTIVE ACTION AHEAD ⚠️")
    print("="*80)
    print("This script will permanently delete ALL data from the following PostgreSQL tables:")
    print("  - facts")
    print("  - fact_topics")
    print("\nThis action will erase all user memories and CANNOT be undone.")
    print("This is useful for starting with a completely fresh memory store.")
    print("="*80 + "\n")

    try:
        confirm = input(f"To confirm deletion, please type 'DELETE ALL MEMORIES' and press Enter: ")
        if confirm.strip() != 'DELETE ALL MEMORIES':
            print("\n❌ Deletion cancelled. No changes were made.")
            return
    except KeyboardInterrupt:
        print("\n\n❌ Deletion cancelled by user. No changes were made.")
        return

    conn = None
    try:
        logging.info(f"Connecting to PostgreSQL database '{POSTGRES_DB}' on {POSTGRES_HOST}...")
        conn = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        logging.info("Successfully connected to PostgreSQL.")

        logging.info("Truncating tables: facts, fact_topics...")
        # TRUNCATE is faster than DELETE and also resets identity columns. CASCADE handles foreign keys.
        await conn.execute("TRUNCATE TABLE facts, fact_topics RESTART IDENTITY CASCADE;")
        logging.info("✅ Tables have been successfully cleared.")

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if conn:
            await conn.close()
            logging.info("PostgreSQL connection closed.")

if __name__ == "__main__":
    asyncio.run(clear_memory_database())
