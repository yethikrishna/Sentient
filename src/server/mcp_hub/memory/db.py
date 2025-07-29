import os
import logging
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Embedding dimensions based on the chosen model in constants.py
EMBEDDING_MODEL_REPO_ID = os.getenv("EMBEDDING_MODEL_REPO_ID", "BAAI/bge-small-en-v1.5")
# This is a common dimension for bge-small models. Adjust if you change the model.
EMBEDDING_DIM = 384

_driver: Driver = None

def get_neo4j_driver() -> Driver:
    """Initializes and returns a singleton Neo4j driver instance."""
    global _driver
    if _driver is None:
        if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
            raise ValueError("Neo4j connection details are not configured in the environment.")
        logger.info(f"Initializing Neo4j driver for URI: {NEO4J_URI}")
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    return _driver

def close_neo4j_driver():
    """Closes the Neo4j driver connection."""
    global _driver
    if _driver is not None:
        logger.info("Closing Neo4j driver.")
        _driver.close()
        _driver = None

def setup_neo4j_constraints_and_indexes():
    """Ensures all necessary constraints and indexes are created in the database."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        logger.info("Setting up Neo4j constraints and vector indexes...")

        # Constraints for uniqueness and faster lookups
        session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
        session.run("CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")

        # Vector Index for RAG
        # Enterprise Edition of Neo4j is required for this feature.
        try:
            session.run(f"""
                CREATE VECTOR INDEX `entity_title_embeddings` IF NOT EXISTS
                FOR (e:Entity) ON (e.title_embedding)
                OPTIONS {{ indexConfig: {{
                    `vector.dimensions`: {EMBEDDING_DIM},
                    `vector.similarity_function`: 'cosine'
                }}}}
            """)
            session.run(f"""
                CREATE VECTOR INDEX `entity_description_embeddings` IF NOT EXISTS
                FOR (e:Entity) ON (e.description_embedding)
                OPTIONS {{ indexConfig: {{
                    `vector.dimensions`: {EMBEDDING_DIM},
                    `vector.similarity_function`: 'cosine'
                }}}}
            """)
            logger.info("Vector indexes for Entity embeddings created successfully.")
        except Exception as e:
            logger.error(f"Could not create vector indexes. Ensure you are running Neo4j Enterprise Edition. Error: {e}")

        logger.info("Neo4j setup complete.")