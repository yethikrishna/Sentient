import os
import logging
from pymongo import MongoClient
from neo4j import GraphDatabase

from ..config import (
    MONGO_URI, MONGO_DB_NAME,
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
)
from .utils import Neo4jMemoryManager, MongoMemoryManager

logger = logging.getLogger(__name__)

# --- Singleton Instances ---
neo4j_driver = None
mongo_client = None

neo4j_manager: Neo4jMemoryManager | None = None
mongo_manager_instance: MongoMemoryManager | None = None

def initialize_memory_managers():
    global neo4j_driver, mongo_client
    global neo4j_manager, mongo_manager_instance
    
    try:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        neo4j_driver.verify_connectivity()
        neo4j_manager = Neo4jMemoryManager(neo4j_driver)
        logger.info("Neo4j Memory Manager initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j Memory Manager: {e}", exc_info=True)

    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_manager_instance = MongoMemoryManager(mongo_client, MONGO_DB_NAME)
        logger.info("MongoDB Memory Manager initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB Memory Manager: {e}", exc_info=True)

def close_memory_managers():
    if neo4j_driver:
        neo4j_driver.close()
        logger.info("Neo4j driver closed.")
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB client for memory closed.")