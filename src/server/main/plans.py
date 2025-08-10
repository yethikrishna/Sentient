PLAN_LIMITS = {
    "free": {
        "text_messages_daily": 50,
        "sync_tasks_daily": 5,
        "voice_chat_daily_seconds": 2 * 60,
        "one_time_tasks_daily": 5,
        "recurring_tasks_active": 3,
        "triggered_tasks_active": 2,
        "swarm_tasks_daily": 1,
        "swarm_sub_agents_max": 10,
        "file_uploads_daily": 3,
        "memories_total": 100,
    },
    "pro": {
        "text_messages_daily": 100,
        "sync_tasks_daily": float('inf'),  # Unlimited
        "voice_chat_daily_seconds": 10 * 60,
        "one_time_tasks_daily": 20,
        "recurring_tasks_active": 10,
        "triggered_tasks_active": 10,
        "swarm_tasks_daily": 5,
        "swarm_sub_agents_max": 50,
        "file_uploads_daily": 20,
        "memories_total": float('inf'),  # Unlimited
    },
    "selfhost": { # Self-host plan has unlimited access
        "text_messages_daily": float('inf'),
        "sync_tasks_daily": float('inf'),
        "voice_chat_daily_seconds": float('inf'),
        "one_time_tasks_daily": float('inf'),
        "recurring_tasks_active": float('inf'),
        "triggered_tasks_active": float('inf'),
        "swarm_tasks_daily": float('inf'),
        "swarm_sub_agents_max": float('inf'),
        "file_uploads_daily": float('inf'),
        "memories_total": float('inf'),
    }
}

# Features that are exclusively for Pro users
PRO_ONLY_FEATURES = [
    "proactivity",
    "calendar_mirroring", # Assuming this is part of proactivity
    "inbox_mirroring"  # Assuming this is part of proactivity
]

PRO_ONLY_INTEGRATIONS = [
    "gdocs", "gslides", "gsheets", # GSuite
    "linkedin"
]