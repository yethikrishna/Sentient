import re

def clean_llm_output(text):
    """
    Removes reasoning tags (e.g., <think>...</think>) and trims whitespace from LLM output.
    This is crucial for models that output their thought process.
    """
    # Use re.DOTALL to make '.' match newlines, and '?' for non-greedy matching.
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text.strip()