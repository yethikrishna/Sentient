from openai import OpenAI
import logging

# Set up your system prompt
sys_prompt = """
You are a helpful assistant.
"""

messages = [{"role": "system", "content": sys_prompt}]

# Set up your OpenAI client
openai_client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama',  # required, but unused
)

# User's prompt
prompt = "Yo whats up."
if not prompt:
    print("STT returned empty string")
print(f"STT response: {prompt}")
messages.append({"role": "user", "content": prompt})

def text_stream():
    """
    Streams text from the LLM, correctly filters out <think> blocks, and yields complete sentences.
    This version correctly avoids deadlocks.
    """
    buffer = ""
    sentence_terminators = {'.', '?', '!', '\n'}

    response = openai_client.chat.completions.create(
        model="qwen3:4b", messages=messages, max_tokens=200, stream=True
    )

    for chunk in response:
        if chunk.choices[0].finish_reason == "stop":
            break
        
        if chunk.choices[0].delta.content:
            buffer += chunk.choices[0].delta.content

        # 1. Strip any complete <think>...</think> blocks from the buffer.
        while '<think>' in buffer and '</think>' in buffer:
            start_idx = buffer.find('<think>')
            end_idx = buffer.find('</think>') + len('</think>')
            if start_idx < end_idx:
                buffer = buffer[:start_idx] + buffer[end_idx:]
            else:
                # Malformed case, just remove the first end tag found.
                buffer = buffer.replace('</think>', '', 1)

        # 2. Identify the portion of the buffer that is safe to process.
        # This is the text up to the start of any new <think> block.
        safe_to_process = buffer
        if '<think>' in buffer:
            safe_to_process = buffer[:buffer.find('<think>')]

        # 3. Process the safe portion for complete sentences.
        start_of_unprocessed = 0
        # Using rfind to find the last possible sentence to avoid yielding fragments
        last_terminator_pos = -1
        # Find the position of the last terminator
        positions = [safe_to_process.rfind(t) for t in sentence_terminators]
        if safe_to_process.rfind('...') > -1: # Handle '...' separately
            positions.append(safe_to_process.rfind('...'))
        
        if positions:
            last_terminator_pos = max(positions)
        
        if last_terminator_pos != -1:
            # The text we can definitely yield
            to_yield_part = safe_to_process[:last_terminator_pos + 1]
            start_of_unprocessed = last_terminator_pos + 1
            
            # Yield all sentences within this part
            processed_len = 0
            # Simple split by common terminators, then filter out empty strings
            sentences = to_yield_part.replace('...', '...|').replace('.', '.|').replace('?', '?|').replace('!', '!|').replace('\n', '\n|').split('|')
            for sentence in sentences:
                if sentence.strip():
                    yield sentence.strip()
        
        # 4. Update the buffer to contain only the unprocessed text.
        # This includes the fragment after the last sentence and the part with the <think> tag.
        buffer = safe_to_process[start_of_unprocessed:] + buffer[len(safe_to_process):]


    # After the loop, if there's anything left in the buffer (and it's not a thought), yield it.
    if buffer.strip():
        final_part = buffer
        if '<think>' in final_part:
            final_part = final_part[:final_part.find('<think>')]
        if final_part.strip():
            yield final_part.strip()


# --- Main Execution ---
full_response = ""
print("\n--- Streaming to TTS ---")
try:
    for sentence in text_stream():
        print("Sentence sent to TTS:", sentence)
        full_response += sentence + " "
except Exception as e:
    print(f"An error occurred during streaming: {e}")

# Append the final, complete response to the message history for context.
if full_response:
    messages.append({"role": "assistant", "content": full_response.strip()})

print("\n--- Final Output ---")
print(f"LLM response: {full_response.strip()}")