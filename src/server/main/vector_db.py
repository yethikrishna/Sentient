# Create new file: src/server/main/vector_db.py
import os
import chromadb
import logging
from chromadb.utils import embedding_functions

# --- Configuration ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8002))
EMBEDDING_MODEL_REPO_ID = os.getenv("EMBEDDING_MODEL_REPO_ID", "BAAI/bge-small-en-v1.5")
CONVERSATION_SUMMARIES_COLLECTION_NAME = "conversation_summaries"

logger = logging.getLogger(__name__)

# --- Singleton Client Instance ---
_client = None
_embedding_function = None

def get_chroma_client():
    """
    Initializes and returns a singleton ChromaDB HTTP client.
    """
    global _client
    if _client is None:
        try:
            logger.info(f"Initializing ChromaDB client for host={CHROMA_HOST}, port={CHROMA_PORT}")
            _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            # Ping the server to ensure it's alive
            _client.heartbeat()
            logger.info("ChromaDB client connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}: {e}", exc_info=True)
            _client = None  # Reset on failure
            raise ConnectionError("Could not connect to ChromaDB service.") from e
    return _client

def get_embedding_function():
    """
    Initializes and returns a singleton sentence-transformer embedding function.
    """
    global _embedding_function
    if _embedding_function is None:
        logger.info(f"Initializing SentenceTransformer embedding model: {EMBEDDING_MODEL_REPO_ID}")
        # This will download the model on first use if not cached
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_REPO_ID
        )
        logger.info("SentenceTransformer model loaded.")
    return _embedding_function

def get_conversation_summaries_collection():
    """
    Gets or creates the collection for storing conversation summaries.
    """
    client = get_chroma_client()
    embedding_function = get_embedding_function()
    
    collection = client.get_or_create_collection(
        name=CONVERSATION_SUMMARIES_COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"} # Use cosine distance for similarity
    )
    return collection