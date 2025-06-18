import fastapi
from fastrtc import ReplyOnPause, Stream, AlgoOptions, SileroVadOptions
from fastrtc.utils import audio_to_bytes, audio_to_float32
import logging
import time
from fastapi.middleware.cors import CORSMiddleware
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import numpy as np

# Qwen Agent imports
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
import json5

ELEVENLABS_API_KEY = "REMOVED"  # Replace with your ElevenLabs API key
if ELEVENLABS_API_KEY == "YOUR_ELEVENLABS_API_KEY":
    print("WARNING: Replace YOUR_ELEVENLABS_API_KEY with your actual ElevenLabs API key.")

logging.basicConfig(level=logging.INFO)

# --- Qwen Agent Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',  # Or your preferred Qwen model
    'model_server': 'http://localhost:11434/v1/', # Your Ollama endpoint
    'api_key': 'ollama',  # Required by qwen-agent but unused for Ollama
}

# --- Tool Definitions ---
@register_tool('add')
class AddTool(BaseTool):
    description = 'A tool to add two integer numbers, a and b.'
    parameters = [{ 'name': 'a', 'type': 'int', 'description': 'The first number.', 'required': True },
                  { 'name': 'b', 'type': 'int', 'description': 'The second number.', 'required': True }]
    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            return str(int(args['a']) + int(args['b']))
        except Exception as e: return f"Error: {e}"

@register_tool('subtract')
class SubtractTool(BaseTool):
    description = 'A tool to subtract the second number (b) from the first number (a).'
    parameters = [{ 'name': 'a', 'type': 'int', 'description': 'The number to subtract from.', 'required': True },
                  { 'name': 'b', 'type': 'int', 'description': 'The number to subtract.', 'required': True }]
    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            return str(int(args['a']) - int(args['b']))
        except Exception as e: return f"Error: {e}"

@register_tool('multiply')
class MultiplyTool(BaseTool):
    description = 'A tool to multiply two integer numbers, a and b.'
    parameters = [{ 'name': 'a', 'type': 'int', 'description': 'The first number.', 'required': True },
                  { 'name': 'b', 'type': 'int', 'description': 'The second number.', 'required': True }]
    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            return str(int(args['a']) * int(args['b']))
        except Exception as e: return f"Error: {e}"

@register_tool('divide')
class DivideTool(BaseTool):
    description = 'A tool to divide the first number (a) by the second number (b).'
    parameters = [{ 'name': 'a', 'type': 'int', 'description': 'The dividend.', 'required': True },
                  { 'name': 'b', 'type': 'int', 'description': 'The divisor.', 'required': True }]
    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            a, b = int(args['a']), int(args['b'])
            if b == 0: return "Error: Cannot divide by zero."
            return str(a / b) # Returns float, will be converted to string
        except Exception as e: return f"Error: {e}"

# --- Initialize Qwen Agent Bot ---
tool_list = ['add', 'subtract', 'multiply', 'divide']
qwen_bot = Assistant(llm=llm_cfg, function_list=tool_list)

# --- System Prompt and Message History ---
sys_prompt = """You are a helpful math assistant. You are witty, engaging and fun.
First, think step-by-step to break down the user's request.
Before calling a tool for a step, announce what you are about to do. For example: 'First, I'll multiply 12 by 5.'
You can also use minimalistic utterances like 'uh-huh' or 'mm-hmm' to make the conversation more natural.
After all steps are complete, state the final answer clearly."""
messages = [{"role": "system", "content": sys_prompt}]

# --- ElevenLabs Client ---
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --- Qwen Agent Text Streaming Logic (from previous script) ---
def qwen_text_stream_for_echo(bot: Assistant, current_messages: list):
    """
    Streams text from a Qwen Agent for the echo function,
    filters out <think> blocks and tool calls, and yields complete, speakable sentences.
    """
    buffer = ""
    processed_lengths = {}
    sentence_terminators = {'.', '?', '!', '\n'}

    # bot.run() yields the *entire* list of messages at each step
    # We pass a copy of current_messages to avoid modification by bot.run internals if any
    for responses_list in bot.run(messages=list(current_messages)):
        for i, response_item in enumerate(responses_list):
            if response_item.get('role') == 'assistant' and 'content' in response_item and response_item['content']:
                last_len = processed_lengths.get(i, 0)
                current_content = response_item['content']
                if len(current_content) > last_len:
                    new_chunk = current_content[last_len:]
                    buffer += new_chunk
                    processed_lengths[i] = len(current_content)

        while '<think>' in buffer and '</think>' in buffer:
            start_idx = buffer.find('<think>')
            end_idx = buffer.find('</think>') + len('</think>')
            if start_idx < end_idx: buffer = buffer[:start_idx] + buffer[end_idx:]
            else: buffer = buffer.replace('</think>', '', 1)

        safe_to_process = buffer
        if '<think>' in buffer:
            safe_to_process = buffer[:buffer.find('<think>')]
        
        last_terminator_pos = -1
        positions = [safe_to_process.rfind(t) for t in sentence_terminators]
        if safe_to_process.rfind('...') > -1: positions.append(safe_to_process.rfind('...'))
        if positions: last_terminator_pos = max(positions)

        if last_terminator_pos != -1:
            terminator_len = 3 if safe_to_process.startswith('...', last_terminator_pos) else 1
            to_yield_part = safe_to_process[:last_terminator_pos + terminator_len]
            buffer = safe_to_process[last_terminator_pos + terminator_len:] + buffer[len(safe_to_process):]
            sentences = to_yield_part.replace('...', '...|').replace('.', '.|').replace('?', '?|').replace('!', '!|').replace('\n', '\n|').split('|')
            for sentence in sentences:
                if sentence.strip(): yield sentence.strip()

    if buffer.strip():
        final_part = buffer
        if '<think>' in final_part: final_part = final_part[:final_part.find('<think>')]
        if final_part.strip(): yield final_part.strip()


# --- FastRTC Echo Function ---
def echo(audio):
    global messages # Use the global messages list

    stt_time = time.time()
    logging.info("Performing STT")
    try:
        transcription = elevenlabs_client.speech_to_text.convert(
            file=audio_to_bytes(audio),
            model_id="scribe_v1",
            tag_audio_events=False,
            language_code="eng",
            diarize=False,
        )
        prompt = transcription.text # Assuming `transcription` has a `text` attribute
    except Exception as e:
        logging.error(f"STT Error: {e}")
        return

    if not prompt.strip(): # Check if prompt is empty or just whitespace
        logging.info("STT returned empty string or whitespace")
        return
    logging.info(f"STT response: '{prompt}'")
    messages.append({"role": "user", "content": prompt})
    logging.info(f"STT took {time.time() - stt_time:.2f} seconds")

    llm_time = time.time()
    full_spoken_response = ""

    # Use the Qwen agent stream
    for sentence in qwen_text_stream_for_echo(qwen_bot, messages):
        if not sentence.strip(): # Skip empty sentences
            continue
        
        logging.info(f"Sending to TTS: '{sentence}'")
        full_spoken_response += sentence + " "
        try:
            audio_stream = elevenlabs_client.text_to_speech.stream(
                text=sentence,
                voice_id="JBFqnCBsd6RMkjVDRZzb", # Example voice ID
                model_id="eleven_multilingual_v2",
                output_format="pcm_24000",
                voice_settings=VoiceSettings(
                    similarity_boost=0.75, stability=0.5, style=0.4, speed =1 # Example settings
                ),
            )
            for audio_chunk in audio_stream:
                if audio_chunk: # Ensure there's data in the chunk
                    audio_array = audio_to_float32(np.frombuffer(audio_chunk, dtype=np.int16))
                    yield (24000, audio_array) # Yield sample rate and audio data
        except Exception as e:
            logging.error(f"TTS Error for sentence '{sentence}': {e}")
            continue # Try to continue with the next sentence

    if full_spoken_response.strip():
        messages.append({"role": "assistant", "content": full_spoken_response.strip()})
        logging.info(f"LLM final spoken response: '{full_spoken_response.strip()}'")
    else:
        logging.info("LLM did not produce any speakable output.")
        
    logging.info(f"LLM processing took {time.time() - llm_time:.2f} seconds")


# --- FastRTC Stream Setup ---
stream = Stream(
    ReplyOnPause(
        echo,
        algo_options=AlgoOptions(
            audio_chunk_duration=0.5,
            started_talking_threshold=0.1,
            speech_threshold=0.03,
        ),
        model_options=SileroVadOptions(
            threshold=0.75, # VAD sensitivity
            min_speech_duration_ms=250,
            min_silence_duration_ms=1000, # Shorter silence for quicker replies
            speech_pad_ms=300, # Padding around detected speech
            max_speech_duration_s=15,
        ),
    ),
    modality="audio",
    mode="send-receive",
)

# --- FastAPI App Setup ---
app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stream.mount(app)

@app.get("/reset")
async def reset():
    global messages
    logging.info("Resetting chat history")
    # Keep the initial system prompt
    messages = [{"role": "system", "content": sys_prompt}]
    return {"status": "success", "message": "Chat history reset."}

# To run this: uvicorn your_filename:app --reload
# Example: uvicorn main_fastrtc_qwen:app --reload