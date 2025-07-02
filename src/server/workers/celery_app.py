import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
import ssl # Import the ssl module


# Load environment variables from the parent 'server' directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)



CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery_app = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        'workers.executor.tasks',
        'workers.tasks'
    ]
)

# SSL configuration for Redis (Upstash requires this).
# Using ssl.CERT_NONE is required for rediss:// URLs in Celery/Kombu.
# redis_ssl_options = {
#     'ssl_cert_reqs': ssl.CERT_NONE
# }
# celery_app.conf.broker_use_ssl = redis_ssl_options # For the broker connection
# celery_app.conf.redis_backend_use_ssl = redis_ssl_options

celery_app.conf.update(
    task_track_started=True,
    beat_schedule = {
        'run-due-tasks-every-minute': {
            'task': 'run_due_tasks',
            'schedule': 300.0,
        },
        'schedule-polling-tasks-every-minute': {
            'task': 'schedule_all_polling',
            'schedule': 3600.0,
        },
    }
)

if __name__ == '__main__':
    celery_app.start()