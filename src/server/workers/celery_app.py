# workers/celery_app.py (or wherever this file is)

import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load .env file for 'dev' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
if ENVIRONMENT == 'dev':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')

if not CELERY_BROKER_URL or not CELERY_RESULT_BACKEND:
    raise ValueError("CELERY_BROKER_URL and CELERY_RESULT_BACKEND must be set in the environment or .env file")

celery_app = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        'workers.executor.tasks',
        'workers.tasks'
    ]
)

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