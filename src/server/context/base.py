from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import time
import json # Added for json.dumps
from server.db.mongo_manager import MongoManager # Import MongoManager

class BaseContextEngine(ABC):
    """Abstract base class for context engines handling various data sources."""

    def __init__(self, user_id, task_queue, memory_backend, websocket_manager, chats_db_lock, notifications_db_lock):
        print(f"BaseContextEngine.__init__ started for user_id: {user_id}")
        self.user_id: str = user_id
        self.task_queue = task_queue # Assuming this is an instance of TaskQueue
        self.memory_backend = memory_backend # Assuming this is an instance of MemoryBackend
        self.websocket_manager = websocket_manager # Assuming this is an instance of WebSocketManager
        # self.chats_db_lock = chats_db_lock # Remnant from file-based system
        # self.notifications_db_lock = notifications_db_lock # Remnant from file-based system
        self.mongo_manager = MongoManager() # Initialize MongoManager for this engine instance
        self.context: dict = {} # Initialize context as empty, to be loaded by load_context
        # asyncio.run(self.load_context()) # ERROR: Cannot call asyncio.run in __init__ of an async app
        print(f"BaseContextEngine.__init__ finished for user_id: {user_id}")

    async def load_context(self):
        """Load the context from MongoDB, or return an empty dict if it doesn't exist."""
        print("BaseContextEngine.load_context started")
        context_data = await self.mongo_manager.get_collection("contexts").find_one({"user_id": self.user_id})
        if context_data:
            print(f"Context loaded for user_id {self.user_id}: {context_data}")
            print("BaseContextEngine.load_context finished (context loaded)")
            return context_data.get("context", {}) # Return the 'context' field, or empty dict if not present
        else:
            print(f"No context found for user_id {self.user_id}, returning empty context.")
            print("BaseContextEngine.load_context finished (empty context)")
            return {}

    async def save_context(self):
        """Save the current context to MongoDB."""
        print("BaseContextEngine.save_context started")
        print(f"Saving context for user_id {self.user_id}: {self.context}")
        await self.mongo_manager.get_collection("contexts").update_one(
            {"user_id": self.user_id},
            {"$set": {"context": self.context}},
            upsert=True
        )
        print("BaseContextEngine.save_context finished")

    async def start(self):
        """Start the engine, running periodically every hour."""
        await self.load_context() # Load context when the engine effectively starts
        # The actual periodic run logic will be in the derived classes or called by a scheduler

    async def run_engine(self):
        """Orchestrate fetching, processing, and generating outputs."""
        await self.load_context() # Ensure context is loaded before running
        print("BaseContextEngine.run_engine started")
        print("BaseContextEngine.run_engine - fetching new data")
        new_data = await self.fetch_new_data()
        if new_data:
            print("BaseContextEngine.run_engine - new data fetched:", new_data)
            print("BaseContextEngine.run_engine - processing new data")
            processed_data = await self.process_new_data(new_data)
            print("BaseContextEngine.run_engine - processed data:", processed_data)
            print("BaseContextEngine.run_engine - generating output")
            output = await self.generate_output(processed_data)
            print("BaseContextEngine.run_engine - generated output:", output)
            print("BaseContextEngine.run_engine - executing outputs")
            await self.execute_outputs(output)
        else:
            print("BaseContextEngine.run_engine - no new data fetched")
        print("BaseContextEngine.run_engine finished")

    @abstractmethod
    async def fetch_new_data(self):
        """Fetch new data from the specific data source."""
        pass

    @abstractmethod
    async def process_new_data(self, new_data):
        """Process the fetched data into a format suitable for the runnable."""
        pass

    @abstractmethod
    async def get_runnable(self):
        """Return the data source-specific runnable for generating outputs."""
        pass

    @abstractmethod
    async def get_category(self):
        """Return the memory category for this data source."""
        pass

    async def generate_output(self, processed_data):
        """Generate tasks, memory operations, and messages using the runnable."""
        print("BaseContextEngine.generate_output started")
        runnable = await self.get_runnable()
        print("BaseContextEngine.generate_output - got runnable:", runnable)
        print("BaseContextEngine.generate_output - retrieving related memories")
        related_memories = await self.memory_backend.retrieve_memory(self.user_id, query=await self.get_category())
        print("BaseContextEngine.generate_output - retrieved related memories:", related_memories)
        print("BaseContextEngine.generate_output - getting ongoing tasks")
        ongoing_tasks = [task for task in await self.task_queue.get_all_tasks() if task["status"] in ["pending", "processing"]]
        print("BaseContextEngine.generate_output - ongoing tasks:", ongoing_tasks)
        print("BaseContextEngine.generate_output - getting chat history")
        chat_history = await self.get_chat_history()
        print("BaseContextEngine.generate_output - chat history:", chat_history)

        related_memories_list = related_memories if related_memories is not None else [] # Handle None case
        memories_str = "\n".join([mem["text"] for mem in related_memories_list])

        ongoing_tasks_list = ongoing_tasks if ongoing_tasks is not None else [] # Handle None case
        tasks_str = "\n".join([task["description"] for task in ongoing_tasks_list])

        chat_history_list = chat_history if chat_history is not None else [] # Handle None case
        chat_str = "\n".join([f"{'User' if msg['isUser'] else 'Assistant'}: {msg['message']}" for msg in chat_history_list])

        print("BaseContextEngine.generate_output - invoking runnable")
        output = runnable.invoke({ # Use ainvoke for async runnable
            "new_information": processed_data,
            "related_memories": memories_str,
            "ongoing_tasks": tasks_str,
            "chat_history": chat_str
        })
        print("BaseContextEngine.generate_output - runnable output:", output)
        print("BaseContextEngine.generate_output finished")
        return output

    async def get_chat_history(self):
        """Retrieve the last 10 messages from the active chat."""
        print("BaseContextEngine.get_chat_history started")
        user_profile = await self.mongo_manager.get_user_profile(self.user_id)
        active_chat_id = None
        if user_profile and "userData" in user_profile and "active_chat_id" in user_profile["userData"]:
            active_chat_id = user_profile["userData"]["active_chat_id"]

        if not active_chat_id:
            print(f"BaseContextEngine.get_chat_history - no active chat ID found for user {self.user_id}, returning empty list")
            return []

        print(f"BaseContextEngine.get_chat_history - active_chat_id: {active_chat_id} for user_id: {self.user_id}")

        # Fetch the specific chat messages using MongoManager's dedicated method
        history = await self.mongo_manager.get_chat_history(self.user_id, active_chat_id)

        # Return last 10 messages
        last_10_messages = history[-10:] if history else []
        print(f"BaseContextEngine.get_chat_history - returning last {len(last_10_messages)} messages.")
        print("BaseContextEngine.get_chat_history finished")
        return last_10_messages

    async def execute_outputs(self, output):
        """Execute the generated tasks, memory operations, and messages."""
        print("BaseContextEngine.execute_outputs started")
        tasks = output.get("tasks", [])
        memory_ops = output.get("memory_operations", [])
        message = output.get("message", [])

        print("BaseContextEngine.execute_outputs - tasks:", tasks)
        print("BaseContextEngine.execute_outputs - memory_operations:", memory_ops)
        print("BaseContextEngine.execute_outputs - message:", message)
        
        # Add tasks to the task queue
        # for task in tasks:
        #     print("BaseContextEngine.execute_outputs - adding task to queue:", task)
        #     await self.task_queue.add_task(
        #         chat_id="context_engine",
        #         description=task["description"],
        #         priority=task["priority"],
        #         username=self.user_id,
        #         personality=None,
        #         use_personal_context=False,
        #         internet="None"
        #     )


        # Add memory operations to the memory queue
        for op in memory_ops:
            print("BaseContextEngine.execute_outputs - processing memory operation:", op)
            await self.memory_backend.memory_queue.add_operation(self.user_id, op["text"])

        # Add messages to the chat database and notifications database
        if message:
            
            new_message = {
                    "id": str(int(time.time() * 1000)),
                    "message": message,
                    "isUser": False,
                    "isVisible": True,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            print("BaseContextEngine.execute_outputs - processing message for user:", self.user_id, "Message:", message)

            # Add message to the user's active chat history
            user_profile = await self.mongo_manager.get_user_profile(self.user_id)
            active_chat_id = "context_engine_default_chat" # Fallback chat_id
            if user_profile and "userData" in user_profile and "active_chat_id" in user_profile["userData"]:
                active_chat_id = user_profile["userData"]["active_chat_id"]

            await self.mongo_manager.add_chat_message(self.user_id, active_chat_id, new_message)
            print(f"BaseContextEngine.execute_outputs - saved message to chat '{active_chat_id}' for user {self.user_id}")

            # Add notification using MongoManager
            notification_payload = {
                "type": "context_engine_update", # Specific type for context engine messages
                "message_id": new_message["id"], # Correlate with the chat message if needed
                "text": message, # The actual content of the notification
                "timestamp": new_message["timestamp"]
            }
            await self.mongo_manager.add_notification(self.user_id, notification_payload)
            print(f"BaseContextEngine.execute_outputs - saved notification for user {self.user_id}")

            await self.websocket_manager.send_personal_message(json.dumps({"type": "notification", "data": notification_payload}), self.user_id)
            print(f"BaseContextEngine.execute_outputs - sent WebSocket notification to user {self.user_id}")
        else:
            print("BaseContextEngine.execute_outputs - no message to process")
        print("BaseContextEngine.execute_outputs finished")