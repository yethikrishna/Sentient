import os
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import numpy as np
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pgvector.asyncpg import register_vector

from . import db, llm
from .prompts import (
    topic_classification_user_prompt_template,
    subtopic_generation_user_prompt_template,
    fact_summarization_user_prompt_template,
    fact_extraction_user_prompt_template,
    edit_decision_user_prompt_template,
    memory_type_decision_user_prompt_template,
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
        embed_model = HuggingFaceEmbedding(model_name=model_repo_id, embed_batch_size=16)

def initialize_agents():
    global agents
    if not agents:
        logger.info("Initializing all memory agents...")
        agents = {
            "topic_classification": llm.get_topic_classification_agent(),
            "subtopic_generation": llm.get_subtopic_generation_agent(),
            "fact_summarization": llm.get_fact_summarization_agent(),
            "fact_extraction": llm.get_fact_extraction_agent(),
            "edit_decision": llm.get_edit_decision_agent(),
            "memory_type": llm.get_memory_type_agent(),
        }

def parse_duration(duration_str: Optional[str]) -> Optional[datetime]:
    """Parses a human-readable duration string and returns a future UTC datetime."""
    if not duration_str:
        return None

    try:
        match = re.match(r"(\d+)\s+(hour|day|week|month)s?", duration_str, re.IGNORECASE)
        if not match:
            return None

        value, unit = int(match.group(1)), match.group(2).lower()

        delta_map = {
            "hour": timedelta(hours=value),
            "day": timedelta(days=value),
            "week": timedelta(weeks=value),
            "month": timedelta(days=value * 30), # Approximation
        }
        if delta := delta_map.get(unit):
            return datetime.now(timezone.utc) + delta
    except Exception as e:
        logger.warning(f"Could not parse duration string '{duration_str}': {e}")

    return None

def clean_llm_output(data: Any) -> Any:
    """Recursively cleans strings in LLM output."""
    if isinstance(data, str):
        cleaned_str = data
        # If the LLM wrapped the JSON in a markdown block, extract it.
        # This is helpful for pre-processing before a json.loads() call.
        if "```json" in cleaned_str:
            match = re.search(r"```json\s*([\s\S]+?)\s*```", cleaned_str)
            if match:
                cleaned_str = match.group(1)

        # Remove any <think> blocks that might be present.
        cleaned_str = re.sub(r'<think>.*?</think>', '', cleaned_str, flags=re.DOTALL)
        return cleaned_str.strip()
    if isinstance(data, dict):
        return {k: clean_llm_output(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_llm_output(i) for i in data]
    return data

# --- Core Memory Operations ---
async def add_fact(user_id: str, content: str, source: Optional[str] = None) -> str:
    """Adds a single fact to the user's memory, determining if it's long or short-term."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)

        # 1. Determine memory type and expiration
        prompt = memory_type_decision_user_prompt_template.format(fact_content=content)
        raw_output = llm.run_agent_with_prompt(agents["memory_type"], prompt)
        cleaned_output = clean_llm_output(raw_output)
        type_decision = {}
        try:
            type_decision = json.loads(cleaned_output)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse memory type decision from LLM output: {cleaned_output}")

        expires_at = None
        if type_decision.get("memory_type") == "short-term":
            expires_at = parse_duration(type_decision.get("duration"))

        async with conn.transaction():
            # 2. Classify into topics
            prompt = topic_classification_user_prompt_template.format(text=content)
            raw_output = llm.run_agent_with_prompt(agents["topic_classification"], prompt)
            cleaned_output = clean_llm_output(raw_output)
            topic_names = ["Miscellaneous"]
            try:
                classification = json.loads(cleaned_output)
                if isinstance(classification, dict):
                    topic_names = classification.get("topics", ["Miscellaneous"])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse topic classification from LLM output: {cleaned_output}")

            # 3. Generate embedding
            embedding = np.array(embed_model.get_text_embedding(content))

            # 4. Insert fact with expires_at timestamp
            fact_id = await conn.fetchval(
                """
                INSERT INTO facts (user_id, content, embedding, source, expires_at)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
                """,
                user_id, content, embedding, source, expires_at
            )

            # 5. Handle subtopics and linking
            for topic_name in topic_names:
                topic_id = await conn.fetchval("SELECT id FROM topics WHERE name = $1", topic_name)
                if not topic_id: continue

                existing_subtopics = await conn.fetch("SELECT name FROM subtopics WHERE topic_id = $1", topic_id)
                existing_subtopic_names = [r['name'] for r in existing_subtopics]

                subtopic_prompt = subtopic_generation_user_prompt_template.format(
                    topic=topic_name,
                    fact_content=content,
                    existing_subtopics=json.dumps(existing_subtopic_names)
                )
                subtopic_raw = llm.run_agent_with_prompt(agents["subtopic_generation"], subtopic_prompt)
                cleaned_output = clean_llm_output(subtopic_raw)
                subtopic_names = []
                try:
                    subtopic_data = json.loads(cleaned_output)
                    if isinstance(subtopic_data, dict):
                        subtopic_names = subtopic_data.get("subtopics", [])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse subtopic generation from LLM output: {cleaned_output}")

                for subtopic_name in subtopic_names:
                    # Insert subtopic if it doesn't exist for this topic, then get its ID
                    subtopic_id = await conn.fetchval("""
                        WITH s AS (
                            INSERT INTO subtopics (name, topic_id) VALUES ($1, $2)
                            ON CONFLICT (name, topic_id) DO NOTHING
                            RETURNING id
                        )
                        SELECT id FROM s
                        UNION ALL (
                            SELECT id FROM subtopics WHERE name = $1 AND topic_id = $2
                        ) LIMIT 1;
                    """,
                        subtopic_name, topic_id
                    )
                    # Link fact to subtopic
                    await conn.execute(
                        "INSERT INTO fact_subtopics (fact_id, subtopic_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                        fact_id, subtopic_id
                    )

    message = f"Fact added with ID {fact_id}."
    if expires_at:
        message += f" This is a short-term memory and will be forgotten around {expires_at.strftime('%Y-%m-%d %H:%M %Z')}."
    return message

async def search_memory(user_id: str, query: str) -> str:
    """Searches memory by performing a semantic search within inferred topics."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)
        
        # 1. Classify query into Topics to scope the semantic search.
        prompt = topic_classification_user_prompt_template.format(text=query)
        raw_output = llm.run_agent_with_prompt(agents["topic_classification"], prompt)
        cleaned_output = clean_llm_output(raw_output)
        topic_names = ["Miscellaneous"]
        try:
            classification = json.loads(cleaned_output)
            if isinstance(classification, dict):
                topic_names = classification.get("topics", ["Miscellaneous"])
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse topic classification from LLM output: {cleaned_output}")

        # 2. Perform a semantic search scoped to the identified topics.
        query_embedding = np.array(embed_model.get_text_embedding(query))
        
        records = await conn.fetch(
            """
            SELECT DISTINCT f.id, f.content, 1 - (f.embedding <=> $3) AS similarity
            FROM facts f
            JOIN fact_subtopics fs ON f.id = fs.fact_id
            JOIN subtopics s ON fs.subtopic_id = s.id
            JOIN topics t ON s.topic_id = t.id
            WHERE f.user_id = $1 AND t.name = ANY($2)
            ORDER BY similarity DESC
            LIMIT 5;
            """, user_id, topic_names, query_embedding
        )
        
        found_facts = {r['id']: r['content'] for r in records}
    
    if not found_facts:
        return "No relevant information found in your memory."

    # 3. Summarize results into a coherent paragraph.
    facts_list = list(found_facts.values())
    prompt = fact_summarization_user_prompt_template.format(facts=json.dumps(facts_list))
    summary_raw = llm.run_agent_with_prompt(agents["fact_summarization"], prompt)
    summary = clean_llm_output(summary_raw)
    
    return summary if isinstance(summary, str) and summary else "Could not generate a summary from the retrieved information."

async def search_memory_by_source(user_id: str, query: str, source_name: str) -> str:
    """Searches memory by performing a semantic search within a specific source."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)

        # 1. Classify query into Topics to scope the semantic search.
        prompt = topic_classification_user_prompt_template.format(text=query)
        raw_output = llm.run_agent_with_prompt(agents["topic_classification"], prompt)
        cleaned_output = clean_llm_output(raw_output)
        topic_names = ["Miscellaneous"]
        try:
            classification = json.loads(cleaned_output)
            if isinstance(classification, dict):
                topic_names = classification.get("topics", ["Miscellaneous"])
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse topic classification from LLM output: {cleaned_output}")

        # 2. Perform a semantic search scoped to the identified topics and source.
        query_embedding = np.array(embed_model.get_text_embedding(query))

        records = await conn.fetch(
            """
            SELECT DISTINCT f.id, f.content, 1 - (f.embedding <=> $4) AS similarity
            FROM facts f
            JOIN fact_subtopics fs ON f.id = fs.fact_id
            JOIN subtopics s ON fs.subtopic_id = s.id
            JOIN topics t ON s.topic_id = t.id
            WHERE f.user_id = $1 AND f.source = $2 AND t.name = ANY($3)
            ORDER BY similarity DESC
            LIMIT 5;
            """, user_id, source_name, topic_names, query_embedding
        )

        found_facts = {r['id']: r['content'] for r in records}

    if not found_facts:
        return f"No relevant information found for your query within the source '{source_name}'."

    # 3. Summarize results into a coherent paragraph.
    facts_list = list(found_facts.values())
    prompt = fact_summarization_user_prompt_template.format(facts=json.dumps(facts_list))
    summary_raw = llm.run_agent_with_prompt(agents["fact_summarization"], prompt)
    summary = clean_llm_output(summary_raw)

    return summary if isinstance(summary, str) and summary else "Could not generate a summary from the retrieved information."

async def cud_memory(user_id: str, information: str, source: Optional[str] = None) -> str:
    """Adds, updates, or deletes a fact based on user input, scoped by topic. The optional 'source' is used when adding new facts."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        await register_vector(conn)
        
        # 1. Classify the information to determine the topic scope for the search.
        prompt = topic_classification_user_prompt_template.format(text=information)
        raw_output = llm.run_agent_with_prompt(agents["topic_classification"], prompt)
        cleaned_output = clean_llm_output(raw_output)
        topic_names = ["Miscellaneous"]
        try:
            classification = json.loads(cleaned_output)
            if isinstance(classification, dict):
                topic_names = classification.get("topics", ["Miscellaneous"])
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse topic classification from LLM output: {cleaned_output}")

        # 2. Find potentially related facts via semantic search within the identified topic scope.
        query_embedding = np.array(embed_model.get_text_embedding(information))
        similar_records = await conn.fetch(
            """
            SELECT DISTINCT f.id, f.content, 1 - (f.embedding <=> $3) AS similarity
            FROM facts f
            JOIN fact_subtopics fs ON f.id = fs.fact_id
            JOIN subtopics s ON fs.subtopic_id = s.id
            JOIN topics t ON s.topic_id = t.id
            WHERE f.user_id = $1 AND t.name = ANY($2)
            ORDER BY similarity DESC
            LIMIT 3;
            """, user_id, topic_names, query_embedding
        )

        # 3. Use LLM to decide on the action based on the scoped context.
        prompt = edit_decision_user_prompt_template.format(
            information=information,
            similar_facts=json.dumps([dict(r) for r in similar_records])
        )
        decision_raw = llm.run_agent_with_prompt(agents["edit_decision"], prompt)
        cleaned_output = clean_llm_output(decision_raw)
        decision = {}
        try:
            decision = json.loads(cleaned_output)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse edit decision from LLM output: {cleaned_output}")

        if not isinstance(decision, dict) or "action" not in decision:
            return await add_fact(user_id, information, source=source)

        action = decision.get("action")
        fact_id = decision.get("fact_id")
        new_content = decision.get("new_content")

        # 4. Execute the decided action.
        if action == "ADD":
            return await add_fact(user_id, new_content or information, source=source)
        
        elif action == "UPDATE" and fact_id and new_content:
            # The most robust way to handle an update is to delete the old fact
            # and add the new one, ensuring all classifications and links are fresh.
            async with conn.transaction():
                await conn.execute("DELETE FROM facts WHERE id = $1 AND user_id = $2", fact_id, user_id)
            return await add_fact(user_id, new_content, source=source)

        elif action == "DELETE" and fact_id:
            result = await conn.execute("DELETE FROM facts WHERE id = $1 AND user_id = $2", fact_id, user_id)
            return f"Fact {fact_id} deleted." if result.endswith("1") else f"Fact {fact_id} not found or not owned by user."
            
        else:
            return await add_fact(user_id, information, source=source)

async def build_initial_memory(user_id: str, documents: List[Dict[str, str]]) -> str:
    """Builds memory from documents, clearing existing memory first."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        # Clear existing facts for this user
        await conn.execute("DELETE FROM facts WHERE user_id = $1", user_id)
    
    total_facts_added = 0
    for doc in documents:
        text, source = doc.get("text", ""), doc.get("source", "unknown")
        if not text: continue
        
        prompt = fact_extraction_user_prompt_template.format(username=user_id, paragraph=text)
        facts_raw = llm.run_agent_with_prompt(agents["fact_extraction"], prompt)
        cleaned_output = clean_llm_output(facts_raw)
        facts = []
        try:
            parsed_facts = json.loads(cleaned_output)
            if isinstance(parsed_facts, list):
                facts = parsed_facts
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse fact extraction from LLM output: {cleaned_output}")

        if isinstance(facts, list):
            for fact_content in facts:
                if fact_content:
                    await add_fact(user_id, fact_content, source=source)
                    total_facts_added += 1
    
    return f"Memory built successfully. Added {total_facts_added} facts."

async def delete_memory_by_source(user_id: str, source_name: str) -> str:
    """Deletes all facts associated with a specific source."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM facts WHERE user_id = $1 AND source = $2", user_id, source_name)
    
    try:
        deleted_count = int(result.split(" ")[1])
    except (IndexError, ValueError):
        deleted_count = 0
    return f"Deleted {deleted_count} facts from source: {source_name}"
async def purge_expired_facts():
    """Deletes facts from the database that have passed their expiration time."""
    pool = await db.get_db_pool()
    async with pool.acquire() as conn:
        # The index on expires_at makes this query very efficient.
        result = await conn.execute("DELETE FROM facts WHERE expires_at IS NOT NULL AND expires_at < NOW()")
        try:
            deleted_count = int(result.split(" ")[1])
            if deleted_count > 0:
                logger.info(f"Purged {deleted_count} expired short-term memories.")
        except (IndexError, ValueError):
            # No facts deleted
            pass