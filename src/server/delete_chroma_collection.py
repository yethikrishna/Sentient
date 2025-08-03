import os
import logging
import chromadb
from dotenv import load_dotenv

# --- Configuration ---
# This script is designed to be run from the `src/server` directory.
# It will load your existing .env file to get the ChromaDB connection details.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded environment variables from: {dotenv_path}")
else:
    logging.warning(f".env file not found at {dotenv_path}. Relying on shell environment variables.")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8002))
COLLECTION_TO_DELETE = "conversation_summaries"

def delete_collection_safely():
    """
    Connects to ChromaDB, confirms with the user, and deletes the specified collection.
    """
    print("\n" + "="*80)
    print("⚠️  WARNING: DESTRUCTIVE ACTION AHEAD ⚠️")
    print("="*80)
    print(f"This script will permanently delete the ChromaDB collection named:")
    print(f"  '{COLLECTION_TO_DELETE}'")
    print("\nThis action will erase all existing conversation summary embeddings and CANNOT be undone.")
    print("New embeddings will be generated over time, but this requires re-processing your data.")
    print("="*80 + "\n")

    try:
        logging.info(f"Connecting to ChromaDB at http://{CHROMA_HOST}:{CHROMA_PORT}...")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        client.heartbeat() # Check if the server is alive
        logging.info("Successfully connected to ChromaDB.")
    except Exception as e:
        logging.error(f"Failed to connect to ChromaDB: {e}")
        logging.error("Please ensure your ChromaDB instance is running and accessible.")
        return

    # --- Pre-deletion Check ---
    try:
        collections = client.list_collections()
        collection_names = [c.name for c in collections]
        logging.info(f"Found existing collections: {collection_names}")

        if COLLECTION_TO_DELETE not in collection_names:
            logging.warning(f"The collection '{COLLECTION_TO_DELETE}' does not exist. Nothing to do.")
            return
    except Exception as e:
        logging.error(f"Failed to list collections: {e}")
        return

    # --- User Confirmation ---
    try:
        confirm = input(f"To confirm deletion of '{COLLECTION_TO_DELETE}', please type 'DELETE' and press Enter: ")
        if confirm.strip() != 'DELETE':
            print("\n❌ Deletion cancelled. No changes were made.")
            return
    except KeyboardInterrupt:
        print("\n\n❌ Deletion cancelled by user. No changes were made.")
        return

    # --- Deletion ---
    try:
        logging.info(f"Proceeding with deletion of '{COLLECTION_TO_DELETE}'...")
        client.delete_collection(name=COLLECTION_TO_DELETE)
        logging.info(f"✅ Collection '{COLLECTION_TO_DELETE}' has been successfully deleted.")
    except Exception as e:
        logging.error(f"An error occurred while trying to delete the collection: {e}")
        return

    # --- Post-deletion Info ---
    try:
        collections_after = client.list_collections()
        collection_names_after = [c.name for c in collections_after]
        logging.info(f"Current collections after deletion: {collection_names_after}")
    except Exception as e:
        logging.error(f"Could not verify collections after deletion: {e}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Restart your main server application.")
    print("   - The server will now automatically create a new, empty collection with the correct embedding function.")
    print("2. The background summarization task will gradually re-populate the collection over time.")
    print("="*80)


if __name__ == "__main__":
    delete_collection_safely()