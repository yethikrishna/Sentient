from abc import ABC, abstractmethod
import json
from datetime import datetime
import asyncio
import os
import time

class BaseContextEngine(ABC):
    """Abstract base class for context engines handling various data sources."""
    
    def __init__(self, user_id, task_queue, memory_backend, websocket_manager, db_lock):
        self.user_id = user_id
        self.task_queue = task_queue
        self.memory_backend = memory_backend
        self.websocket_manager = websocket_manager
        self.db_lock = db_lock
        self.context_file = "context.json"
        self.context = self.load_context()

    def load_context(self):
        """Load the context from a JSON file, or return an empty dict if it doesn't exist."""
        if os.path.exists(self.context_file):
            with open(self.context_file, 'r') as f:
                return json.load(f)
        return {}

    def save_context(self):
        """Save the current context to the JSON file."""
        with open(self.context_file, 'w') as f:
            json.dump(self.context, f, indent=4)

    async def start(self):
        """Start the engine, running periodically every hour."""
        while True:
            await self.run_engine()
            await asyncio.sleep(3600)  # Check every hour

    async def run_engine(self):
        """Orchestrate fetching, processing, and generating outputs."""
        new_data = await self.fetch_new_data()
        if new_data:
            processed_data = self.process_new_data(new_data)
            output = self.generate_output(processed_data)
            await self.execute_outputs(output)

    @abstractmethod
    async def fetch_new_data(self):
        """Fetch new data from the specific data source."""
        pass

    @abstractmethod
    def process_new_data(self, new_data):
        """Process the fetched data into a format suitable for the runnable."""
        pass

    @abstractmethod
    def get_runnable(self):
        """Return the data source-specific runnable for generating outputs."""
        pass

    @abstractmethod
    def get_category(self):
        """Return the memory category for this data source."""
        pass

    def generate_output(self, processed_data):
        """Generate tasks, memory operations, and messages using the runnable."""
        runnable = self.get_runnable()
        related_memories = self.memory_backend.retrieve_memory(self.user_id, category=self.get_category())
        ongoing_tasks = [task for task in await self.task_queue.get_all_tasks() if task["status"] in ["pending", "processing"]]
        chat_history = await self.get_chat_history()
        memories_str = "\n".join([mem["text"] for mem in related_memories])
        tasks_str = "\n".join([task["description"] for task in ongoing_tasks])
        chat_str = "\n".join([f"{'User' if msg['isUser'] else 'Assistant'}: {msg['message']}" for msg in chat_history])
        output = runnable.invoke({
            "new_information": processed_data,
            "related_memories": memories_str,
            "ongoing_tasks": tasks_str,
            "chat_history": chat_str
        })
        return json.loads(output)

    async def get_chat_history(self):
        """Retrieve the last 10 messages from the active chat."""
        async with self.db_lock:
            from app import load_db  # Import here to avoid circular import
            chatsDb = await load_db()
            active_chat_id = chatsDb["active_chat_id"]
            active_chat = next((chat for chat in chatsDb["chats"] if chat["id"] == active_chat_id), None)
            return active_chat["messages"][-10:] if active_chat else []

    async def execute_outputs(self, output):
        """Execute the generated tasks, memory operations, and messages."""
        tasks = output.get("tasks", [])
        memory_ops = output.get("memory_operations", [])
        messages = output.get("messages", [])

        # Add tasks to the task queue
        for task in tasks:
            await self.task_queue.add_task(
                chat_id="context_engine",
                description=task["description"],
                priority=task["priority"],
                username=self.user_id,
                personality=None,
                use_personal_context=False,
                internet="None"
            )

        # Add memory operations to the memory queue
        for op in memory_ops:
            if op["operation"] == "add":
                await self.memory_backend.memory_queue.add_operation({
                    "type": "add",
                    "user_id": self.user_id,
                    "text": op["text"],
                    "category": op["category"],
                    "retention_days": op["retention_days"]
                })
            elif op["operation"] == "update":
                await self.memory_backend.memory_queue.add_operation({
                    "type": "update",
                    "user_id": self.user_id,
                    "category": op["category"],
                    "id": op["id"],
                    "text": op["text"],
                    "retention_days": op["retention_days"]
                })
            elif op["operation"] == "delete":
                await self.memory_backend.memory_queue.add_operation({
                    "type": "delete",
                    "user_id": self.user_id,
                    "category": op["category"],
                    "id": op["id"]
                })

        # Add messages to the chat database and send notifications
        from app import save_db, load_db
        for message in messages:
            async with self.db_lock:
                chatsDb = await load_db()
                active_chat_id = chatsDb["active_chat_id"]
                active_chat = next((chat for chat in chatsDb["chats"] if chat["id"] == active_chat_id), None)
                if active_chat:
                    new_message = {
                        "id": str(int(time.time() * 1000)),
                        "type": "system_message",
                        "message": message,
                        "isUser": False,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    active_chat["messages"].append(new_message)
                    await save_db(chatsDb)
                    notification = {
                        "type": "new_message",
                        "message": message
                    }
                    await self.websocket_manager.broadcast(json.dumps(notification))
                    
