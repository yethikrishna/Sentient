from dotenv import load_dotenv
import os

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
