import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
from bson import ObjectId
from fastmcp import FastMCP, Context
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from neo4j import GraphDatabase, exceptions as Neo4jExceptions
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

from . import auth

# --- General Configuration & Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set the Neo4j notifications logger to a higher level to hide informational messages
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

# --- Constants ---
class Cfg:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_main_db")
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    CATEGORIES = ["Personal", "Professional", "Social", "Financial", "Health", "Preferences", "Events", "General"]

# --- Embedding Model Singleton ---
try:
    embedding_model = SentenceTransformer(Cfg.EMBEDDING_MODEL)
    logger.info(f"Successfully loaded SentenceTransformer model: {Cfg.EMBEDDING_MODEL}")
except Exception as e:
    logger.error(f"Failed to load sentence-transformer model. Error: {e}")
    exit(1)

def get_embedding(text: str) -> List[float]:
    return embedding_model.encode(text, convert_to_tensor=False).tolist()

# --- Neo4j Knowledge Graph Memory Manager ---
class Neo4jKnowledgeGraph:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver.verify_connectivity()
        logger.info(f"Successfully connected to Neo4j: {uri}")
        self._setup_database()

    def _setup_database(self):
        with self._driver.session() as session:
            session.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
            session.run("CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
            session.run("CREATE VECTOR INDEX `observation-embeddings` IF NOT EXISTS FOR (o:Observation) ON (o.embedding) OPTIONS { indexConfig: { `vector.dimensions`: 384, `vector.similarity_function`: 'cosine' } }")
            session.run("UNWIND $categories as category_name MERGE (c:Category {name: category_name})", categories=Cfg.CATEGORIES)
            logger.info("Ensured Neo4j constraints, indexes, and categories.")

    def close(self):
        if self._driver: self._driver.close()

    def _sanitize_relation_type(self, relation_type: str) -> str:
        return relation_type.upper().replace(' ', '_').replace('-', '_')

    def upsert_memory_fact(self, user_id: str, fact_text: str, category: str, relations: List[Dict]) -> Dict[str, Any]:
        fact_embedding = get_embedding(fact_text)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._driver.session() as session:
            session.run("""
                MERGE (u:User:Entity {user_id: $user_id})
                ON CREATE SET u.created_at = datetime($now_iso), u.name = 'User Profile'
                
                CREATE (o:Observation {
                    text: $fact_text, embedding: $fact_embedding,
                    created_at: datetime($now_iso), last_accessed_at: datetime($now_iso)
                })
                
                MERGE (u)-[:HAS_OBSERVATION]->(o)
                WITH u, o
                MATCH (c:Category {name: $category})
                MERGE (o)-[:IN_CATEGORY]->(c)
            """, user_id=user_id, now_iso=now_iso, fact_text=fact_text, fact_embedding=fact_embedding, category=category)

            relations_created_summary = []
            for rel in relations:
                rel_type = self._sanitize_relation_type(rel['type'])
                tx_result = session.execute_write(
                    self._create_relation_tx, user_id, rel['from'], rel['to'], rel_type
                )
                if tx_result:
                    relations_created_summary.append(tx_result)

        return {"status": "success", "fact_added": fact_text, "relations_processed": relations_created_summary}

    @staticmethod
    def _create_relation_tx(tx, user_id, from_entity_name, to_entity_name, rel_type):
        from_node_alias = 'a'
        from_match_clause = f"MATCH ({from_node_alias}:User {{user_id: $user_id}})" if from_entity_name.lower() == 'user' \
                            else f"MERGE ({from_node_alias}:Entity {{user_id: $user_id, name: $from_name}})"
        
        to_node_alias = 'b'
        to_match_clause = f"MATCH ({to_node_alias}:User {{user_id: $user_id}})" if to_entity_name.lower() == 'user' \
                          else f"MERGE ({to_node_alias}:Entity {{user_id: $user_id, name: $to_name}})"

        query = f"""
        {from_match_clause}
        WITH {from_node_alias}
        {to_match_clause}
        MERGE ({from_node_alias})-[r:`{rel_type}`]->({to_node_alias})
        RETURN $from_name as from_name, $to_name as to_name, $rel_type_orig as type
        """
        result = tx.run(query, user_id=user_id, from_name=from_entity_name, to_name=to_entity_name, rel_type_orig=rel_type)
        return result.single()

    def semantic_search(self, user_id: str, query_text: str, categories: Optional[List[str]] = None, limit: int = 5) -> List[Dict]:
        query_embedding = get_embedding(query_text)
        
        category_match_clause = ""
        if categories:
            category_match_clause = "MATCH (o)-[:IN_CATEGORY]->(c:Category) WHERE c.name IN $categories"

        query = f"""
            CALL db.index.vector.queryNodes('observation-embeddings', $limit, $query_embedding) YIELD node AS o, score
            MATCH (e:Entity {{user_id: $user_id}})-[:HAS_OBSERVATION]->(o)
            SET o.last_accessed_at = datetime()
            WITH o, e, score
            {category_match_clause}
            RETURN
                o.text as fact,
                c.name as category,
                score as similarity
            LIMIT $limit
        """
        
        with self._driver.session() as session:
            results = session.run(query, limit=limit, query_embedding=query_embedding, user_id=user_id, categories=categories)
            return [{"fact": r["fact"], "category": r["category"], "similarity": round(r["similarity"], 2)} for r in results]
            
    def get_full_user_profile(self, user_id: str) -> Dict[str, List[str]]:
        query = """
            MATCH (u:User:Entity {user_id: $user_id})-[:HAS_OBSERVATION]->(o:Observation)-[:IN_CATEGORY]->(c:Category)
            RETURN c.name as category, collect(o.text) as facts
        """
        with self._driver.session() as session:
            results = session.run(query, user_id=user_id)
            return {r["category"]: r["facts"] for r in results}
            
    def clear_all_long_term_memories(self, user_id: str):
        with self._driver.session() as session:
            # This deletes observations and standalone entities linked to the user.
            # It keeps the User node itself.
            result = session.run("""
                MATCH (u:User {user_id: $user_id})-[r:HAS_OBSERVATION]->(o:Observation)
                DETACH DELETE o
            """, user_id=user_id)
            return result.consume().counters.nodes_deleted

# --- MongoDB Short-Term Memory Manager ---
class MongoMemory:
    def __init__(self, client):
        self.db = client[Cfg.MONGO_DB_NAME]
        self.stm_collection = self.db["short_term_memories"]
        self.chat_history_collection = self.db["chat_history"]
        self._setup_database()

    def _setup_database(self):
        if "expire_at_ttl" not in self.stm_collection.index_information():
            self.stm_collection.create_index("expire_at", name="expire_at_ttl", expireAfterSeconds=0)
        if "user_category_idx" not in self.stm_collection.index_information():
            self.stm_collection.create_index([("user_id", 1), ("category", 1)], name="user_category_idx")
        chat_indexes = self.chat_history_collection.index_information()
        if "message_text_idx" not in chat_indexes:
            self.chat_history_collection.create_index([("messages.message", "text")], name="message_text_idx")

    def _cosine_similarity(self, vec1, vec2):
        vec1_np, vec2_np = np.array(vec1), np.array(vec2)
        dot_product = np.dot(vec1_np, vec2_np)
        norm_vec1 = np.linalg.norm(vec1_np)
        norm_vec2 = np.linalg.norm(vec2_np)
        if norm_vec1 == 0 or norm_vec2 == 0: return 0.0
        return float(dot_product / (norm_vec1 * norm_vec2))

    def add_memory(self, user_id, content, ttl_seconds, category):
        # Check for existing memory to prevent duplicates
        existing_memory = self.stm_collection.find_one({"user_id": user_id, "content": content})
        now = datetime.now(timezone.utc)

        if existing_memory:
            # If it exists, just update its expiration to "refresh" it
            logger.info(f"Memory content already exists for user {user_id}. Refreshing TTL.")
            self.stm_collection.update_one(
                {"_id": existing_memory["_id"]},
                {"$set": {"expire_at": now + timedelta(seconds=ttl_seconds), "last_accessed_at": now}}
            )
            return self._serialize_mongo_doc(self.stm_collection.find_one({"_id": existing_memory["_id"]}))

        embedding = get_embedding(content)
        doc = {
            "user_id": user_id, "content": content, "content_embedding": embedding,
            "category": category, "expire_at": now + timedelta(seconds=ttl_seconds),
            "created_at": now, "last_accessed_at": now
        }
        self.stm_collection.insert_one(doc)
        logger.info(f"Added new memory for user {user_id}.")
        return self._serialize_mongo_doc(doc)

    def search_memories(self, user_id, query_text, categories=None, limit=5):
        query_embedding = get_embedding(query_text)
        mongo_filter = {"user_id": user_id}
        if categories: mongo_filter["category"] = {"$in": [c.capitalize() for c in categories]}
        
        candidate_docs = list(self.stm_collection.find(mongo_filter))
        if not candidate_docs: return []

        scored_docs = [
            {'similarity': self._cosine_similarity(query_embedding, doc['content_embedding']), 'doc': self._serialize_mongo_doc(doc)}
            for doc in candidate_docs if 'content_embedding' in doc and doc['content_embedding']
        ]
        
        sorted_results = sorted(scored_docs, key=lambda x: x['similarity'], reverse=True)
        top_results = sorted_results[:limit]
        
        final_docs_to_return = []
        if top_results:
            doc_ids_to_update = [ObjectId(item['doc']['_id']) for item in top_results]
            self.stm_collection.update_many(
                {"_id": {"$in": doc_ids_to_update}},
                {"$set": {"last_accessed_at": datetime.now(timezone.utc)}}
            )
            for item in top_results:
                doc = item['doc']
                final_docs_to_return.append({
                    **doc, "similarity": round(item['similarity'], 2)
                })
        return final_docs_to_return

    def update_memory(self, memory_id: str, new_content: str, new_ttl_seconds: int):
        new_embedding = get_embedding(new_content)
        now = datetime.now(timezone.utc)
        update_doc = {
            "$set": {
                "content": new_content,
                "content_embedding": new_embedding,
                "expire_at": now + timedelta(seconds=new_ttl_seconds),
                "last_accessed_at": now
            }
        }
        result = self.stm_collection.update_one({"_id": ObjectId(memory_id)}, update_doc)
        return result.modified_count > 0

    def delete_memory(self, memory_id: str):
        result = self.stm_collection.delete_one({"_id": ObjectId(memory_id)})
        return result.deleted_count > 0

    def clear_all_short_term_memories(self, user_id: str):
        result = self.stm_collection.delete_many({"user_id": user_id})
        return result.deleted_count

    def search_chat_history(self, user_id: str, query_text: str, limit: int = 10):
        # Using a text index for search. Ensure index exists on `messages.message`.
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$unwind": "$messages"},
            {"$match": {"messages.message": {"$regex": query_text, "$options": "i"}}},
            {"$sort": {"messages.timestamp": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "message": "$messages"}}
        ]
        results_cursor = self.chat_history_collection.aggregate(pipeline)
        results = list(results_cursor)
        return [self._serialize_mongo_doc(r['message']) for r in results]

    def _serialize_mongo_doc(self, doc):
        if not doc: return None
        if "_id" in doc: doc["_id"] = str(doc["_id"])
        if "content_embedding" in doc: del doc["content_embedding"]
        for key, value in doc.items():
            if isinstance(value, datetime): doc[key] = value.isoformat()
        return doc

# --- Initialize Managers and MCP Server ---
kg_manager = Neo4jKnowledgeGraph(Cfg.NEO4J_URI, Cfg.NEO4J_USER, Cfg.NEO4J_PASSWORD)
mongo_client = MongoClient(Cfg.MONGO_URI)
memory_manager = MongoMemory(mongo_client)

mcp = FastMCP(
    name="SentientMemoryCompanionServer",
    instructions="This server provides a robust, dual-system memory for an AI companion. It has tools for saving and searching long-term (knowledge graph) and short-term (expiring) memories."
)

# --- MCP Tools ---
@mcp.tool()
def save_long_term_fact(ctx: Context, fact_text: str, category: str, relations: Optional[List[Dict]] = None) -> Dict:
    """
    Saves a permanent fact to the user's knowledge graph. Use for preferences, relationships, or key personal/professional details.
    To connect entities, use the 'relations' field. Use 'user' to refer to the primary user.
    Example relations: [{"from": "user", "to": "Innovatech", "type": "WORKS_AT"}, {"from": "Jordan", "to": "user", "type": "FRIEND_OF"}].
    
    :param fact_text: The string of information to remember. E.g., "I work at Innovatech as a software engineer."
    :param category: The category of this fact. Must be one of: Personal, Professional, Social, Financial, Health, Preferences, Events, General.
    :param relations: (Optional) A list of relationships to create between entities.
    """
    user_id = auth.get_user_id_from_context(ctx)
    if category not in Cfg.CATEGORIES: raise ValueError(f"Invalid category '{category}'. Must be one of {Cfg.CATEGORIES}")
    return kg_manager.upsert_memory_fact(user_id, fact_text, category, relations or [])

@mcp.tool()
def add_short_term_memory(ctx: Context, content: str, ttl_seconds: int, category: str) -> Dict:
    """
    Saves a temporary, expiring piece of information like a reminder or to-do item.
    
    :param content: The information to remember temporarily.
    :param ttl_seconds: How long to remember this for, in seconds. E.g., 3600 for one hour.
    :param category: The category of this memory. Must be one of: Personal, Professional, Social, Financial, Health, Preferences, Events, General.
    """
    user_id = auth.get_user_id_from_context(ctx)
    if category not in Cfg.CATEGORIES: raise ValueError(f"Invalid category '{category}'. Must be one of {Cfg.CATEGORIES}")
    return memory_manager.add_memory(user_id, content, ttl_seconds, category)

@mcp.tool()
def search_memories(ctx: Context, query_text: str, categories: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    Performs a semantic search across all memories (long and short term) to find relevant information. Use this before answering any user query.
    
    :param query_text: The question or topic to search for, e.g., "What do I do for work?".
    :param categories: (Optional) A list of categories to restrict the search to.
    """
    user_id = auth.get_user_id_from_context(ctx)
    ltm_results = kg_manager.semantic_search(user_id, query_text, categories)
    stm_results = memory_manager.search_memories(user_id, query_text, categories)
    return {"long_term_facts": ltm_results, "short_term_reminders": stm_results}

@mcp.tool()
def get_user_profile_summary(ctx: Context) -> Dict[str, List[str]]:
    """Retrieves a structured summary of everything known about the user from the long-term knowledge graph."""
    user_id = auth.get_user_id_from_context(ctx)
    return kg_manager.get_full_user_profile(user_id)

@mcp.tool()
def clear_all_long_term_memories(ctx: Context) -> Dict[str, Any]:
    """
    Deletes all long-term facts and observations for the user. This is a permanent action.
    """
    user_id = auth.get_user_id_from_context(ctx)
    deleted_count = kg_manager.clear_all_long_term_memories(user_id)
    return {"status": "success", "message": f"Successfully deleted {deleted_count} long-term memory nodes."}

@mcp.tool()
def clear_all_short_term_memories(ctx: Context) -> Dict[str, Any]:
    """
    Deletes all short-term memories for the user. This is a permanent action.
    """
    user_id = auth.get_user_id_from_context(ctx)
    deleted_count = memory_manager.clear_all_short_term_memories(user_id)
    return {"status": "success", "message": f"Successfully deleted {deleted_count} short-term memories."}

@mcp.tool()
def update_short_term_memory(ctx: Context, memory_id: str, new_content: str, new_ttl_seconds: int) -> Dict[str, Any]:
    """
    Updates the content and expiration of a specific short-term memory.

    :param memory_id: The unique ID of the memory to update.
    :param new_content: The new text content for the memory.
    :param new_ttl_seconds: The new time-to-live in seconds from now.
    """
    auth.get_user_id_from_context(ctx) # Just for auth check
    success = memory_manager.update_memory(memory_id, new_content, new_ttl_seconds)
    if success:
        return {"status": "success", "message": "Memory updated."}
    return {"status": "error", "message": "Memory not found or not updated."}

@mcp.tool()
def delete_short_term_memory(ctx: Context, memory_id: str) -> Dict[str, Any]:
    """Deletes a single short-term memory by its ID."""
    auth.get_user_id_from_context(ctx) # Just for auth check
    success = memory_manager.delete_memory(memory_id)
    if success:
        return {"status": "success", "message": "Memory deleted."}
    return {"status": "error", "message": "Memory not found."}

@mcp.tool()
def search_conversation_history(ctx: Context, query_text: str, limit: int = 10) -> List[Dict]:
    """
    Searches the user's entire past conversation history for specific keywords or topics.
    Use this as a last resort if `search_memories` does not return relevant information.
    
    :param query_text: The keywords or topic to search for in the conversation history.
    :param limit: The maximum number of messages to return. Defaults to 10.
    """
    user_id = auth.get_user_id_from_context(ctx)
    return memory_manager.search_chat_history(user_id, query_text, limit)

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", 8001))
    logger.info(f"Starting Sentient Memory Companion MCP Server on http://{host}:{port}")
    try:
        mcp.run(transport="sse", host=host, port=port)
    finally:
        if kg_manager: kg_manager.close()
        if mongo_client: mongo_client.close()
        logger.info("MCP Server shut down and DB connections closed.")