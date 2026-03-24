"""Database query analysis utilities.

Provides EXPLAIN ANALYZE helpers for profiling slow queries during
development and periodic performance reviews.

Usage in dev/staging only — not exposed in production API routes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Allowlist of materialized view names that may be refreshed.
# Prevents SQL injection via view_name parameter.
_ALLOWED_MATERIALIZED_VIEWS = frozenset({
    "mv_portfolio_task_stats",
    "mv_matter_summary",
    "mv_asset_summary",
    "mv_deadline_summary",
})


async def explain_analyze(
    db: AsyncSession,
    query_sql: str,
    params: dict[str, Any] | None = None,
    *,
    analyze: bool = True,
    buffers: bool = True,
    fmt: str = "TEXT",
) -> list[str]:
    """Run EXPLAIN (ANALYZE, BUFFERS) on a raw SQL query and return the plan.

    Args:
        db: Async database session.
        query_sql: The SQL query to analyze.
        params: Optional bind parameters.
        analyze: If True, actually execute the query (not just plan).
        buffers: If True, include buffer usage statistics.
        fmt: Output format — TEXT, JSON, YAML, or XML.

    Returns:
        List of plan lines (TEXT format) or serialized plan (JSON/YAML/XML).
    """
    if not (settings.is_development or settings.app_env == "staging"):
        raise RuntimeError(
            "explain_analyze is only available in development/staging environments"
        )
    if not query_sql or not query_sql.strip():
        raise ValueError("query_sql must not be empty")

    options = []
    if analyze:
        options.append("ANALYZE")
    if buffers:
        options.append("BUFFERS")
    options.append(f"FORMAT {fmt}")

    explain_sql = f"EXPLAIN ({', '.join(options)}) {query_sql}"
    result = await db.execute(text(explain_sql), params or {})
    rows = result.fetchall()
    return [row[0] for row in rows]


async def refresh_materialized_view(
    db: AsyncSession,
    view_name: str,
    *,
    concurrently: bool = True,
) -> None:
    """Refresh a materialized view.

    Uses CONCURRENTLY when possible (requires a unique index on the view)
    to avoid locking reads during refresh.
    """
    if view_name not in _ALLOWED_MATERIALIZED_VIEWS:
        raise ValueError(
            f"Unknown materialized view '{view_name}'. "
            f"Allowed views: {sorted(_ALLOWED_MATERIALIZED_VIEWS)}"
        )
    keyword = "CONCURRENTLY" if concurrently else ""
    try:
        await db.execute(text(f"REFRESH MATERIALIZED VIEW {keyword} {view_name}"))
        logger.info("Refreshed materialized view %s (concurrently=%s)", view_name, concurrently)
    except Exception:
        if concurrently:
            # Fall back to non-concurrent refresh (e.g., first refresh when view is empty)
            logger.warning(
                "Concurrent refresh of %s failed, falling back to blocking refresh",
                view_name,
            )
            await db.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))  # view_name already validated above
        else:
            raise


# ---------------------------------------------------------------------------
# Dashboard-specific queries with EXPLAIN guidance
# ---------------------------------------------------------------------------

# These are the key dashboard queries we want to keep optimized.
# The index recommendations in the migration should make these efficient:

DASHBOARD_QUERIES = {
    "task_summary": """
        -- Uses: ix_tasks_matter_status_due_date, ix_tasks_active_due_date
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'not_started') AS not_started,
            COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress,
            COUNT(*) FILTER (WHERE status = 'blocked') AS blocked,
            COUNT(*) FILTER (WHERE status = 'complete') AS complete,
            COUNT(*) FILTER (WHERE status = 'waived') AS waived,
            COUNT(*) FILTER (
                WHERE due_date < CURRENT_DATE
                AND status NOT IN ('complete', 'waived', 'cancelled')
            ) AS overdue
        FROM tasks
        WHERE matter_id = :matter_id
    """,
    "asset_summary": """
        -- Uses: ix_assets_matter_status_value
        SELECT
            COUNT(*) AS total_count,
            SUM(current_estimated_value) AS total_value
        FROM assets
        WHERE matter_id = :matter_id
    """,
    "upcoming_deadlines": """
        -- Uses: ix_deadlines_matter_id_due_date_upcoming (partial index)
        SELECT *
        FROM deadlines
        WHERE matter_id = :matter_id
          AND status = 'upcoming'
          AND due_date >= CURRENT_DATE
        ORDER BY due_date
        LIMIT 5
    """,
    "recent_events": """
        -- Uses: ix_events_matter_created_desc
        SELECT *
        FROM events
        WHERE matter_id = :matter_id
        ORDER BY created_at DESC
        LIMIT 10
    """,
    "portfolio_task_stats": """
        -- Uses: ix_tasks_matter_status_due_date
        SELECT
            matter_id,
            COUNT(*) AS total_count,
            COUNT(*) FILTER (WHERE status = 'complete') AS complete_count,
            COUNT(*) FILTER (
                WHERE status NOT IN ('complete', 'waived', 'cancelled')
            ) AS open_count,
            COUNT(*) FILTER (
                WHERE due_date < CURRENT_DATE
                AND due_date IS NOT NULL
                AND status NOT IN ('complete', 'waived', 'cancelled')
            ) AS overdue_count,
            MIN(updated_at) FILTER (WHERE status = 'blocked') AS oldest_blocked_at
        FROM tasks
        WHERE matter_id = ANY(:matter_ids)
        GROUP BY matter_id
    """,
}
