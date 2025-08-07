import os
from posthog import Posthog

# It's important to use the API key directly, not the public/project key, for backend events.
POSTHOG_KEY = os.getenv("POSTHOG_KEY") 
POSTHOG_HOST = os.getenv("POSTHOG_HOST")

posthog_client = None
if POSTHOG_KEY and POSTHOG_HOST:
    posthog_client = Posthog(project_api_key=POSTHOG_KEY, host=POSTHOG_HOST)
    print("PostHog client initialized for backend tracking.")
else:
    print("PostHog API key or host not found. Backend event tracking is disabled.")

def capture_event(user_id: str, event_name: str, properties: dict = None):
    """
    Captures a backend event in PostHog if the client is initialized.
    """
    if posthog_client:
        posthog_client.capture(
            distinct_id=user_id,
            event=event_name,
            properties=properties
        )