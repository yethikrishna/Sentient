from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import time
from server.db.mongo_manager import MongoManager # Import MongoManager

class BaseContextEngine(ABC):
    """Abstract base class for context engines handling various data sources."""

    def __init__(self, user_id, task_queue, memory_backend, websocket_manager, chats_db_lock, notifications_db_lock):
        print(f"BaseContextEngine.__init__ started for user_id: {user_id}")
        self.user_id = user_id
        self.task_queue = task_queue
        self.memory_backend = memory_backend
        self.websocket_manager = websocket_manager
        self.chats_db_lock = chats_db_lock
        self.notifications_db_lock = notifications_db_lock
        self.mongo_manager = MongoManager() # Initialize MongoManager
        self.context = asyncio.run(self.load_context()) # Await the async load_context
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
        pass

    async def run_engine(self):
        """Orchestrate fetching, processing, and generating outputs."""
        self.context = self.load_context()
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
:start_line:127
-------
        print("BaseContextEngine.get_chat_history started")
        async with self.chats_db_lock:
            print("BaseContextEngine.get_chat_history - acquired db_lock")
            # Fetch active chat ID for the user
            user_chat_data = await self.mongo_manager.get_collection("chats").find_one({"user_id": self.user_id})
            if not user_chat_data or "active_chat_id" not in user_chat_data:
                print("BaseContextEngine.get_chat_history - no active chat ID found for user, returning empty list")
                return []

            active_chat_id = user_chat_data["active_chat_id"]
            print(f"BaseContextEngine.get_chat_history - active_chat_id: {active_chat_id} for user_id: {self.user_id}")

            # Fetch the specific chat messages
            active_chat = await self.mongo_manager.get_collection("chat_messages").find_one(
                {"user_id": self.user_id, "chat_id": active_chat_id}
            )

            if active_chat and "messages" in active_chat:
                history = active_chat["messages"][-10:]
                print(f"BaseContextEngine.get_chat_history - returning last 10 messages: {history}")
                print("BaseContextEngine.get_chat_history finished")
                return history
            else:
                print("BaseContextEngine.get_chat_history - no active chat found or no messages, returning empty list")
                print("BaseContextEngine.get_chat_history finished")
                return []

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
            print("BaseContextEngine.execute_outputs - processing message:", message)
:start_line:188
-------
            # Save to notifications collection in MongoDB
            async with self.notifications_db_lock:
                print("BaseContextEngine.execute_outputs - acquired notifications_db_lock")
                
                # Get the current max notification ID for the user
                last_notification = await self.mongo_manager.get_collection("notifications").find_one(
                    {"user_id": self.user_id},
                    sort=[("id", -1)]
                )
                next_notification_id = (last_notification["id"] + 1) if last_notification else 1

                new_notification = {
                    "user_id": self.user_id, # Ensure multi-tenancy
                    "id": next_notification_id,
                    "type": "new_message",
                    "message_id": new_message["id"],
                    "message": message,
                    "timestamp": new_message["timestamp"]
                }
                print("BaseContextEngine.execute_outputs - adding notification:", new_notification)
                await self.mongo_manager.get_collection("notifications").insert_one(new_notification)
                print("BaseContextEngine.execute_outputs - saved notification to MongoDB")
                
                notification = {"type": "new_message", "message": message}
                print("BaseContextEngine.execute_outputs - broadcasting notification:", notification)
                await self.websocket_manager.broadcast(notification) # json.dumps is not needed here, websocket_manager handles it
        else:
            print("BaseContextEngine.execute_outputs - no message to process")
        print("BaseContextEngine.execute_outputs finished")