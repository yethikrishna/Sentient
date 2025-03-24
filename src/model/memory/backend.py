from neo4j import GraphDatabase
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os
from dotenv import load_dotenv

from .runnables import *
from .functions import *
from .dual_memory import MemoryManager
from model.app.base import *

load_dotenv("model/.env")

class MemoryBackend:
    def __init__(self):
        """Initialize the memory backend with both long-term and short-term agents."""
        # Long-term memory (Neo4j)
        self.embed_model = HuggingFaceEmbedding(model_name=os.environ["EMBEDDING_MODEL_REPO_ID"])
        self.graph_driver = GraphDatabase.driver(
            uri=os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
        )
        self.graph_decision_runnable = get_graph_decision_runnable()
        self.info_extraction_runnable = get_information_extraction_runnable()
        self.graph_analysis_runnable = get_graph_analysis_runnable()
        self.query_class_runnable = get_query_classification_runnable()
        self.fact_extraction_runnable = get_fact_extraction_runnable()
        self.text_desc_runnable = get_text_description_runnable()
        self.text_conv_runnable = get_text_conversion_runnable()

        # Short-term memory (SQLite)
        self.memory_manager = MemoryManager(db_path="memory.db", model_name=os.environ["BASE_MODEL_REPO_ID"])

        # Memory type classifiers
        self.memory_type_runnable = self._initialize_memory_type_classifier()
        self.query_memory_type_runnable = self._initialize_query_memory_type_classifier()

    def _initialize_memory_type_classifier(self):
        """Initialize the classifier for short-term vs long-term memories."""
        return OllamaRunnable(
            model_url="http://localhost:11434/api/chat/",
            model_name="llama3.2:3b",
            system_prompt_template="""
            You are an AI designed to classify user-provided facts into 'Short Term' or 'Long Term' memory types.
            - 'Short Term' memories are transient (e.g., tasks, recent events) and typically expire within days or weeks.
            - 'Long Term' memories are persistent (e.g., preferences, personal traits) and stored indefinitely.
            Provide your classification as a string: "Short Term" or "Long Term".
            """,
            user_prompt_template="Classify this fact: {fact}",
            input_variables=["fact"],
            response_type="chat"
        )

    def _initialize_query_memory_type_classifier(self):
        """Initialize the classifier for short-term vs long-term queries."""
        return OllamaRunnable(
            model_url="http://localhost:11434/api/chat/",
            model_name="llama3.2:3b",
            system_prompt_template="""
            You are an AI designed to classify user queries into 'Short Term' or 'Long Term' memory types based on the kind of information being requested.
            - 'Short Term' queries are about recent events, tasks, or transient information (e.g., days or weeks). Examples: "What did I have for lunch yesterday?" or "Do I have meetings tomorrow?"
            - 'Long Term' queries are about persistent information, preferences, or knowledge (e.g., habits, traits). Examples: "What's my favorite color?" or "What do I usually order at restaurants?"
            Provide your classification as a string: "Short Term" or "Long Term".
            """,
            user_prompt_template="Classify this query: {query}",
            input_variables=["query"],
            response_type="chat"
        )

    def extract_memory_fact(self, query: str) -> str:
        """Extract the factual statement from a memory-related query."""
        try:
            fact_extraction_runnable = OllamaRunnable(
                model_url="http://localhost:11434/api/chat/",
                model_name="llama3.2:3b",
                system_prompt_template="""
                You are an AI assistant tasked with extracting the factual statement from a user's request to remember something. 
                Extract the complete fact exactly as stated, without adding assumptions, commentary, or partial extractions. 
                Return only the factual statement.

                Examples:
                - Input: "can you remember that I have a meeting tomorrow"
                Output: "I have a meeting tomorrow"
                - Input: "please note that my favorite color is blue"
                Output: "my favorite color is blue"

                Extract the factual statement from this query:
                """,
                user_prompt_template="{query}",
                input_variables=["query"],
                response_type="chat"
            )
            response = fact_extraction_runnable.invoke({"query": query})
            print(f"Raw fact extraction response: '{response}'")  # Debug log
            return response.strip()
        except Exception as e:
            print(f"Error extracting memory fact: {e}")
            return query  # Fallback

    def classify_memory(self, fact: str) -> str:
        """Classify a fact as short-term or long-term."""
        try:
            response = self.memory_type_runnable.invoke({"fact": fact})
            return response.strip()
        except Exception as e:
            print(f"Error classifying memory: {e}")
            return "Long Term"  # Default to long-term if classification fails

    def classify_query_memory_type(self, query: str) -> str:
        """Classify a query as short-term or long-term."""
        try:
            response = self.query_memory_type_runnable.invoke({"query": query})
            return response.strip()
        except Exception as e:
            print(f"Error classifying query memory type: {e}")
            return "Long Term"  # Default to long-term if classification fails

    def store_memory(self, user_id: str, query: str):
        """Store a fact in the appropriate memory system after extracting the fact."""
        fact = self.extract_memory_fact(query)
        memory_type = self.classify_memory(fact)
        print(f"Extracted fact: '{fact}' | Classified as: {memory_type}")

        if memory_type == "Short Term":
            expiry_info = self.memory_manager.expiry_date_decision(fact)
            retention_days = expiry_info.get("retention_days", 7)
            memory_info = self.memory_manager.extract_and_invoke_memory(fact)
            category = memory_info.get("memories", [{}])[0].get("category", "TASKS")
            self.memory_manager.store_memory(user_id, fact, {"retention_days": retention_days}, category)
        else:
            crud_graph_operations(
                fact, self.graph_driver, self.embed_model, self.query_class_runnable,
                self.info_extraction_runnable, self.graph_analysis_runnable,
                self.graph_decision_runnable, self.text_desc_runnable
            )

    def retrieve_memory(self, user_id: str, query: str) -> str:
        """Retrieve relevant memories from the appropriate store based on query classification."""
        memory_type = self.classify_query_memory_type(query)
        print(f"Query classified as: {memory_type}")

        if memory_type == "Short Term":
            context = self.memory_manager.process_user_query(user_id, query)
            if context and context != "I'm having trouble processing your question. Please try again.":
                print(f"Retrieved short-term context: {context}")
                return context
            else:
                print("No relevant short-term memories found.")
                return "I don't have any relevant short-term memories for that query."
        else:
            context = query_user_profile(
                query, self.graph_driver, self.embed_model,
                self.text_conv_runnable, self.query_class_runnable
            )
            print(f"Retrieved long-term context: {context}")
            return context

    def update_memory(self, user_id: str, query: str):
        """Update existing memories based on new facts after extracting the fact."""
        fact = self.extract_memory_fact(query)
        memory_type = self.classify_memory(fact)
        print(f"Extracted fact: '{fact}' | Classified as: {memory_type}")

        if memory_type == "Short Term":
            self.memory_manager.update_memory(user_id, fact)
        else:
            crud_graph_operations(
                fact, self.graph_driver, self.embed_model, self.query_class_runnable,
                self.info_extraction_runnable, self.graph_analysis_runnable,
                self.graph_decision_runnable, self.text_desc_runnable
            )

    def cleanup(self):
        """Clean up expired short-term memories."""
        self.memory_manager.cleanup_expired_memories()