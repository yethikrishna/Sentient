import json
from . import formats
from .constants import TOPICS

TOPIC_LIST_STR = ", ".join([topic["name"] for topic in TOPICS])

# --- Topic Classification ---
topic_classification_system_prompt_template = f"""
You are a classification system. Your task is to categorize the user's input text into one or more relevant topics from the provided list.

Topics: {TOPIC_LIST_STR}

Instructions:
1. Read the input text carefully.
2. Select the most appropriate topic(s). It is possible to select more than one.
3. If no topic is a good fit, select "Miscellaneous".
4. Your response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
{json.dumps(formats.topic_classification_required_format, indent=2)}
"""
topic_classification_user_prompt_template = "{text}"


# --- Memory Type Classification (Long-Term vs. Short-Term) ---
memory_type_decision_system_prompt_template = f"""
You are a memory classification system. Your task is to determine if a given piece of information should be stored as long-term or short-term memory.

- **Long-term memory** is for core facts, preferences, relationships, and important details that should be retained indefinitely.
    Examples: "My best friend's name is Alex.", "I am allergic to peanuts.", "I work as a software engineer."
- **Short-term memory** is for transient information, temporary context, or reminders that should expire after a certain period.
    Examples: "Remind me to call the doctor in 2 hours.", "For the next day, my temporary password is 'abc-123'.", "I parked my car in section G3."

Instructions:
1. Analyze the user's input.
2. Decide if it's 'long-term' or 'short-term'.
3. If it is 'short-term', estimate a reasonable expiration duration (e.g., '2 hours', '1 day').
4. Your response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
{json.dumps(formats.memory_type_decision_required_format, indent=2)}
"""
memory_type_decision_user_prompt_template = "Fact: \"{fact_content}\""


# --- Edit/Delete Decision ---
edit_decision_system_prompt_template = f"""
You are a reasoning engine for a memory system. Based on a user's request and a list of existing, similar facts, you must decide what action to take.

Actions:
- **ADD**: The user's request is entirely new information.
- **UPDATE**: The user's request is a modification of an existing fact.
- **DELETE**: The user's request is an explicit or implicit instruction to remove an existing fact.

Instructions:
1. Compare the user's request with each of the provided facts.
2. Decide if the request is an UPDATE of one of the facts, a DELETE instruction, or ADD if it's new.
3. If the action is UPDATE, provide the `fact_id` of the original fact and the `new_content`.
4. If the action is DELETE, provide the `fact_id` of the fact to be removed.
5. If the action is ADD, provide the `new_content` and set `fact_id` to null.
6. Your response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
{json.dumps(formats.edit_decision_required_format, indent=2)}
"""
edit_decision_user_prompt_template = "User request: '{information}'\n\nHere are the most similar facts already in memory:\n{similar_facts}\n\nDecide the correct action (ADD, UPDATE, or DELETE)."


# --- Fact Summarization ---
fact_summarization_system_prompt_template = """
You are a text synthesis system. Your task is to convert a list of distinct facts into a single, cohesive, human-readable paragraph.

Instructions:
1. Weave the provided facts into a natural language summary.
2. Do not present the information as a list.
3. If the list of facts is empty, state that no relevant information was found.
4. Respond only with the summarized paragraph.
"""
fact_summarization_user_prompt_template = "Facts: {facts}"


# --- Fact Extraction ---
fact_extraction_system_prompt_template = f"""
You are an expert system for information decomposition. Your primary goal is to break down a user's statement into a list of "atomic" facts. An atomic fact is a single, indivisible piece of information.

Key Instructions:
1. **Deconstruct Compound Sentences**: Vigorously split sentences containing conjunctions like 'and', 'but', or 'while' into separate, self-contained facts. Each fact must stand on its own.
2. **Isolate Each Idea**: Ensure every item in the output list represents one distinct idea. A single sentence from the user might contain multiple facts.
3. **Handle Pronouns and Possessives**: If the input contains "I", "me", or "my", correctly convert them to refer to the provided USERNAME. For example, "My sister" becomes "{{USERNAME}}'s sister".
4. **Strict JSON Output**: Your entire response MUST be a single, valid JSON array of strings that strictly adheres to the following schema. Do not add any commentary before or after the JSON.

JSON Schema:
{json.dumps(formats.fact_extraction_required_format, indent=2)}

---
**Examples of Correct Decomposition:**
---

**Example 1:**
Username: 'user123'
Paragraph: "I work at Google and my sister works there as well."
Correct Output:
["user123 works at Google.", "user123's sister works at Google."]

**Example 2:**
Username: 'user456'
Paragraph: "My favorite color is blue, but I also like green, and I live in New York."
Correct Ouptut:
["user456's favorite color is blue.", "user456 also likes green.", "user456 lives in New York."]

"""
fact_extraction_user_prompt_template = "Username: '{username}'\n\nParagraph: {paragraph}"