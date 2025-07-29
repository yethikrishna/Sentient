from .constants import TOPICS

TOPIC_NAMES = [topic["name"] for topic in TOPICS]

# For classifying text into one or more topics.
topic_classification_required_format = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {"type": "string", "enum": TOPIC_NAMES},
            "description": "A list of one or more relevant topics for the given text. If none fit, use ['Miscellaneous']."
        }
    },
    "required": ["topics"],
}

# For deciding on an action (UPDATE/DELETE/ADD) based on user intent and search results.
edit_decision_required_format = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["UPDATE", "DELETE", "ADD"]},
        "fact_id": {"type": ["integer", "null"], "description": "The ID of the fact to be updated or deleted. This should be null if the action is ADD."},
        "new_content": {"type": "string", "description": "The new, full content of the fact if the action is ADD or UPDATE."}
    },
    "required": ["action"]
}

# Kept for its general utility in breaking down paragraphs into single-sentence facts.
fact_extraction_required_format = {"type": "array", "items": {"type": "string"}}
# For deciding if a memory is long-term or short-term.
memory_type_decision_required_format = {
    "type": "object",
    "properties": {
        "memory_type": {
            "type": "string",
            "enum": ["long-term", "short-term"],
            "description": "The type of memory. Use 'short-term' for transient info like reminders or temporary context."
        },
        "duration": {
            "type": ["string", "null"],
            "description": "If memory_type is 'short-term', provide a human-readable duration (e.g., '1 hour', '3 days'). Otherwise, this should be null."
        }
    },
    "required": ["memory_type", "duration"]
}