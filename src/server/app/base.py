import os
import requests
from typing import Dict, Any, List, Union, Optional, Generator, Tuple
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import json
import platform # Keep for Ollama platform-specific JSON format

# Load .env from the server's root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

def get_selected_model() -> Tuple[str, str]:
    """
    Returns a default model configuration. For the revamped server,
    we'll use a simple local Ollama model if a dummy chat response still needs an LLM,
    or this function can be made to return None if chat is fully hardcoded.
    """
    # Default to a local Ollama model for simplicity or dummy responses.
    # The BASE_MODEL_REPO_ID can be set in .env to something like "llama3.2:3b"
    default_model_name = os.getenv("BASE_MODEL_REPO_ID", "dummy_model") # e.g., llama3.2:3b or a placeholder
    default_provider = "ollama" # Assuming Ollama for local/dummy
    
    # If BASE_MODEL_REPO_ID is explicitly set to "dummy_model" or not set,
    # we can indicate that no real LLM call should be made for chat.
    if default_model_name == "dummy_model":
        return "dummy_model", "dummy_provider" # Special values to indicate hardcoded dummy response

    return default_model_name, default_provider


class BaseRunnable(ABC):
    """
    Abstract base class for runnable language model interactions.
    Simplified for the revamped server focusing on dummy responses.
    """
    @abstractmethod
    def __init__(self, model_url: Optional[str], model_name: str, 
                 system_prompt_template: Optional[str] = None, # Optional for dummy
                 user_prompt_template: Optional[str] = None,   # Optional for dummy
                 response_type: str = "text", # Default to text
                 stream: bool = False):
        self.model_url: Optional[str] = model_url
        self.model_name: str = model_name
        self.system_prompt_template: Optional[str] = system_prompt_template
        self.user_prompt_template: Optional[str] = user_prompt_template
        self.response_type: str = response_type
        self.stream: bool = stream
        self.messages: List[Dict[str, str]] = [] # Still useful for structuring input if an LLM (even local) is hit

    def build_prompt(self, inputs: Dict[str, Any]) -> None:
        """
        Builds the prompt. For dummy responses, this might be minimal or unused
        if the LLM call is bypassed.
        """
        # If system_prompt_template is defined, add it
        if self.system_prompt_template:
            self.messages = [{"role": "system", "content": self.system_prompt_template}]
        else:
            self.messages = []

        # If user_prompt_template and inputs are relevant, format and add user message
        if self.user_prompt_template and "query" in inputs:
            user_prompt = self.user_prompt_template.format(**inputs)
            self.messages.append({"role": "user", "content": user_prompt})
        elif "query" in inputs: # If no template, just use query directly
            self.messages.append({"role": "user", "content": inputs["query"]})


    @abstractmethod
    def invoke(self, inputs: Dict[str, Any]) -> Union[Dict[str, Any], str, None]:
        pass

    @abstractmethod
    def stream_response(self, inputs: Dict[str, Any]) -> Generator[Optional[str], None, None]:
        pass

class OllamaRunnable(BaseRunnable):
    """
    Simplified Runnable for Ollama, potentially for generating dummy responses if not hardcoded.
    """
    def __init__(self, model_name: str, system_prompt_template: Optional[str] = None, 
                 user_prompt_template: Optional[str] = None, response_type: str = "text", stream: bool = False):
        
        ollama_url = os.getenv("BASE_MODEL_URL", "http://localhost:11434/api/chat")
        super().__init__(model_url=ollama_url, model_name=model_name, 
                         system_prompt_template=system_prompt_template,
                         user_prompt_template=user_prompt_template,
                         response_type=response_type, stream=stream)

    def invoke(self, inputs: Dict[str, Any]) -> Union[Dict[str, Any], str, None]:
        """
        Invokes Ollama for a non-streaming dummy response.
        """
        # For a dummy response, we might not even call Ollama.
        # This depends on how "dummy" the response needs to be.
        # If it's truly hardcoded, this method won't be called by the chat endpoint.
        # If it's a *simple* LLM-generated dummy, then proceed:
        self.build_prompt(inputs)
        payload = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False,
            "options": {"num_ctx": 2048}, 
        }
        print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_INVOKE] Payload: {json.dumps(payload, indent=2)}")
        try:
            response = requests.post(self.model_url, json=payload, timeout=10) # Short timeout for dummy
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "This is a dummy Ollama response.")
            
            if self.response_type == "json":
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_INVOKE_ERROR] Expected JSON, got: {content}")
                    return {"error": "Invalid JSON format from dummy Ollama"}
            return content
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_INVOKE_ERROR] Request failed: {e}")
            return "Dummy Ollama call failed."
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_INVOKE_ERROR] Unexpected error: {e}")
            return "Unexpected error in dummy Ollama call."


    def stream_response(self, inputs: Dict[str, Any]) -> Generator[Optional[str], None, None]:
        """
        Streams a dummy response, potentially using Ollama for a simple phrase or hardcoded.
        """
        # For a truly hardcoded dummy streamed response, this will be handled directly in the endpoint.
        # If a simple Ollama call is made for the dummy stream:
        self.build_prompt(inputs)
        payload = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": True,
            "options": {"num_ctx": 2048},
        }
        print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_STREAM] Payload: {json.dumps(payload, indent=2)}")
        try:
            with requests.post(self.model_url, json=payload, stream=True, timeout=10) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get("done", False):
                                yield None # End of stream
                                break
                            yield data.get("message", {}).get("content", "")
                        except json.JSONDecodeError:
                            print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_STREAM_ERROR] Non-JSON line: {line}")
                            continue # Skip malformed lines
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_STREAM_ERROR] Request failed: {e}")
            yield "Dummy Ollama stream failed."
            yield None
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [OLLAMA_DUMMY_STREAM_ERROR] Unexpected error: {e}")
            yield "Unexpected error in dummy Ollama stream."
            yield None

# Mapping of provider names to their respective Runnable classes
# Simplified for the revamp.
RUNNABLE_MAP: Dict[str, type[BaseRunnable]] = {
    "ollama": OllamaRunnable,
    "dummy_provider": OllamaRunnable, # Map dummy to Ollama or a specific DummyRunnable
    # Remove OpenAI, Claude, Gemini, OpenRouter
}

# If you need to use these specific runnables, they would be imported here
# For now, they are removed as per the goal of simplification.
# from server.memory.runnables import get_graph_analysis_runnable, ...
# from server.agents.runnables import get_reflection_runnable, ...
# from server.chat.runnables import get_chat_runnable (this will be simplified or replaced)
# from server.common.runnables import get_internet_query_reframe_runnable, ...