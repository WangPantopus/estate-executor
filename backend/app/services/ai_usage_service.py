"""AI usage monitoring service — aggregates usage stats for firm dashboards."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.models.ai_usage_logs import AIUsageLog
from app.models.matters import Matter
from app.services.ai_rate_limiter import (
    FIRM_LIMIT_PER_HOUR,
    MATTER_LIMIT_PER_HOUR,
    get_usage,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_usage_stats(
    db: AsyncSession,
    *,
    firm_id: UUID,
    since: datetime | None = None,
) -> dict[str, Any]:
    """Get AI usage statistics for a firm.

    Returns:
        total_calls: Total API calls in period
        successful_calls: Successful calls
        failed_calls: Failed calls
        total_input_tokens: Sum of input tokens
        total_output_tokens: Sum of output tokens
        total_cost_usd: Sum of estimated cost
        by_operation: Breakdown by operation type
        by_matter: Breakdown by matter (top 20)
        rate_limit_status: Current rate limit usage
    """
    if since is None:
        # Default to current calendar month
        now = datetime.now(UTC)
        since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_filter = [
        AIUsageLog.firm_id == firm_id,
        AIUsageLog.created_at >= since,
    ]

    # Overall totals
    totals_result = await db.execute(
        select(
            func.count(AIUsageLog.id).label("total_calls"),
            func.count(AIUsageLog.id)
            .filter(AIUsageLog.status == "success")
            .label("successful_calls"),
            func.count(AIUsageLog.id).filter(AIUsageLog.status == "error").label("failed_calls"),
            func.coalesce(func.sum(AIUsageLog.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(AIUsageLog.output_tokens), 0).label("total_output_tokens"),
            func.coalesce(func.sum(AIUsageLog.cost_estimate_usd), 0.0).label("total_cost_usd"),
        ).where(*base_filter)
    )
    totals = totals_result.one()

    # By operation
    by_op_result = await db.execute(
        select(
            AIUsageLog.operation,
            func.count(AIUsageLog.id).label("calls"),
            func.coalesce(func.sum(AIUsageLog.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(AIUsageLog.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(AIUsageLog.cost_estimate_usd), 0.0).label("cost_usd"),
        )
        .where(*base_filter)
        .group_by(AIUsageLog.operation)
        .order_by(func.count(AIUsageLog.id).desc())
    )
    by_operation = [
        {
            "operation": row.operation,
            "calls": row.calls,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "cost_usd": round(float(row.cost_usd), 4),
        }
        for row in by_op_result.all()
    ]

    # By matter (top 20)
    by_matter_result = await db.execute(
        select(
            AIUsageLog.matter_id,
            func.count(AIUsageLog.id).label("calls"),
            func.coalesce(func.sum(AIUsageLog.cost_estimate_usd), 0.0).label("cost_usd"),
        )
        .where(*base_filter)
        .group_by(AIUsageLog.matter_id)
        .order_by(func.sum(AIUsageLog.cost_estimate_usd).desc())
        .limit(20)
    )
    matter_rows = by_matter_result.all()

    # Fetch matter titles
    matter_ids = [row.matter_id for row in matter_rows]
    matter_titles: dict[UUID, str] = {}
    if matter_ids:
        titles_result = await db.execute(
            select(Matter.id, Matter.title).where(Matter.id.in_(matter_ids))
        )
        matter_titles = {row[0]: row[1] for row in titles_result.all()}

    by_matter = [
        {
            "matter_id": str(row.matter_id),
            "matter_title": matter_titles.get(row.matter_id, "Unknown"),
            "calls": row.calls,
            "cost_usd": round(float(row.cost_usd), 4),
        }
        for row in matter_rows
    ]

    # Rate limit status
    rate_limit_usage = get_usage(firm_id=firm_id)

    return {
        "period_start": since.isoformat(),
        "total_calls": totals.total_calls,
        "successful_calls": totals.successful_calls,
        "failed_calls": totals.failed_calls,
        "total_input_tokens": totals.total_input_tokens,
        "total_output_tokens": totals.total_output_tokens,
        "total_cost_usd": round(float(totals.total_cost_usd), 4),
        "by_operation": by_operation,
        "by_matter": by_matter,
        "rate_limits": {
            "firm_limit_per_hour": FIRM_LIMIT_PER_HOUR,
            "matter_limit_per_hour": MATTER_LIMIT_PER_HOUR,
            "firm_calls_this_hour": rate_limit_usage.get("firm_calls_this_hour", 0),
        },
    }
