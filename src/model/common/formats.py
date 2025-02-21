context_classification_required_format = {
    "type": "object",
    "properties": {"class": {"type": "string", "enum": ["personal", "general"]}},
    "required": ["class"],
    "additionalProperties": False,
}

orchestrator_required_format = {
    "type": "object",
    "properties": {
        "class": {"type": "string", "enum": ["agent", "memory", "chat"]},
        "input": {"type": "string"},
    },
    "required": ["class", "input"],
    "additionalProperties": False,
}

internet_classification_required_format = {
    "type": "object",
    "properties": {"class": {"type": "string", "enum": ["Internet", "None"]}},
    "required": ["class"],
    "additionalProperties": False,
}
