# (Copied from old system)
text_dissection_required_format = {
    "type": "object",
    "properties": {
        "categories": {
            "type": "object",
            "properties": {
                "Personal": {"type": "string"},
                "Interests": {"type": "string"},
                "Career": {"type": "string"},
                "Relationships": {"type": "string"},
                "Goals": {"type": "string"},
                "Education": {"type": "string"},
                "Health": {"type": "string"},
                "Financial": {"type": "string"},
                "Lifestyle": {"type": "string"},
                "Values": {"type": "string"},
                "Achievements": {"type": "string"},
                "Challenges": {"type": "string"},
                "Preferences": {"type": "string"},
                "Socials": {"type": "string"},
                "Miscellaneous": {"type": "string"},
            },
            "required": [
                "Personal", "Interests", "Career", "Relationships", "Goals",
                "Education", "Health", "Financial", "Lifestyle", "Values",
                "Achievements", "Challenges", "Preferences", "Socials", "Miscellaneous"
            ],
        },
    },
    "required": ["categories"],
}

information_extraction_required_format = {
    "type": "object",
    "properties": {
        "category": {"type": "string"},
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "relationship": {"type": "string"},
                    "target": {"type": "string"},
                    "source_properties": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]},
                    "target_properties": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]},
                },
                "required": ["source", "relationship", "target", "source_properties", "target_properties"],
            },
        },
    },
    "required": ["category", "relationships"],
}

query_classification_required_format = {
    "type": "object",
    "properties": {"category": {"type": "string"}},
    "required": ["category"],
}

fact_extraction_required_format = {"type": "array", "items": {"type": "string"}}

crud_decision_required_format = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["create", "update", "delete"]},
            "node": {"type": "string"},
            "properties": {"type": "object"},
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "type": {"type": "string"},
                        "action": {"type": "string", "enum": ["create", "update", "delete"]},
                        "target_properties": {"type": "object"},
                    },
                    "required": ["target", "type", "action"],
                },
            },
        },
        "required": ["action", "node"],
    },
}