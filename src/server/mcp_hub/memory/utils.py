import os
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import numpy as np
import google.generativeai as genai
from pgvector.asyncpg import register_vector

from . import db, llm
from .prompts import (
    fact_summarization_user_prompt_template,
    fact_extraction_user_prompt_template,
    cud_decision_user_prompt_template,
    fact_analysis_user_prompt_template,
)

logger = logging.getLogger(__name__)

# --- Module-level state (initialized by lifespan event) ---
embed_model_name: str = None
agents: Dict[str, Any] = {}

# --- Initialization Functions ---
def initialize_embedding_model():
    global embed_model_name
    if embed_model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "models/gemini-embedding-001")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        logger.info(f"Initializing embedding model: {model_name}")
        genai.configure(api_key=api_key)
        embed_model_name = model_name

def initialize_agents():
    global agents
    if not agents:
        logger.info("Initializing all memory agents...")
        agents = {
            "fact_summarization": llm.get_fact_summarization_agent(),
            "fact_extraction": llm.get_fact_extraction_agent(),
            "fact_analysis": llm.get_fact_analysis_agent(),
            "cud_decision": llm.get_cud_decision_agent(),
        }

def parse_duration(duration_str: Optional[str]) -> Optional[datetime]:
    """Parses a human-readable duration string and returns a future UTC datetime."""
    if not duration_str:
        return None
    logger.debug(f"Attempting to parse duration string: '{duration_str}'")
    try:
        match = re.match(r"(\d+)\s+(hour|day|week|month)s?", duration_str, re.IGNORECASE)
        if not match:
            logger.warning(f"Duration string '{duration_str}' does not match expected format.")
            return None

        value, unit = int(match.group(1)), match.group(2).lower()

        delta_map = {
            "hour": timedelta(hours=value),
            "day": timedelta(days=value),
            "week": timedelta(weeks=value),
            "month": timedelta(days=value * 30), # Approximation
        }
        if delta := delta_map.get(unit):
            result = datetime.now(timezone.utc) + delta
            logger.info(f"Parsed '{duration_str}' to an expiration date of {result.isoformat()}")
            return result
    except Exception as e:
        logger.warning(f"Could not parse duration string '{duration_str}': {e}")

    logger.warning(f"Failed to parse duration string '{duration_str}'.")
    return None

def clean_llm_output(data: Any) -> Any:
    """Recursively cleans strings in LLM output."""
    logger.debug(f"Cleaning LLM output. Input type: {type(data)}")
    if isinstance(data, str):
        cleaned_str = data
        original_str = str(data)
        # If the LLM wrapped the JSON in a markdown block, extract it.
        # This is helpful for pre-processing before a json.loads() call.
        if "```json" in cleaned_str:
            match = re.search(r"```json\s*([\s\S]+?)\s*```", cleaned_str)
            if match:
                cleaned_str = match.group(1)
                logger.debug("Extracted JSON content from markdown block.")

        # Remove any <think> blocks that might be present.
        cleaned_str = re.sub(r'<think>.*?</think>', '', cleaned_str, flags=re.DOTALL)
        cleaned_str = cleaned_str.strip()
        if cleaned_str != original_str:
            logger.debug("LLM string output was cleaned.")
        return cleaned_str
    if isinstance(data, dict):
        return {k: clean_llm_output(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_llm_output(i) for i in data]
    return data

def _get_normalized_embedding(text: str, task_type: str) -> np.ndarray:
    """
    Generates and normalizes an embedding for the given text using Gemini.
    We use a truncated embedding dimension (768), which requires manual normalization for
    optimal performance as per the Gemini API documentation.
    See: https://ai.google.dev/gemini-api/docs/embeddings#ensuring_quality_for_smaller_dimensions
    """
    # Task types: "RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT", "SEMANTIC_SIMILARITY", "CLASSIFICATION", "CLUSTERING"
    result = genai.embed_content(
        model=embed_model_name,
        content=text,
        task_type=task_type,
        output_dimensionality=768
    )
    embedding_np = np.array(result['embedding'], dtype=np.float32)

    norm = np.linalg.norm(embedding_np)
    if norm == 0:
        return embedding_np # Return zero vector if norm is zero

    normalized_embedding = embedding_np / norm
    return normalized_embedding

async def search_memory(user_id: str, query: str) -> str:
    """Searches memory by performing a direct semantic search and summarizing results."""
    logger.info(f"Executing search_memory for user_id='{user_id}' with query: '{query}'")
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)
        
        logger.info("Step 1/2: Performing direct semantic search in database.")
        query_embedding = _get_normalized_embedding(query, task_type="RETRIEVAL_QUERY")
        
        records = await conn.fetch(
            """
            SELECT DISTINCT f.id, f.content, 1 - (f.embedding <=> $2) AS similarity
            FROM facts f
            WHERE f.user_id = $1
            ORDER BY similarity DESC
            LIMIT 5;
            """, user_id, query_embedding
        )
        
        found_facts = {r['id']: r['content'] for r in records}
        logger.info(f"Found {len(found_facts)} relevant facts from search.")
    
    if not found_facts:
        logger.info("No relevant facts found. Returning message to user.")
        return "No relevant information found in your memory."

    logger.info("Step 2/2: Summarizing search results into a coherent paragraph.")
    facts_list = list(found_facts.values())
    prompt = fact_summarization_user_prompt_template.format(facts=json.dumps(facts_list))
    summary_raw = llm.run_agent_with_prompt(agents["fact_summarization"], prompt)
    summary = clean_llm_output(summary_raw)
    
    logger.info("Search complete. Returning summary.")
    return summary if isinstance(summary, str) and summary else "Could not generate a summary from the retrieved information."

async def search_memory_by_source(user_id: str, query: str, source_name: str) -> str:
    """Searches memory by performing a semantic search within a specific source."""
    logger.info(f"Executing search_memory_by_source for user_id='{user_id}', source='{source_name}' with query: '{query}'")
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)

        logger.info(f"Step 1/2: Performing semantic search in database for source '{source_name}'.")
        query_embedding = _get_normalized_embedding(query, task_type="RETRIEVAL_QUERY")

        records = await conn.fetch(
            """
            SELECT DISTINCT f.id, f.content, 1 - (f.embedding <=> $3) AS similarity
            FROM facts f
            WHERE f.user_id = $1 AND f.source = $2
            ORDER BY similarity DESC
            LIMIT 5;
            """, user_id, source_name, query_embedding
        )

        found_facts = {r['id']: r['content'] for r in records}
        logger.info(f"Found {len(found_facts)} relevant facts from search.")

    if not found_facts:
        logger.info(f"No relevant facts found for source '{source_name}'. Returning message to user.")
        return f"No relevant information found for your query within the source '{source_name}'."

    logger.info("Step 2/2: Summarizing search results into a coherent paragraph.")
    facts_list = list(found_facts.values())
    prompt = fact_summarization_user_prompt_template.format(facts=json.dumps(facts_list))
    summary_raw = llm.run_agent_with_prompt(agents["fact_summarization"], prompt)
    summary = clean_llm_output(summary_raw)

    logger.info("Search by source complete. Returning summary.")
    return summary if isinstance(summary, str) and summary else "Could not generate a summary from the retrieved information."

async def _insert_fact_with_analysis(conn, user_id: str, content: str, source: Optional[str], analysis: dict) -> str:
    """Internal function to insert a fact and its related metadata into the database."""
    logger.info("Executing _insert_fact_with_analysis.")
    
    expires_at = None
    if analysis.get("memory_type") == "short-term":
        expires_at = parse_duration(analysis.get("duration"))

    async with conn.transaction():
        embedding = _get_normalized_embedding(content, task_type="RETRIEVAL_DOCUMENT")
        
        fact_id = await conn.fetchval(
            """
            INSERT INTO facts (user_id, content, embedding, source, expires_at)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
            """,
            user_id, content, embedding, source, expires_at
        )
        logger.info(f"Inserted new fact with ID: {fact_id}.")

        # Link topics
        topic_names = analysis.get("topics", ["Miscellaneous"])
        for topic_name in topic_names:
            topic_id = await conn.fetchval("SELECT id FROM topics WHERE name = $1", topic_name)
            if topic_id:
                await conn.execute("INSERT INTO fact_topics (fact_id, topic_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", fact_id, topic_id)

    message = f"Fact added with ID {fact_id}."
    if expires_at:
        message += f" This is a short-term memory and will be forgotten around {expires_at.strftime('%Y-%m-%d %H:%M %Z')}."
    return message

async def cud_memory(user_id: str, information: str, source: Optional[str] = None) -> str:
    """Adds, updates, or deletes a fact based on user input using a streamlined process."""
    logger.info(f"Executing cud_memory for user_id='{user_id}' with source='{source}'.")
    logger.debug(f"CUD information: \"{information}\"")
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)
        
        logger.info("Step 1/3: Finding potentially related facts via semantic search.")
        query_embedding = _get_normalized_embedding(information, task_type="RETRIEVAL_QUERY")
        similar_records = await conn.fetch(
            """
            SELECT DISTINCT f.id, f.content, 1 - (f.embedding <=> $2) AS similarity
            FROM facts f
            WHERE f.user_id = $1
            ORDER BY similarity DESC
            LIMIT 3;
            """, user_id, query_embedding
        )
        logger.info(f"Found {len(similar_records)} potentially related facts.")

        logger.info("Step 2/3: Using LLM to decide on action and perform analysis.")
        prompt = cud_decision_user_prompt_template.format(
            information=information,
            similar_facts=json.dumps([dict(r) for r in similar_records])
        )
        decision_raw = llm.run_agent_with_prompt(agents["cud_decision"], prompt)
        cleaned_output = clean_llm_output(decision_raw)
        decision = {}
        try:
            decision = json.loads(cleaned_output)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse CUD decision JSON from LLM. Defaulting to ADD. Output: {cleaned_output}")
            decision = {"action": "ADD", "content": information} # Fallback

        logger.info(f"Step 3/3: Executing action '{decision.get('action')}'.")
        action = decision.get("action")
        
        if action == "ADD" and decision.get("content") and decision.get("analysis"):
            logger.info("Action is ADD. Inserting new fact with full analysis.")
            return await _insert_fact_with_analysis(conn, user_id, decision["content"], source, decision["analysis"])

        elif action == "UPDATE" and decision.get("fact_id") and decision.get("content") and decision.get("analysis"):
            fact_id = decision["fact_id"]
            logger.info(f"Action is UPDATE for fact_id {fact_id}. Replacing fact.")
            async with conn.transaction():
                await conn.execute("DELETE FROM facts WHERE id = $1 AND user_id = $2", fact_id, user_id)
                logger.info(f"Original fact {fact_id} deleted.")
            return await _insert_fact_with_analysis(conn, user_id, decision["content"], source, decision["analysis"])

        elif action == "DELETE" and decision.get("fact_id"):
            fact_id = decision["fact_id"]
            logger.info(f"Action is DELETE for fact_id {fact_id}.")
            result = await conn.execute("DELETE FROM facts WHERE id = $1 AND user_id = $2", fact_id, user_id)
            if result.endswith("1"):
                logger.info(f"Successfully deleted fact {fact_id}.")
                return f"Fact {fact_id} deleted."
            else:
                logger.warning(f"Attempted to delete fact {fact_id}, but it was not found or not owned by the user.")
                return f"Fact {fact_id} not found or not owned by user."

        else:
            logger.warning(f"LLM decision was ambiguous or invalid, falling back to simple ADD. Decision: {decision}")
            # Fallback to analyzing and adding the original information
            prompt = fact_analysis_user_prompt_template.format(text=information)
            analysis_raw = llm.run_agent_with_prompt(agents["fact_analysis"], prompt)
            analysis_cleaned = clean_llm_output(analysis_raw)
            try:
                analysis = json.loads(analysis_cleaned)
                return await _insert_fact_with_analysis(conn, user_id, information, source, analysis)
            except json.JSONDecodeError:
                logger.error(f"Fallback ADD failed due to analysis JSON error. Output: {analysis_cleaned}")
                return "Failed to process memory due to an internal analysis error."

async def build_initial_memory(user_id: str, documents: List[Dict[str, str]]) -> str:
    """Builds memory from documents, clearing existing memory first."""
    logger.info(f"Executing build_initial_memory for user_id='{user_id}' with {len(documents)} documents.")
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        logger.info(f"Clearing all existing facts for user_id='{user_id}'.")
        # Use a transaction to ensure atomicity
        async with conn.transaction():
            # Cascading delete on 'facts' will also clear 'fact_topics'
            await conn.execute("DELETE FROM facts WHERE user_id = $1", user_id)
    
    total_facts_added = 0
    for doc in documents:
        text, source = doc.get("text", ""), doc.get("source", "unknown")
        if not text: continue
        
        logger.info(f"Extracting facts from document with source: '{source}'.")
        prompt = fact_extraction_user_prompt_template.format(username=user_id, paragraph=text)
        facts_raw = llm.run_agent_with_prompt(agents["fact_extraction"], prompt)
        cleaned_output = clean_llm_output(facts_raw)
        facts = []
        try:
            parsed_facts = json.loads(cleaned_output)
            if isinstance(parsed_facts, list):
                facts = parsed_facts
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse fact extraction JSON from LLM. Skipping document. Output: {cleaned_output}")

        logger.info(f"Extracted {len(facts)} facts from source '{source}'.")
        if isinstance(facts, list):
            # Analyze all facts from the document in a batch-like manner
            for fact_content in facts:
                if not fact_content: continue
                
                logger.debug(f"Analyzing and adding extracted fact: '{fact_content}'")
                # Use the streamlined CUD path with a direct ADD intent
                await cud_memory(user_id, fact_content, source=source)
                total_facts_added += 1
    
    logger.info(f"Finished building initial memory. Added {total_facts_added} total facts.")
    return f"Memory built successfully. Added {total_facts_added} facts."

async def delete_memory_by_source(user_id: str, source_name: str) -> str:
    """Deletes all facts associated with a specific source."""
    logger.info(f"Executing delete_memory_by_source for user_id='{user_id}' and source='{source_name}'.")
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM facts WHERE user_id = $1 AND source = $2", user_id, source_name)
    
    try:
        deleted_count = int(result.split(" ")[1])
    except (IndexError, ValueError):
        deleted_count = 0
    logger.info(f"Deleted {deleted_count} facts from source: {source_name}")
    return f"Deleted {deleted_count} facts from source: {source_name}"

async def purge_expired_facts():
    """Deletes facts from the database that have passed their expiration time."""
    logger.info("Purge job: Checking for expired short-term memories.")
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        # The index on expires_at makes this query very efficient.
        result = await conn.execute("DELETE FROM facts WHERE expires_at IS NOT NULL AND expires_at < NOW()")
        try:
            deleted_count = int(result.split(" ")[1])
            logger.info(f"Purge job: Purged {deleted_count} expired short-term memories.")
        except (IndexError, ValueError):
            logger.info("Purge job: No expired memories found to purge.")