"""Celery application configuration.

Broker/backend: Redis
Task routing: ai, notifications, documents, default queues
Beat schedule: check_deadlines (hourly), check_overdue_tasks (6h)
Retry policy: exponential backoff (60s, 300s, 900s), max 3 retries
Time limits: soft=300s, hard=600s (overridable per task)
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "estate_executor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.workers.ai_tasks.*": {"queue": "ai"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
        "app.workers.document_tasks.*": {"queue": "documents"},
    },
    task_default_queue="default",
    # Default retry policy — exponential backoff
    # NOTE: autoretry_for is NOT set globally because all tasks use explicit
    # self.retry() calls. Setting both would cause double-retries.
    task_default_retry_delay=60,
    task_annotations={
        "*": {
            "max_retries": 3,
            "retry_backoff": True,
            "retry_backoff_max": 900,
            "retry_jitter": True,
        }
    },
    # Time limits
    task_soft_time_limit=300,
    task_time_limit=600,
    # Late ack — ensures tasks aren't lost if worker crashes mid-execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Dead-letter: tasks that permanently fail are stored in result backend
    task_reject_on_worker_lost=True,
    task_store_errors_even_if_ignored=True,
    # Beat schedule
    beat_schedule={
        "check-deadlines-hourly": {
            "task": "app.workers.deadline_tasks.check_deadlines",
            "schedule": 3600.0,
        },
        "check-overdue-tasks-6h": {
            "task": "app.workers.deadline_tasks.check_overdue_tasks",
            "schedule": 21600.0,  # every 6 hours
        },
    },
)

# Auto-discover task modules
celery_app.autodiscover_tasks([
    "app.workers",
])
