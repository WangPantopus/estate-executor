"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "estate_executor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-deadlines-hourly": {
            "task": "app.workers.tasks.check_deadlines",
            "schedule": 3600.0,  # every hour
        },
    },
)

# Auto-discover tasks in app.workers.tasks
celery_app.autodiscover_tasks(["app.workers"])
