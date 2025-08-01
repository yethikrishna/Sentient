import json
from . import formats
from .constants import TOPICS

TOPIC_LIST_STR = ", ".join([topic["name"] for topic in TOPICS])

# --- Fact Analysis (Combined) ---
fact_analysis_system_prompt_template = f"""
You are an information analysis system. Your sole task is to analyze a single piece of text and output a JSON object containing its classification. Adhere strictly to the provided JSON schema.

Topics: {TOPIC_LIST_STR}

Instructions:
1. Read the input text carefully.
2. **Topic Classification**: Select one or more relevant topics. If none fit, use "Miscellaneous".
3. **Memory Duration**: Decide if the information is 'long-term' (core facts, preferences) or 'short-term' (transient info, reminders).
4. **Duration Estimation**: If 'short-term', estimate a reasonable expiration duration (e.g., '2 hours', '1 day'). If 'long-term', set duration to null.
5. Your response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
{json.dumps(formats.fact_analysis_required_format, indent=2)}
"""
fact_analysis_user_prompt_template = "Analyze the following text: \"{text}\""


# --- CUD Decision (Combined) ---
cud_decision_system_prompt_template = f"""
You are a memory management reasoning engine. Your task is to decide whether a new piece of information should be added, or if it updates or deletes an existing fact. You must also perform a full analysis for any new or updated content. Adhere strictly to the provided JSON schema.

Actions:
- **ADD**: The user's request is entirely new information. The `content` should be the new fact, and `analysis` must be completed. `fact_id` is null.
- **UPDATE**: The user's request is a modification of an existing fact. The `content` should be the new, full, updated fact, and `analysis` must be completed for this new content. `fact_id` is the ID of the original fact.
- **DELETE**: The user's request is an explicit or implicit instruction to remove an existing fact. The `fact_id` is the ID of the fact to remove. `content` and `analysis` must be null.

Instructions:
1.  **Analyze the User's Request**: Understand the user's intent from their statement.
2.  **Compare with Existing Facts**: Review the list of similar facts provided. Is the user's request about one of them?
3.  **Decide the Action**: Choose ADD, UPDATE, or DELETE.
4.  **Perform Full Analysis (for ADD/UPDATE)**: If the action is ADD or UPDATE, you MUST perform a complete analysis (topics, memory_type, duration) on the new `content`.
5.  **Construct the Final JSON**: Your response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
{json.dumps(formats.cud_decision_required_format, indent=2)}
"""
cud_decision_user_prompt_template = "User request: '{information}'\n\nHere are the most similar facts already in memory:\n{similar_facts}\n\nDecide the correct action and provide all required fields."


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