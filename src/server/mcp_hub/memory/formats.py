from .constants import TOPICS

TOPIC_NAMES = [topic["name"] for topic in TOPICS]

# This format defines the full analysis of a single piece of text.
fact_analysis_required_format = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {"type": "string", "enum": TOPIC_NAMES},
            "description": "A list of one or more relevant topics for the given text. If none fit, use ['Miscellaneous']."
        },
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
    "required": ["topics", "memory_type", "duration"]
}

# This format is for the CUD (Create, Update, Delete) decision process.
cud_decision_required_format = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["ADD", "UPDATE", "DELETE"]},
        "fact_id": {"type": ["integer", "null"], "description": "The ID of the fact to be updated or deleted. This should be null if the action is ADD."},
        "content": {"type": ["string", "null"], "description": "The new, full content of the fact if the action is ADD or UPDATE. Should be null for DELETE."},
        "analysis": {
            "type": ["object", "null"],
            "properties": fact_analysis_required_format["properties"],
            "description": "A full analysis of the new content. Required for ADD or UPDATE actions, null for DELETE."
        }
    },
    "required": ["action", "fact_id", "content", "analysis"]
}