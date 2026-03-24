"""Monitoring endpoints for metrics, alerts, and business dashboards.

- GET /monitoring/metrics     — Request latency percentiles and error rates
- GET /monitoring/alerts      — Currently firing alert rules
- GET /monitoring/business    — Business metrics (matters, tasks, AI usage)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text

from app.core.dependencies import get_db
from app.core.security import get_current_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.auth import CurrentUser

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/monitoring/metrics")
async def get_metrics(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return request performance metrics with latency percentiles."""
    from app.core.metrics import metrics_collector

    return metrics_collector.get_summary()


@router.get("/monitoring/alerts")
async def get_alerts(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Evaluate all alert rules and return any that are firing."""
    from app.services.alerting_service import evaluate_alerts

    alerts = await evaluate_alerts()
    return {
        "status": "ok" if not alerts else "alerting",
        "alert_count": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.get("/monitoring/business")
async def get_business_metrics(
    db: AsyncSession = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Business metrics dashboard: active matters, task completion, AI usage.

    Returns aggregate counts useful for operational dashboards.
    """
    metrics: dict[str, Any] = {}

    # ── Active matters by status ───────────────────────────────────────
    try:
        from app.models.matters import Matter

        matter_rows = await db.execute(
            select(Matter.status, func.count(Matter.id))
            .where(Matter.deleted_at.is_(None))
            .group_by(Matter.status)
        )
        matter_counts = {
            str(row[0].value) if hasattr(row[0], "value") else str(row[0]): row[1]
            for row in matter_rows
        }
        metrics["matters"] = {
            "by_status": matter_counts,
            "total": sum(matter_counts.values()),
        }
    except Exception as exc:
        logger.warning("business_metric_failed", extra={"metric": "matters", "error": str(exc)})
        metrics["matters"] = {"error": str(exc)}

    # ── Task completion rate ───────────────────────────────────────────
    try:
        from app.models.tasks import Task

        task_rows = await db.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        task_counts = {
            str(row[0].value) if hasattr(row[0], "value") else str(row[0]): row[1]
            for row in task_rows
        }
        total_tasks = sum(task_counts.values())
        completed = task_counts.get("complete", 0) + task_counts.get("completed", 0)
        metrics["tasks"] = {
            "by_status": task_counts,
            "total": total_tasks,
            "completed": completed,
            "completion_rate": round(completed / total_tasks, 4) if total_tasks > 0 else 0.0,
        }
    except Exception as exc:
        logger.warning("business_metric_failed", extra={"metric": "tasks", "error": str(exc)})
        metrics["tasks"] = {"error": str(exc)}

    # ── AI usage (last 30 days) ────────────────────────────────────────
    try:
        from app.models.ai_usage_logs import AIUsageLog

        ai_row = await db.execute(
            select(
                func.count(AIUsageLog.id),
                func.sum(AIUsageLog.input_tokens),
                func.sum(AIUsageLog.output_tokens),
            ).where(
                AIUsageLog.created_at >= text("NOW() - INTERVAL '30 days'")
            )
        )
        row = ai_row.one()
        metrics["ai_usage_30d"] = {
            "total_requests": row[0] or 0,
            "total_input_tokens": row[1] or 0,
            "total_output_tokens": row[2] or 0,
        }
    except Exception as exc:
        logger.warning("business_metric_failed", extra={"metric": "ai_usage", "error": str(exc)})
        metrics["ai_usage_30d"] = {"error": str(exc)}

    # ── Overdue deadlines ──────────────────────────────────────────────
    try:
        from app.models.deadlines import Deadline

        overdue_row = await db.execute(
            select(func.count(Deadline.id)).where(
                Deadline.due_date < text("NOW()"),
                Deadline.completed_at.is_(None),
            )
        )
        metrics["overdue_deadlines"] = overdue_row.scalar() or 0
    except Exception as exc:
        logger.warning("business_metric_failed", extra={"metric": "deadlines", "error": str(exc)})
        metrics["overdue_deadlines"] = {"error": str(exc)}

    return metrics
