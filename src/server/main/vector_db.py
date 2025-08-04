import os
import chromadb
import logging
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
from dotenv import load_dotenv


# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8002))
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "models/gemini-embedding-001")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
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
    Initializes and returns a singleton Google Generative AI embedding function.
    """
    global _embedding_function
    if _embedding_function is None:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set. Cannot initialize Google embedding function.")
            raise ValueError("GEMINI_API_KEY is not configured.")
        
        logger.info(f"Initializing Google Generative AI embedding model: {EMBEDDING_MODEL_NAME}")
        try:
            _embedding_function = GoogleGenerativeAiEmbeddingFunction(
                api_key=GEMINI_API_KEY,
                model_name=EMBEDDING_MODEL_NAME
                # The default task_type is RETRIEVAL_DOCUMENT, which is appropriate for storing summaries.
            )
            logger.info("Google Generative AI embedding model loaded.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleGenerativeAiEmbeddingFunction: {e}", exc_info=True)
            _embedding_function = None
            raise
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