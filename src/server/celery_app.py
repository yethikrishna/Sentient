import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery_app = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        'server.workers.executor.tasks', 
        'server.workers.tasks'
    ]
)

celery_app.conf.update(
    task_track_started=True,
    beat_schedule = {
        'check-scheduled-tasks-every-minute': {
            'task': 'server.workers.tasks.check_scheduled_tasks',
            'schedule': 60.0,
        },
        'schedule-polling-tasks-every-minute': {
            'task': 'server.workers.tasks.schedule_all_polling',
            'schedule': 60.0,
        },
    }
)

if __name__ == '__main__':
    celery_app.start()