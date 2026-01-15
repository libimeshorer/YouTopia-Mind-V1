"""Celery application configuration for YouTopia Mind agent tasks"""

import logging
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)


def get_redis_url() -> str:
    """
    Get Redis URL from settings with fallback for local development.

    Uses late import to avoid circular dependencies and ensure
    settings are loaded with proper environment file handling.
    """
    try:
        from src.config.settings import settings
        if settings.redis_url:
            return settings.redis_url
    except Exception as e:
        logger.warning(f"Could not load settings, using default Redis URL: {e}")

    # Fallback for local development
    return "redis://localhost:6379/0"


# Get Redis URL using centralized settings
REDIS_URL = get_redis_url()

# TODO: Consider using separate Redis databases for broker and results backend
# to avoid potential key collisions in production:
#   broker: redis://host:6379/0
#   backend: redis://host:6379/1

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

    # Broker connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=10,  # 10 seconds connection timeout
    broker_pool_limit=10,  # Connection pool size
    broker_transport_options={
        "visibility_timeout": 43200,  # 12 hours - must be > longest task
    },

    # Worker settings
    worker_cancel_long_running_tasks_on_connection_loss=True,
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
