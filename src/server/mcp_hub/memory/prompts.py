import json
from . import formats

text_dissection_system_prompt_template = f"""You are a categorization system designed to dissect bulk unstructured text into predefined categories for a user.

Instructions:
1. Divide the input text into the predefined categories listed in the JSON schema below.
2. For each category, extract the relevant portion of the input text and return it.
3. If some information belongs to multiple categories, include it in all relevant ones.
4. If no information is available for a category, return an empty string for that category.
5. Your entire response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
```json
{json.dumps(formats.text_dissection_required_format, indent=2)}
```
"""

text_dissection_user_prompt_template = "Dissect the following text into the predefined categories. Return a JSON object strictly adhering to the specified format.\n\nText: {text}"

information_extraction_system_prompt_template = f"""You are an advanced information extraction system. Your task is to extract entities and their relationships from a given text for a specific category.

Instructions:
1. Identify key entities (people, places, concepts, objects) and the relationships between them.
2. Structure the output as a JSON object containing the category name and a list of relationship triplets.
3. Each triplet in the 'relationships' list must have a 'source' entity, a 'relationship' type (in uppercase, e.g., 'WORKS_AT', 'LIKES'), a 'target' entity, and descriptions for both source and target properties.
4. If an entity is a direct attribute of the main category, the category itself should be the 'source'.
5. Your entire response MUST be a single, valid JSON object that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
```json
{json.dumps(formats.information_extraction_required_format, indent=2)}
```
"""

information_extraction_user_prompt_template = "Extract entities and relationships for the category '{category}' from the following text. Return the JSON object strictly adhering to the specified format.\n\nText: {text}"

graph_decision_system_prompt_template = f"""You are a reasoning system for graph-based knowledge management. Your task is to analyze existing graph data and new information, then decide on a series of Create, Update, or Delete (CRUD) operations.

Instructions:
1. Analyze the existing graph and the new information to decide what to create, update, or delete.
2. For each decision, include the 'action' (create, update, delete), the 'node' name, its 'properties', and a list of its 'relationships' with their own actions.
3. Exclude "do_nothing" actions from the output.
4. Your entire response MUST be a single, valid JSON array of decision objects that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
```json
{json.dumps(formats.crud_decision_required_format, indent=2)}
```
"""

graph_decision_user_prompt_template = "Given the following analysis of graph changes, return a JSON array of decisions. Strictly return no additional text.\n\nAnalysis:\n{analysis}"

text_conversion_system_prompt_template = """You are a reasoning system. Your task is to convert structured graph data into a single, cohesive, human-readable paragraph.

Instructions:
1. Use the provided nodes and relationships to create a flowing, natural language summary.
2. Refer to the individual described in the graph as "the user".
3. Do not list the relationships; instead, weave them into sentences.
4. If the graph data is empty, state that no relevant information was found.
"""

text_conversion_user_prompt_template = "Convert the following graph data into unstructured text. Use 'user' to describe the individual. Return only the text.\n\nInput:\n{graph_data}"

query_classification_system_prompt_template = f"""You are a classification system. Categorize the given query into the most relevant category from the provided list.

Categories: Personal, Interests, Career, Relationships, Goals, Education, Health, Financial, Lifestyle, Values, Achievements, Challenges, Preferences, Socials, Miscellaneous.

Return a JSON object with a single key "category" that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
```json
{json.dumps(formats.query_classification_required_format, indent=2)}
```
"""

query_classification_user_prompt_template = "Categorize the following query. Return the JSON object strictly adhering to the specified format.\n\nQuery: {query}"

fact_extraction_system_prompt_template = f"""
You are a system designed to convert an unstructured paragraph into a list of concise, single-sentence facts.

### Key Instructions:
1. If the input contains "I", "me", or "my", replace them with the provided USERNAME.
2. Each distinct idea or relationship must be its own sentence in the output list.
3. Your entire response MUST be a single, valid JSON array of strings that strictly adheres to the following schema. Do not include any other text or explanations.

JSON Schema:
```json
{json.dumps(formats.fact_extraction_required_format, indent=2)}
```
"""

fact_extraction_user_prompt_template = "Analyze the following paragraph and convert it into a JSON array of single-sentence points. Replace first-person pronouns with the username '{username}'.\n\nParagraph: {paragraph}"