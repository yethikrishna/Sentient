# src/server/main/runnables.py
import os
import json
import requests
from typing import Dict, Any, List, Union, Optional, Generator, Tuple, AsyncGenerator
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from wrapt_timeout_decorator import timeout 
from sys import platform 

# Load .env from server directory
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

# Assume these are similar prompts used by the main server
# or adjust as needed by the actual LLM interaction logic in main.py
chat_system_prompt_template = "You are a helpful AI assistant."
chat_user_prompt_template = "{query}"


class BaseRunnable(ABC):
    @abstractmethod
    def __init__(self, model_url: Optional[str], model_name: str, system_prompt_template: str,
                 user_prompt_template: str, input_variables: List[str], response_type: str,
                 required_format: Optional[Union[dict, list]] = None, stream: bool = False,
                 stateful: bool = False, api_key: Optional[str] = None):
        self.model_url: Optional[str] = model_url
        self.model_name: str = model_name
        self.system_prompt_template: str = system_prompt_template
        self.user_prompt_template: str = user_prompt_template
        self.input_variables: List[str] = input_variables
        self.response_type: str = response_type
        self.required_format: Optional[Union[dict, list]] = required_format
        self.stream: bool = stream
        self.stateful: bool = stateful
        self.messages: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt_template}] if system_prompt_template else []
        self.api_key: Optional[str] = api_key

    def build_prompt(self, inputs: Dict[str, Any]) -> None:
        user_prompt = self.user_prompt_template.format(**inputs)
        
        if self.stateful:
            self.messages.append({"role": "user", "content": user_prompt})
        else:
            self.messages = []
            if self.system_prompt_template:
                 self.messages.append({"role": "system", "content": self.system_prompt_template})
            self.messages.append({"role": "user", "content": user_prompt})

    def add_to_history(self, chat_history: List[Dict[str, str]]) -> None:
        self.messages = []
        if self.system_prompt_template:
            self.messages.append({"role": "system", "content": self.system_prompt_template})
        self.messages.extend(chat_history)

    def clear_history(self) -> None:
        self.messages = []
        if self.system_prompt_template:
            self.messages.append({"role": "system", "content": self.system_prompt_template})
    
    @abstractmethod
    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[Dict[str, Any], List[Any], str, None]:
        pass

    @abstractmethod
    async def astream_response(self, inputs: Dict[str, Any]) -> AsyncGenerator[Optional[str], None]:
        # This is an async generator, so it needs to be defined with `async def`
        # and use `yield` for streaming. The `pass` here is a placeholder.
        # Since it's abstract, the actual implementation will be in subclasses.
        # To make pylint happy with an empty async generator:
        if False: # This block will not be executed
            yield None


class OllamaRunnable(BaseRunnable):
    """
    Runnable for Ollama models, compatible with the main server's direct usage.
    """
    def __init__(self, model_name: str, model_url: Optional[str] = None,
                 system_prompt_template: str = "You are a helpful assistant.", 
                 user_prompt_template: str = "{query}", 
                 stream: bool = True, stateful: bool = True):
        
        super().__init__(
            model_url=model_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat"), # Use OLLAMA_BASE_URL
            model_name=model_name,
            system_prompt_template=system_prompt_template,
            user_prompt_template=user_prompt_template,
            input_variables=["query"], # Simplified for direct use
            response_type="chat", # Assuming text chat
            stream=stream,
            stateful=stateful
        )

    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[Dict[str, Any], str, None]:
        self.build_prompt(inputs) # inputs should contain 'query'
        payload = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False,
            "options": {"num_ctx": 4096}, 
        }
        # For a simple general response, JSON format is not typically needed from Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(self.model_url, json=payload, timeout=60.0)
        
        if response.status_code == 200:
            try:
                data = response.json().get("message", {}).get("content", "")
                if self.stateful:
                    self.messages.append({"role": "assistant", "content": data})
                return data
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to decode JSON response from Ollama: {response.text}. Error: {e}")
        raise ValueError(f"Ollama request failed with status {response.status_code}: {response.text}")

    async def astream_response(self, inputs: Dict[str, Any]) -> AsyncGenerator[Optional[str], None]:
        self.build_prompt(inputs)
        payload = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": True,
            "options": {"num_ctx": 4096},
        }
        
        full_response_content = ""
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", self.model_url, json=payload, timeout=60.0) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get("done", False):
                                break 
                            content_chunk = data.get("message", {}).get("content")
                            if content_chunk:
                                full_response_content += content_chunk
                                yield content_chunk
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON stream line from Ollama: {line}")
                            continue
        if self.stateful:
            self.messages.append({"role": "assistant", "content": full_response_content})
        yield None # Signal end of stream

class OpenRouterRunnable(BaseRunnable):
    """
    Runnable for OpenRouter API.
    """
    def __init__(self, model_name: str, api_key: str,
                 system_prompt_template: str = "You are a helpful assistant.", 
                 user_prompt_template: str = "{query}", 
                 stream: bool = True, stateful: bool = True):
        super().__init__(
            model_url="https://openrouter.ai/api/v1/chat/completions", # OpenRouter API URL
            model_name=model_name,
            system_prompt_template=system_prompt_template,
            user_prompt_template=user_prompt_template,
            input_variables=["query"],
            response_type="chat",
            stream=stream,
            stateful=stateful,
            api_key=api_key
        )
        if not self.api_key:
            raise ValueError("OpenRouter API key is required.")

    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[Dict[str, Any], str, None]:
        self.build_prompt(inputs)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.model_url, json=payload, headers=headers, timeout=60.0)

        if response.status_code == 200:
            try:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if self.stateful:
                    self.messages.append({"role": "assistant", "content": content})
                return content
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                raise ValueError(f"Failed to parse response from OpenRouter: {response.text}. Error: {e}")
        raise ValueError(f"OpenRouter request failed with status {response.status_code}: {response.text}")

    async def astream_response(self, inputs: Dict[str, Any]) -> AsyncGenerator[Optional[str], None]:
        self.build_prompt(inputs)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Sentient Electron Client" # Optional: For OpenRouter analytics
        }
        payload = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": True
        }
        full_response_content = ""
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", self.model_url, json=payload, headers=headers, timeout=60.0) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line_data = line[len("data: "):]
                        if line_data.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(line_data)
                            content_chunk = data.get("choices", [{}])[0].get("delta", {}).get("content")
                            if content_chunk:
                                full_response_content += content_chunk
                                yield content_chunk
                        except (json.JSONDecodeError, IndexError, KeyError):
                            print(f"Warning: Could not decode JSON stream line from OpenRouter: {line_data}")
                            continue
        if self.stateful:
            self.messages.append({"role": "assistant", "content": full_response_content})
        yield None


# Other runnable classes (OpenAI, Claude, Gemini) would follow a similar pattern
# For now, the main server will implement dummy logic or specific client calls for prod.
# This runnables.py is more for a unified agent interaction pattern which might be used by agents_server
# or if main_server evolves to use it directly for complex chain-of-thought.