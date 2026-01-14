"""Celery application configuration for YouTopia Mind agent tasks"""

import os
from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "youtopia_agents",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes

    # Reliability
    task_acks_late=True,  # Acknowledge after task completes (enables retry on crash)
    worker_prefetch_multiplier=1,  # Fair distribution across workers

    # Results
    result_expires=3600,  # Results expire after 1 hour
)

# Beat schedule - periodic tasks
celery_app.conf.beat_schedule = {
    "observe-and-classify-all-clones": {
        "task": "src.workers.tasks.observe_all_clones",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours at :00
        "options": {"queue": "default"},
    },
}

# Task routing (optional, for future scaling)
celery_app.conf.task_routes = {
    "src.workers.tasks.observe_*": {"queue": "default"},
    "src.workers.tasks.classify_*": {"queue": "default"},
}
