"""Add full-text search tsvector columns and GIN indexes.

Revision ID: n4i5j6k7l8m9
Revises: m3h4i5j6k7l8
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "n4i5j6k7l8m9"
down_revision: str | None = "m3h4i5j6k7l8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Matters: search on title + decedent_name ---
    op.execute("""
        ALTER TABLE matters
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(decedent_name, '')), 'A')
        ) STORED;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_matters_search_vector
        ON matters USING GIN (search_vector);
    """)

    # --- Tasks: search on title + description ---
    op.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
        ) STORED;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tasks_search_vector
        ON tasks USING GIN (search_vector);
    """)

    # --- Assets: search on title + description + institution ---
    op.execute("""
        ALTER TABLE assets
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(institution, '')), 'B')
        ) STORED;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_assets_search_vector
        ON assets USING GIN (search_vector);
    """)

    # --- Documents: search on filename ---
    op.execute("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(filename, '')), 'A')
        ) STORED;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_search_vector
        ON documents USING GIN (search_vector);
    """)

    # --- Communications: search on subject + body ---
    op.execute("""
        ALTER TABLE communications
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(subject, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(body, '')), 'B')
        ) STORED;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_communications_search_vector
        ON communications USING GIN (search_vector);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_communications_search_vector;")
    op.execute("ALTER TABLE communications DROP COLUMN IF EXISTS search_vector;")
    op.execute("DROP INDEX IF EXISTS ix_documents_search_vector;")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS search_vector;")
    op.execute("DROP INDEX IF EXISTS ix_assets_search_vector;")
    op.execute("ALTER TABLE assets DROP COLUMN IF EXISTS search_vector;")
    op.execute("DROP INDEX IF EXISTS ix_tasks_search_vector;")
    op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS search_vector;")
    op.execute("DROP INDEX IF EXISTS ix_matters_search_vector;")
    op.execute("ALTER TABLE matters DROP COLUMN IF EXISTS search_vector;")
