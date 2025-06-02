unified_classification_format = {
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "enum": ["chat", "memory", "agent"]
    },
    "use_personal_context": {
      "type": "boolean"
    },
    "internet": {
      "type": "boolean",
    },
    "transformed_input": {
      "type": "string"
    }
  },
  "required": ["category", "use_personal_context", "internet", "transformed_input"],
  "additionalProperties": False
}

priority_required_format = {
    "type": "object",
    "properties": {
        "priority": {
            "type": "integer",
            "enum": [0, 1, 2],
        }
    },
    "required": ["priority"],
    "additionalProperties": False,
}
