import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any
from pgvector.asyncpg import register_vector

from .db import get_db_pool

logger = logging.getLogger(__name__)

# A threshold to determine if two memories are connected in the graph.
# This can be tuned. A higher value means fewer, but more relevant, connections.
SIMILARITY_THRESHOLD = 0.85

def truncate_text(text: str, max_length: int = 25) -> str:
    """Truncates text to a max length and adds ellipsis if needed."""
    if len(text) > max_length:
        return text[:max_length].strip() + "..."
    return text

async def create_memory_graph(user_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches user's memories, calculates semantic similarity, and returns a graph structure.
    """
    logger.info(f"Generating memory graph for user_id: {user_id}")
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        await register_vector(connection)
        # Fetch all facts that have an embedding for the user, along with their topics
        query = """
            SELECT
                f.id,
                f.content,
                f.source,
                f.created_at,
                f.embedding,
                COALESCE(ARRAY_AGG(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') as topics
            FROM facts f
            LEFT JOIN fact_topics ft ON f.id = ft.fact_id
            LEFT JOIN topics t ON ft.topic_id = t.id
            WHERE f.user_id = $1 AND f.embedding IS NOT NULL
            GROUP BY f.id
            ORDER BY f.created_at DESC;
        """
        records = await connection.fetch(query, user_id)

    if not records:
        logger.info(f"No memories with embeddings found for user {user_id}.")
        return {"nodes": [], "edges": []}

    # Prepare data for similarity calculation
    fact_map = {record['id']: record for record in records}
    fact_ids = list(fact_map.keys())
    embeddings = np.array([record['embedding'] for record in records])

    # Create nodes for the graph, including all necessary data for the detail panel
    nodes = [
        {
            "id": record["id"],
            "label": truncate_text(record["content"]),
            "title": record["content"], # Full content for vis.js tooltip
            "content": record["content"], # Pass full content for our detail panel
            "created_at": record["created_at"].isoformat(),
            "source": record["source"],
            "topics": record.get("topics", [])
        } for record in fact_map.values()
    ]

    # Calculate cosine similarity matrix if there's more than one embedding
    edges = []
    if len(embeddings) > 1:
        logger.info(f"Calculating similarity matrix for {len(embeddings)} memories.")
        similarity_matrix = cosine_similarity(embeddings)

        # Create edges based on the similarity threshold
        for i in range(len(similarity_matrix)):
            for j in range(i + 1, len(similarity_matrix)):
                similarity = similarity_matrix[i][j]
                if similarity >= SIMILARITY_THRESHOLD:
                    edges.append({
                        "from": fact_ids[i],
                        "to": fact_ids[j],
                        "value": float(similarity), # Convert numpy.float32 to standard float
                        "title": f"Similarity: {similarity:.2%}" # Tooltip for the edge
                    })

    logger.info(f"Generated graph with {len(nodes)} nodes and {len(edges)} edges.")
    return {"nodes": nodes, "edges": edges}
