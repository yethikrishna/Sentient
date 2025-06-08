import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from qwen_agent.agents import Assistant

from ..llm import get_qwen_assistant
from ..config import MEMORY_MCP_SERVER_URL

logger = logging.getLogger(__name__)

class Neo4jMemoryManager:
    """Handles direct interactions with the Neo4j graph for memory visualization."""
    def __init__(self, driver):
        self._driver = driver

    def get_graph_data_for_user(self, user_id: str) -> Dict[str, List[Dict]]:
        # This new query is more robust. It finds all paths starting from the user,
        # up to 4 hops away, and returns the paths themselves. This captures all
        # nodes and relationships in the user's immediate subgraph.
        query = """
        MATCH path = (u:User {user_id: $user_id})-[*1..4]-(n)
        RETURN path
        """
        nodes = []
        edges = []
        node_ids = set()
        edge_ids = set()

        def add_node(node_record):
            if node_record and node_record.id not in node_ids:
                props: Dict[str, Any] = dict(node_record)

                # Sanitize properties for JSON serialization
                for key, value in props.items():
                    if hasattr(value, 'isoformat'): # Checks for datetime, date, etc.
                        props[key] = value.isoformat()

                node_id = str(node_record.id)
                node_ids.add(node_record.id)
                nodes.append({
                    "id": node_id,
                    "label": next(iter(node_record.labels), "Node"),
                    "title": props.get('name') or props.get('text', 'User'),
                    **props
                })
        
        def add_edge(rel_record):
            # Add a check for edge_ids to prevent duplicates
            if rel_record and rel_record.id not in edge_ids:
                edge_ids.add(rel_record.id)
                edges.append({
                    "id": str(rel_record.id),
                    "from": str(rel_record.start_node.id),
                    "to": str(rel_record.end_node.id),
                    "label": rel_record.type
                })

        with self._driver.session() as session:
            results = session.run(query, user_id=user_id)
            # We now iterate through each path found by the query
            for record in results:
                path = record['path']
                for node in path.nodes:
                    add_node(node)
                for rel in path.relationships:
                    add_edge(rel)
        
        return {"nodes": nodes, "edges": edges}

class MongoMemoryManager:
    """Handles direct interactions with MongoDB for short-term memory visualization."""
    def __init__(self, client, db_name):
        self.db = client[db_name]
        self.collection = self.db["short_term_memories"]

    def get_memories(self, user_id: str, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        query = {"user_id": user_id}
        if category:
            query["category"] = category
        
        memories = self.collection.find(query).sort("created_at", -1).limit(limit)
        
        results = []
        for mem in memories:
            mem["_id"] = str(mem["_id"])
            if "content_embedding" in mem:
                del mem["content_embedding"]
            for key, value in mem.items():
                if isinstance(value, datetime):
                    mem[key] = value.isoformat()
            results.append(mem)
        return results

# --- Memory Agent ---
async def run_memory_agent_instruction(user_id: str, instruction: str) -> Dict[str, Any]:
    """
    Uses a Qwen Agent with memory tools to process a user's instruction.
    """
    logger.info(f"Running memory agent for user {user_id} with instruction: '{instruction}'")

    tools = [{
        "mcpServers": {
            "memory_server": {
                "url": MEMORY_MCP_SERVER_URL,
                "headers": {"X-User-ID": user_id},
            }
        }
    }]
    
    system_prompt = (
        "You are a memory management assistant. Your task is to accurately interpret the user's "
        "instruction and use the available tools to save, search, or update their memories. "
        "Be precise. Use the tools provided to perform operations on the user's memory. "
        "You can call the Memory MCP server to perform operations like saving, searching, or updating memories. "
        "Analyze the instruction carefully to extract all necessary parameters for the tool calls."
    )
    
    agent = get_qwen_assistant(system_message=system_prompt, function_list=tools)
    
    messages = [{'role': 'user', 'content': instruction}]
    
    final_response = ""
    try:
        # We only care about the tool calls and final result, not streaming.
        for response in agent.run(messages=messages):
            final_response = response # Keep overwriting until the last one
        
        # The final response from the agent contains the history, including tool calls and results.
        # We can return this for debugging or extract the key message.
        last_message = final_response[-1] if isinstance(final_response, list) and final_response else {}
        
        if last_message.get('role') == 'assistant' and 'tool_calls' in last_message:
             return {"status": "success", "message": "Memory operation initiated.", "details": final_response}
        elif last_message.get('role') == 'assistant':
             return {"status": "success", "message": last_message.get('content', "Operation complete."), "details": final_response}
        else:
             return {"status": "success", "message": "Processing complete.", "details": final_response}

    except Exception as e:
        logger.error(f"Error in memory agent for user {user_id}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def trigger_mcp_tool(user_id: str, tool_name: str, params: Dict = {}):
    """Directly triggers a specific tool on the Memory MCP server."""
    payload = {
        "tool": tool_name,
        "parameters": params
    }
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": user_id
    }
    async with httpx.AsyncClient() as client:
        try:
            # MCP server endpoint for direct tool call is usually the base URL
            mcp_base_url = MEMORY_MCP_SERVER_URL.replace("/sse", "")
            response = await client.post(mcp_base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            # The direct response is a stream of events, we need to parse the final 'result'
            full_response_text = ""
            for line in response.text.splitlines():
                full_response_text += line
            # This parsing is simplistic, assuming the last JSON object is the result
            # A more robust MCP client would handle SSE events properly.
            # For this use case, we just need to confirm it ran.
            return {"status": "success", "raw_response": full_response_text}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling MCP tool '{tool_name}': {e.response.text}")
            return {"status": "error", "message": e.response.text}
        except Exception as e:
            logger.error(f"Error calling MCP tool '{tool_name}': {e}", exc_info=True)
            return {"status": "error", "message": str(e)}