from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
import json5

# --- LLM and Tool Configuration ---

# Define LLM configuration for Ollama
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
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
            return str(a / b)
        except Exception as e: return f"Error: {e}"


# --- The Streaming Function for Qwen Agent (Unchanged) ---
# This function is already robust enough to handle the new scenario.

def qwen_text_stream(bot: Assistant, messages: list):
    """
    Streams text from a Qwen Agent, filters out <think> blocks and tool calls,
    and yields complete, speakable sentences.
    """
    buffer = ""
    processed_lengths = {}  # Tracks processed length for each message index
    sentence_terminators = {'.', '?', '!', '\n'}

    for responses in bot.run(messages=messages):
        for i, response in enumerate(responses):
            if response.get('role') == 'assistant' and 'content' in response and response['content']:
                last_len = processed_lengths.get(i, 0)
                current_content = response['content']
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


# --- Main Execution with a Multi-Step Problem ---

# 1. Initialize the agent with the new, larger tool list
tool_list = ['add', 'subtract', 'multiply', 'divide']
bot = Assistant(llm=llm_cfg, function_list=tool_list)

# 2. Define prompts and a multi-step user message
system_prompt = """You are a helpful math assistant. 
First, think step-by-step to break down the user's request.
Before calling a tool for a step, announce what you are about to do. For example: 'First, I'll multiply 12 by 5.'
After all steps are complete, state the final answer clearly."""
messages = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': 'Could you please multiply 15 by 8, and then subtract 20 from the result?'},
]

# 3. Stream the response and process for TTS
full_spoken_response = ""
print("--- User Request ---")
print(messages[-1]['content'])
print("\n--- Streaming to TTS ---")

try:
    for sentence in qwen_text_stream(bot, messages):
        print("Sentence sent to TTS:", sentence)
        full_spoken_response += sentence + " "
except Exception as e:
    print(f"An error occurred during streaming: {e}")

print("\n--- Final Spoken Output ---")
print(f"Full TTS Script: {full_spoken_response.strip()}")