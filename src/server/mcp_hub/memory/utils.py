import os
import json
import logging
import asyncio
import re
import numpy as np
from typing import Dict, Any, List
from neo4j import Driver
from sklearn.metrics.pairwise import cosine_similarity
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from . import db, llm
from .constants import CATEGORIES
from .prompts import (
    text_dissection_user_prompt_template,
    information_extraction_user_prompt_template,
    query_classification_user_prompt_template,
    text_conversion_user_prompt_template,
    fact_extraction_user_prompt_template,
    graph_decision_user_prompt_template
)

logger = logging.getLogger(__name__)

# --- Module-level state (initialized by lifespan event) ---
embed_model: HuggingFaceEmbedding = None
agents: Dict[str, Any] = {}

# --- Initialization Functions ---
def initialize_embedding_model():
    global embed_model
    if embed_model is None:
        model_repo_id = os.getenv("EMBEDDING_MODEL_REPO_ID", "BAAI/bge-small-en-v1.5")
        logger.info(f"Initializing embedding model: {model_repo_id}")
        embed_model = HuggingFaceEmbedding(model_name=model_repo_id)

def initialize_agents():
    global agents
    if not agents:
        logger.info("Initializing all memory agents...")
        agents = {
            "dissection": llm.get_text_dissection_agent(),
            "extraction": llm.get_info_extraction_agent(),
            "classification": llm.get_query_classification_agent(),
            "conversion": llm.get_text_conversion_agent(),
            "fact": llm.get_fact_extraction_agent(),
            "decision": llm.get_crud_decision_agent(),
        }

def clean_llm_output(text: str) -> str:
    """
    Removes reasoning tags (e.g., <think>...</think>) and trims whitespace from LLM output.
    This is crucial for models that output their thought process.
    """
    # Use re.DOTALL to make '.' match newlines, and '?' for non-greedy matching.
    if not isinstance(text, str): # Safety check
        return ""
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text.strip()


# --- Core Graph Building Logic (Refactored) ---
async def build_initial_knowledge_graph(user_id: str, extracted_texts: List[Dict[str, str]]):
    driver = db.get_neo4j_driver()
    
    # Clear existing graph for this user ONLY
    with driver.session() as session:
        session.run("MATCH (u:User {user_id: $user_id})-[r]-() DETACH DELETE r", user_id=user_id)
        session.run("MATCH (u:User {user_id: $user_id}) DETACH DELETE u", user_id=user_id)
    
    await _create_predefined_graph(user_id, driver)

    # 1. Dissect all documents into categories
    categorized_texts = {}
    for entry in extracted_texts:
        text, source = entry["text"], entry["source"]
        if not text.strip(): continue
        
        prompt = text_dissection_user_prompt_template.format(text=text)
        dissected_data_raw = llm.run_agent_with_prompt(agents["dissection"], prompt)
        dissected_data = json.loads(clean_llm_output(dissected_data_raw))
        
        if dissected_data and isinstance(dissected_data.get("categories"), dict):
            for category, category_text in dissected_data["categories"].items():
                if category_text.strip():
                    categorized_texts.setdefault(category, []).append({"text": category_text, "source": source})

    if not categorized_texts:
        return "Failed to create graph: No information was categorized from the documents."

    # 2. Extract triplets from each categorized text
    all_triplets = {}
    for category, texts_with_sources in categorized_texts.items():
        for entry in texts_with_sources:
            text, source = entry["text"], entry["source"]
            prompt = information_extraction_user_prompt_template.format(category=category, text=text)
            extracted_data_raw = llm.run_agent_with_prompt(agents["extraction"], prompt)
            extracted_data = json.loads(clean_llm_output(extracted_data_raw))
            
            if extracted_data and isinstance(extracted_data.get("relationships"), list):
                if category not in all_triplets:
                    all_triplets[category] = []
                # Add source info to each relationship for traceability
                for rel in extracted_data["relationships"]:
                    rel["source_document"] = source
                all_triplets[category].extend(extracted_data["relationships"])

    if not all_triplets:
        return "Failed to create graph: No entities or relationships were extracted."

    # 3. Create the graph from all collected triplets
    await _create_graph_from_triplets(user_id, all_triplets, driver)
    return "Graph built successfully from documents."

async def _create_predefined_graph(user_id: str, driver: Driver):
    """Creates the root User node and connects it to predefined Category nodes."""
    with driver.session() as session:
        session.run("MERGE (u:User {user_id: $user_id})", user_id=user_id)
        for category in CATEGORIES:
            session.run("""
                MERGE (c:Category {name: $name})
                ON CREATE SET c.description = $description
                WITH c
                MATCH (u:User {user_id: $user_id})
                MERGE (u)-[:HAS_CATEGORY]->(c)
            """, name=category["name"], description=category["description"], user_id=user_id)

async def _create_graph_from_triplets(user_id: str, all_triplets: Dict[str, List], driver: Driver):
    """Populates the graph with entities and relationships for a specific user."""
    with driver.session() as session:
        for category, triplets in all_triplets.items():
            for triplet in triplets:
                source_name = triplet['source']
                target_name = triplet['target']
                rel_type = triplet['relationship'].upper().replace(" ", "_")
                source_props = triplet.get('source_properties', {})
                target_props = triplet.get('target_properties', {})
                source_doc = triplet.get('source_document', 'unknown')

                # Embeddings
                target_title_emb = embed_model.get_text_embedding(target_name)
                target_desc_emb = embed_model.get_text_embedding(target_props.get('description', ''))

                if source_name == category: # Relationship from Category to a new Entity
                    session.run("""
                        MATCH (u:User {user_id: $user_id})-[:HAS_CATEGORY]->(c:Category {name: $category})
                        MERGE (e:Entity {name: $target_name})
                        ON CREATE SET e.description = $target_desc, e.source = $source_doc, e.category = $category,
                                      e.title_embedding = $target_title_emb, e.description_embedding = $target_desc_emb
                        MERGE (c)-[r:`%s`]->(e)
                        MERGE (u)-[:OWNS]->(e)
                    """ % rel_type, user_id=user_id, category=category, target_name=target_name, target_desc=target_props.get('description',''),
                                 source_doc=source_doc, target_title_emb=target_title_emb, target_desc_emb=target_desc_emb)
                else: # Relationship between two Entities
                    source_title_emb = embed_model.get_text_embedding(source_name)
                    source_desc_emb = embed_model.get_text_embedding(source_props.get('description', ''))
                    
                    session.run("""
                        MATCH (u:User {user_id: $user_id})
                        MERGE (s:Entity {name: $source_name})
                        ON CREATE SET s.description = $source_desc, s.source = $source_doc, s.category = $category,
                                      s.title_embedding = $source_title_emb, s.description_embedding = $source_desc_emb
                        MERGE (t:Entity {name: $target_name})
                        ON CREATE SET t.description = $target_desc, t.source = $source_doc, t.category = $category,
                                      t.title_embedding = $target_title_emb, t.description_embedding = $target_desc_emb
                        MERGE (s)-[r:`%s`]->(t)
                        MERGE (u)-[:OWNS]->(s)
                        MERGE (u)-[:OWNS]->(t)
                    """ % rel_type, user_id=user_id, category=category, source_name=source_name, source_desc=source_props.get('description',''),
                                 target_name=target_name, target_desc=target_props.get('description',''), source_doc=source_doc,
                                 source_title_emb=source_title_emb, source_desc_emb=source_desc_emb,
                                 target_title_emb=target_title_emb, target_desc_emb=target_desc_emb)

# --- Core RAG Logic (Refactored for Performance) ---
async def query_user_profile(user_id: str, query: str) -> str:
    driver = db.get_neo4j_driver()
    
    # 1. Classify Query
    prompt = query_classification_user_prompt_template.format(query=query)
    classification_raw = llm.run_agent_with_prompt(agents["classification"], prompt)
    classification = json.loads(clean_llm_output(classification_raw))
    category = classification.get("category", "Miscellaneous")
    
    # 2. Perform Vector Similarity Search
    graph_data = await _perform_vector_similarity_search(user_id, category, query, driver)
    if not graph_data.get("nodes"): # Fallback to Miscellaneous
        graph_data = await _perform_vector_similarity_search(user_id, "Miscellaneous", query, driver)

    if not graph_data.get("nodes"):
        return "No relevant information found in your memory."

    # 3. Convert Graph Data to Text
    prompt = text_conversion_user_prompt_template.format(graph_data=json.dumps(graph_data))
    context_raw = llm.run_agent_with_prompt(agents["conversion"], prompt)
    context = clean_llm_output(context_raw)
    
    return context if context else "Could not generate a summary from the retrieved information."

async def _perform_vector_similarity_search(user_id: str, category: str, query: str, driver: Driver) -> Dict:
    query_embedding = embed_model.get_text_embedding(query)
    
    with driver.session() as session:
        # This query uses the vector index for fast similarity search
        result = session.run("""
            MATCH (u:User {user_id: $user_id})-[:OWNS]->(e:Entity)
            WHERE e.category = $category OR $category = 'Miscellaneous'
            CALL db.index.vector.queryNodes('entity_title_embeddings', 5, $embedding) YIELD node, score
            WHERE node = e
            WITH node AS similar_node, score
            OPTIONAL MATCH (similar_node)-[r]-(related)
            RETURN similar_node, r, related
        """, user_id=user_id, category=category, embedding=query_embedding)
        
        nodes = {}
        triplets = []
        for record in result:
            source_node = record["similar_node"]
            rel = record["r"]
            target_node = record["related"]
            
            if source_node.id not in nodes:
                nodes[source_node.id] = {"name": source_node["name"], "properties": dict(source_node)}
            
            if rel:
                if target_node and target_node.id not in nodes:
                     nodes[target_node.id] = {"name": target_node["name"], "properties": dict(target_node)}
                
                triplets.append({
                    "source": source_node["name"],
                    "relationship": type(rel).__name__,
                    "target": target_node["name"] if target_node else "Unknown"
                })

    return {"nodes": list(nodes.values()), "triplets": triplets}

# --- Core CRUD Logic (Refactored) ---
async def crud_graph_operations(user_id: str, information: str):
    """Orchestrates CRUD operations on the user's knowledge graph."""
    driver = db.get_neo4j_driver()

    # 1. Classify information to get a category context
    prompt = query_classification_user_prompt_template.format(query=information)
    classification_raw = llm.run_agent_with_prompt(agents["classification"], prompt)
    classification = json.loads(clean_llm_output(classification_raw))
    category = classification.get("category", "Miscellaneous")
    
    # 2. Extract new information as triplets
    prompt = information_extraction_user_prompt_template.format(category=category, text=information)
    extracted_data_raw = llm.run_agent_with_prompt(agents["extraction"], prompt)
    extracted_data = json.loads(clean_llm_output(extracted_data_raw))
    if not extracted_data or not isinstance(extracted_data.get("relationships"), list):
        return "Could not extract structured information to update memory."

    # 3. Find related parts of the existing graph using vector search
    related_graph_data = await _perform_vector_similarity_search(user_id, category, information, driver)

    # 4. Let an agent decide on the CRUD operations
    # NOTE: The old analysis step is merged into the decision step for efficiency
    prompt = graph_decision_user_prompt_template.format(analysis=json.dumps({
        "existing_graph": related_graph_data.get("triplets", []),
        "new_information": extracted_data.get("relationships", [])
    }))
    decisions_raw = llm.run_agent_with_prompt(agents["decision"], prompt)
    decisions = json.loads(clean_llm_output(decisions_raw))
    
    if not decisions:
        return "Could not determine the necessary changes for the memory."

    # 5. Execute the decisions
    await _execute_crud_decisions(user_id, category, decisions, driver)
    return "Memory updated successfully."
    
async def _execute_crud_decisions(user_id: str, category: str, decisions: List[Dict], driver: Driver):
    """Executes a list of CRUD decisions on the graph for a specific user."""
    with driver.session() as session:
        for decision in decisions:
            action = decision.get("action")
            node_name = decision.get("node")
            properties = decision.get("properties", {})
            
            if action == "create":
                emb_title = embed_model.get_text_embedding(node_name)
                emb_desc = embed_model.get_text_embedding(properties.get("description", ""))
                session.run("""
                    MATCH (u:User {user_id: $user_id})
                    MERGE (e:Entity {name: $name})
                    ON CREATE SET e += $props, e.category = $category, e.title_embedding = $emb_title, e.description_embedding = $emb_desc
                    MERGE (u)-[:OWNS]->(e)
                """, user_id=user_id, name=node_name, props=properties, category=category, emb_title=emb_title, emb_desc=emb_desc)
            
            elif action == "update":
                 session.run("""
                    MATCH (u:User {user_id: $user_id})-[:OWNS]->(e:Entity {name: $name})
                    SET e += $props
                """, user_id=user_id, name=node_name, props=properties)

            elif action == "delete":
                session.run("""
                    MATCH (u:User {user_id: $user_id})-[:OWNS]->(e:Entity {name: $name})
                    DETACH DELETE e
                """, user_id=user_id, name=node_name)

            # Handle relationships
            for rel in decision.get("relationships", []):
                rel_action = rel.get("action")
                rel_type = rel.get("type", "RELATED_TO").upper().replace(" ", "_")
                target_name = rel.get("target")

                if rel_action == "create":
                    session.run("""
                        MATCH (u:User {user_id: $user_id})-[:OWNS]->(s:Entity {name: $source})
                        MATCH (u)-[:OWNS]->(t:Entity {name: $target})
                        MERGE (s)-[:`%s`]->(t)
                    """ % rel_type, user_id=user_id, source=node_name, target=target_name)
                elif rel_action == "delete":
                    session.run("""
                        MATCH (:User {user_id: $user_id})-[:OWNS]->(s:Entity {name: $source})-[r:`%s`]-(t:Entity {name: $target})
                        DELETE r
                    """ % rel_type, user_id=user_id, source=node_name, target=target_name)

# --- Other Utility Functions ---
async def delete_source_subgraph(user_id: str, file_name: str):
    driver = db.get_neo4j_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (u:User {user_id: $user_id})-[:OWNS]->(n)
            WHERE n.source = $file_name
            DETACH DELETE n
            RETURN count(n) as deleted_count
        """, user_id=user_id, file_name=file_name)
        count = result.single()["deleted_count"]
    return f"Deleted {count} nodes related to source: {file_name}"