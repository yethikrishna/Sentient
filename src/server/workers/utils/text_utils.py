import re

def clean_llm_output(text: str) -> str:
    """
    Removes reasoning tags (e.g., <think>...</think>) and trims whitespace from LLM output.
    """
    if not isinstance(text, str):
        return ""
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text.strip()