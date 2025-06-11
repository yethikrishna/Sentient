# path: src/server/workers/utils/kafka_producer_test.py
import asyncio
import json
import uuid
import os
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

# --- Configuration ---
# Load .env file from the main server directory to get Kafka settings
try:
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
except Exception as e:
    print(f"Warning: Could not load .env file. Using default values. Error: {e}")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
CONTEXT_EVENTS_TOPIC = os.getenv("CONTEXT_EVENTS_TOPIC", "gmail_polling_results")
USER_ID_TO_TEST = "google-oauth2|100870952531954264970" # Use a valid user_id from your system

# --- Sample Email Events ---
# A list of sample email data structures that mimic what the Gmail poller would produce.
# Each dictionary in this list will be sent as a separate event inside a single Kafka message batch.
SAMPLE_EMAIL_EVENTS = [
    {
        "subject": "Project Phoenix - Weekly Sync",
        "body": """
Hi Team,

Just a reminder that our weekly sync for Project Phoenix is scheduled for tomorrow at 10:00 AM.
Please come prepared to discuss your progress on the Q3 roadmap deliverables.

Also, can someone please follow up with the marketing team about the new campaign assets?

David, I've reviewed your latest proposal and it looks great. Let's touch base after the meeting.

Thanks,
Sarah
""",
    },
    {
        "subject": "Your flight confirmation to SFO",
        "body": """
Dear Kabeer,

Your flight UA246 to San Francisco is confirmed for this Friday, June 14th, departing at 8:00 AM.

Remember to check in 24 hours before your flight.

Best,
United Airlines
""",
    },
    {
        "subject": "Re: Dinner Plans",
        "body": """
Hey, sounds good! Let's meet at The Italian Place on Saturday at 7 PM. My number is 555-123-4567 in case you need it.

P.S. My partner, Alex, will be joining us.
""",
    },
    {
        "subject": "Action Required: Your invoice #INV-003 is due",
        "body": """
Your invoice for the cloud hosting services is due next week. The total amount is $45.50.

Please ensure payment is made by the 20th to avoid any service interruptions.
""",
    }
]


async def produce_test_events():
    """Connects to Kafka and sends the sample email events."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
    )

    await producer.start()
    print(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")

    try:
        # Format the sample data into the structure the extractor expects
        # The extractor service expects a list of event dictionaries in the `msg.value`
        batch_to_send = []
        for email_data in SAMPLE_EMAIL_EVENTS:
            event_id = f"test-event-{uuid.uuid4()}"
            event = {
                "user_id": USER_ID_TO_TEST,
                "service_name": "gmail_test_producer",
                "event_type": "new_email",
                "event_id": event_id,
                "data": email_data,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }
            batch_to_send.append(event)
            print(f"Prepared event '{email_data['subject']}' with ID {event_id}")

        # Send the entire batch as a single message to the topic
        await producer.send_and_wait(CONTEXT_EVENTS_TOPIC, value=batch_to_send)
        print(f"\nSuccessfully sent a batch of {len(batch_to_send)} events to the '{CONTEXT_EVENTS_TOPIC}' topic.")
        print("Your Extractor worker should now be processing these events.")

    except Exception as e:
        print(f"An error occurred while sending messages: {e}")
    finally:
        await producer.stop()
        print("Producer stopped.")


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    print("--- Kafka Test Event Producer ---")
    asyncio.run(produce_test_events())