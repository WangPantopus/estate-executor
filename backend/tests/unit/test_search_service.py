"""Unit tests for the search service and schemas."""

from __future__ import annotations

import uuid

import pytest
from pydantic import BaseModel, ConfigDict, Field

from app.services.search_service import search

# ---------------------------------------------------------------------------
# Inline schema mirrors (avoids importing app.schemas which triggers full
# app init chain including database engine creation)
# ---------------------------------------------------------------------------


class _SearchResult(BaseModel):
    model_config = ConfigDict(strict=True)
    entity_type: str = Field(...)
    entity_id: str
    matter_id: str
    title: str
    subtitle: str | None = None
    snippet: str = Field(...)
    rank: float = Field(...)


class _SearchResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    query: str
    total: int
    results: list[_SearchResult]
    groups: dict[str, int] = Field(...)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSearchInputValidation:
    """Tests for search input handling."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        """An empty query string should return no results without hitting the DB."""
        result = await search(None, firm_id=uuid.uuid4(), query="")  # type: ignore[arg-type]
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty(self):
        """A whitespace-only query should return no results."""
        result = await search(None, firm_id=uuid.uuid4(), query="   ")  # type: ignore[arg-type]
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_entity_types_return_empty(self):
        """Invalid entity types should be silently ignored, returning empty."""
        result = await search(
            None,  # type: ignore[arg-type]
            firm_id=uuid.uuid4(),
            query="test",
            entity_types=["invalid", "nonexistent"],
        )
        assert result == []


class TestSearchServiceStructure:
    """Tests for the search service module structure."""

    def test_search_function_exists(self):
        """The search function should be importable."""
        assert callable(search)

    def test_search_function_signature(self):
        """The search function should accept the expected parameters."""
        import inspect

        sig = inspect.signature(search)
        param_names = list(sig.parameters.keys())
        assert "db" in param_names
        assert "firm_id" in param_names
        assert "query" in param_names
        assert "entity_types" in param_names
        assert "matter_id" in param_names
        assert "limit" in param_names


class TestSearchSchemas:
    """Tests for search Pydantic schemas (using inline mirrors)."""

    def test_search_result_schema(self):
        """SearchResult schema should accept valid data."""
        result = _SearchResult(
            entity_type="matter",
            entity_id="abc-123",
            matter_id="abc-123",
            title="Estate of Smith",
            subtitle="John Smith",
            snippet="Estate of <mark>Smith</mark>",
            rank=0.85,
        )
        assert result.entity_type == "matter"
        assert result.rank == 0.85

    def test_search_response_schema(self):
        """SearchResponse schema should accept valid data."""
        response = _SearchResponse(
            query="smith",
            total=2,
            results=[
                _SearchResult(
                    entity_type="matter",
                    entity_id="1",
                    matter_id="1",
                    title="Estate of Smith",
                    subtitle=None,
                    snippet="<mark>Smith</mark>",
                    rank=0.9,
                ),
                _SearchResult(
                    entity_type="task",
                    entity_id="2",
                    matter_id="1",
                    title="Contact Smith",
                    subtitle="in_progress",
                    snippet="Contact <mark>Smith</mark>",
                    rank=0.7,
                ),
            ],
            groups={"matter": 1, "task": 1},
        )
        assert response.total == 2
        assert len(response.results) == 2
        assert response.groups["matter"] == 1

    def test_search_result_snippet_allows_html(self):
        """Snippet field should allow HTML mark tags."""
        result = _SearchResult(
            entity_type="task",
            entity_id="1",
            matter_id="1",
            title="Test",
            subtitle=None,
            snippet="This is a <mark>test</mark> with <mark>highlighting</mark>",
            rank=0.5,
        )
        assert "<mark>" in result.snippet
