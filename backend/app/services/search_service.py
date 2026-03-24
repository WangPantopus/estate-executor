"""Full-text search service — queries tsvector columns across entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, literal_column, text, union_all
from sqlalchemy.dialects.postgresql import TSVECTOR

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def search(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    query: str,
    entity_types: list[str] | None = None,
    matter_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search across matters, tasks, assets, documents, and communications.

    Uses PostgreSQL ts_query with websearch_to_tsquery for natural-language
    query parsing. Results are ranked by ts_rank_cd and grouped by entity type.

    Args:
        firm_id: Tenant scope — only search within this firm's data.
        query: User search string (natural language or keywords).
        entity_types: Optional filter to specific entity types.
        matter_id: Optional filter to a single matter.
        limit: Max results per entity type.

    Returns:
        List of result dicts with entity_type, id, matter_id, title,
        subtitle, snippet, rank, and url.
    """
    if not query or not query.strip():
        return []

    # websearch_to_tsquery handles natural language: "hello world" → 'hello' & 'world'
    tsquery = func.websearch_to_tsquery("english", query)

    allowed_types = {"matter", "task", "asset", "document", "communication"}
    if entity_types:
        search_types = set(entity_types) & allowed_types
    else:
        search_types = allowed_types

    subqueries = []

    # --- Matters ---
    if "matter" in search_types:
        matter_q = text("""
            SELECT
                'matter' AS entity_type,
                m.id::text AS entity_id,
                m.id::text AS matter_id,
                m.title AS title,
                m.decedent_name AS subtitle,
                ts_headline('english', coalesce(m.title, '') || ' ' || coalesce(m.decedent_name, ''),
                    websearch_to_tsquery('english', :query),
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
                ) AS snippet,
                ts_rank_cd(m.search_vector, websearch_to_tsquery('english', :query)) AS rank
            FROM matters m
            WHERE m.firm_id = :firm_id
              AND m.search_vector @@ websearch_to_tsquery('english', :query)
              AND (:matter_id IS NULL OR m.id = :matter_id)
            ORDER BY rank DESC
            LIMIT :per_type_limit
        """)
        subqueries.append(matter_q)

    # --- Tasks ---
    if "task" in search_types:
        task_q = text("""
            SELECT
                'task' AS entity_type,
                t.id::text AS entity_id,
                t.matter_id::text AS matter_id,
                t.title AS title,
                t.status::text AS subtitle,
                ts_headline('english', coalesce(t.title, '') || ' ' || coalesce(t.description, ''),
                    websearch_to_tsquery('english', :query),
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
                ) AS snippet,
                ts_rank_cd(t.search_vector, websearch_to_tsquery('english', :query)) AS rank
            FROM tasks t
            JOIN matters m ON m.id = t.matter_id
            WHERE m.firm_id = :firm_id
              AND t.search_vector @@ websearch_to_tsquery('english', :query)
              AND (:matter_id IS NULL OR t.matter_id = :matter_id)
            ORDER BY rank DESC
            LIMIT :per_type_limit
        """)
        subqueries.append(task_q)

    # --- Assets ---
    if "asset" in search_types:
        asset_q = text("""
            SELECT
                'asset' AS entity_type,
                a.id::text AS entity_id,
                a.matter_id::text AS matter_id,
                a.title AS title,
                a.institution AS subtitle,
                ts_headline('english', coalesce(a.title, '') || ' ' || coalesce(a.description, '') || ' ' || coalesce(a.institution, ''),
                    websearch_to_tsquery('english', :query),
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
                ) AS snippet,
                ts_rank_cd(a.search_vector, websearch_to_tsquery('english', :query)) AS rank
            FROM assets a
            JOIN matters m ON m.id = a.matter_id
            WHERE m.firm_id = :firm_id
              AND a.search_vector @@ websearch_to_tsquery('english', :query)
              AND (:matter_id IS NULL OR a.matter_id = :matter_id)
            ORDER BY rank DESC
            LIMIT :per_type_limit
        """)
        subqueries.append(asset_q)

    # --- Documents ---
    if "document" in search_types:
        doc_q = text("""
            SELECT
                'document' AS entity_type,
                d.id::text AS entity_id,
                d.matter_id::text AS matter_id,
                d.filename AS title,
                d.doc_type AS subtitle,
                ts_headline('english', coalesce(d.filename, ''),
                    websearch_to_tsquery('english', :query),
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
                ) AS snippet,
                ts_rank_cd(d.search_vector, websearch_to_tsquery('english', :query)) AS rank
            FROM documents d
            JOIN matters m ON m.id = d.matter_id
            WHERE m.firm_id = :firm_id
              AND d.search_vector @@ websearch_to_tsquery('english', :query)
              AND (:matter_id IS NULL OR d.matter_id = :matter_id)
            ORDER BY rank DESC
            LIMIT :per_type_limit
        """)
        subqueries.append(doc_q)

    # --- Communications ---
    if "communication" in search_types:
        comm_q = text("""
            SELECT
                'communication' AS entity_type,
                c.id::text AS entity_id,
                c.matter_id::text AS matter_id,
                coalesce(c.subject, 'Message') AS title,
                c.type::text AS subtitle,
                ts_headline('english', coalesce(c.subject, '') || ' ' || coalesce(c.body, ''),
                    websearch_to_tsquery('english', :query),
                    'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
                ) AS snippet,
                ts_rank_cd(c.search_vector, websearch_to_tsquery('english', :query)) AS rank
            FROM communications c
            JOIN matters m ON m.id = c.matter_id
            WHERE m.firm_id = :firm_id
              AND c.search_vector @@ websearch_to_tsquery('english', :query)
              AND (:matter_id IS NULL OR c.matter_id = :matter_id)
            ORDER BY rank DESC
            LIMIT :per_type_limit
        """)
        subqueries.append(comm_q)

    if not subqueries:
        return []

    # Execute each subquery and collect results
    params = {
        "firm_id": str(firm_id),
        "query": query,
        "matter_id": str(matter_id) if matter_id else None,
        "per_type_limit": limit,
    }

    results: list[dict[str, Any]] = []
    for sq in subqueries:
        rows = await db.execute(sq, params)
        for row in rows.mappings().all():
            results.append(dict(row))

    # Sort all results by rank descending
    results.sort(key=lambda r: r.get("rank", 0), reverse=True)

    return results
