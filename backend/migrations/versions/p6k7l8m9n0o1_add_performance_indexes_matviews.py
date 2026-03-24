"""Add performance indexes and materialized views for dashboard aggregation.

Revision ID: p6k7l8m9n0o1
Revises: o5j6k7l8m9n0
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p6k7l8m9n0o1"
down_revision: str | None = "o5j6k7l8m9n0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Additional indexes for dashboard query optimization ──────────────

    # Covering index for task status aggregation per matter (used by dashboard)
    op.create_index(
        "ix_tasks_matter_status_due_date",
        "tasks",
        ["matter_id", "status", "due_date"],
        if_not_exists=True,
    )

    # Index for task assignment lookups
    op.create_index(
        "ix_tasks_assigned_to_status",
        "tasks",
        ["assigned_to", "status"],
        if_not_exists=True,
    )

    # Partial index for active (non-terminal) tasks — speeds up overdue queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tasks_active_due_date
        ON tasks (matter_id, due_date)
        WHERE status NOT IN ('complete', 'waived', 'cancelled')
        """
    )

    # Index for asset valuation aggregation
    op.create_index(
        "ix_assets_matter_status_value",
        "assets",
        ["matter_id", "status", "current_estimated_value"],
        if_not_exists=True,
    )

    # Stakeholder lookup by user_id + matter_id (used in permission checks)
    op.create_index(
        "ix_stakeholders_user_matter",
        "stakeholders",
        ["user_id", "matter_id"],
        unique=True,
        if_not_exists=True,
    )

    # Communications: faster dispute flag lookups per matter
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_communications_dispute_flags
        ON communications (matter_id)
        WHERE type = 'dispute_flag'
        """
    )

    # Events: faster recent-events-per-matter query
    op.create_index(
        "ix_events_matter_created_desc",
        "events",
        [sa.text("matter_id"), sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # ── Materialized view: matter dashboard summary ─────────────────────
    # Pre-aggregates task & asset stats per matter for fast dashboard loads.
    # Refreshed concurrently by a periodic job or after batch mutations.
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_matter_dashboard_summary AS
        SELECT
            m.id AS matter_id,
            m.firm_id,
            m.status AS matter_status,
            m.phase AS matter_phase,
            -- Task aggregates
            COALESCE(t.total, 0) AS task_total,
            COALESCE(t.not_started, 0) AS task_not_started,
            COALESCE(t.in_progress, 0) AS task_in_progress,
            COALESCE(t.blocked, 0) AS task_blocked,
            COALESCE(t.complete, 0) AS task_complete,
            COALESCE(t.waived, 0) AS task_waived,
            COALESCE(t.overdue, 0) AS task_overdue,
            -- Asset aggregates
            COALESCE(a.total_count, 0) AS asset_total_count,
            a.total_value AS asset_total_value,
            -- Stakeholder count
            COALESCE(s.cnt, 0) AS stakeholder_count,
            -- Deadline: next upcoming
            d.next_due_date,
            -- Refresh timestamp
            NOW() AS refreshed_at
        FROM matters m
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE tk.status = 'not_started') AS not_started,
                COUNT(*) FILTER (WHERE tk.status = 'in_progress') AS in_progress,
                COUNT(*) FILTER (WHERE tk.status = 'blocked') AS blocked,
                COUNT(*) FILTER (WHERE tk.status = 'complete') AS complete,
                COUNT(*) FILTER (WHERE tk.status = 'waived') AS waived,
                COUNT(*) FILTER (
                    WHERE tk.due_date < CURRENT_DATE
                    AND tk.status NOT IN ('complete', 'waived', 'cancelled')
                ) AS overdue
            FROM tasks tk
            WHERE tk.matter_id = m.id
        ) t ON true
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) AS total_count,
                SUM(ast.current_estimated_value) AS total_value
            FROM assets ast
            WHERE ast.matter_id = m.id
        ) a ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt
            FROM stakeholders st
            WHERE st.matter_id = m.id
        ) s ON true
        LEFT JOIN LATERAL (
            SELECT MIN(dl.due_date) AS next_due_date
            FROM deadlines dl
            WHERE dl.matter_id = m.id
              AND dl.status = 'upcoming'
              AND dl.due_date >= CURRENT_DATE
        ) d ON true
        """
    )

    # Index on the materialized view for fast lookups
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_dashboard_matter_id
        ON mv_matter_dashboard_summary (matter_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mv_dashboard_firm_id
        ON mv_matter_dashboard_summary (firm_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_matter_dashboard_summary CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_communications_dispute_flags")
    op.execute("DROP INDEX IF EXISTS ix_tasks_active_due_date")
    op.execute("DROP INDEX IF EXISTS ix_events_matter_created_desc")
    op.drop_index("ix_tasks_matter_status_due_date", table_name="tasks", if_exists=True)
    op.drop_index("ix_tasks_assigned_to_status", table_name="tasks", if_exists=True)
    op.drop_index("ix_assets_matter_status_value", table_name="assets", if_exists=True)
    op.drop_index("ix_stakeholders_user_matter", table_name="stakeholders", if_exists=True)
