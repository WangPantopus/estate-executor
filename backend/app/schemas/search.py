"""Search-related Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SearchResult(BaseModel):
    """A single search result."""

    model_config = ConfigDict(strict=True)

    entity_type: str = Field(..., description="Type: matter, task, asset, document, communication")
    entity_id: str
    matter_id: str
    title: str
    subtitle: str | None = None
    snippet: str = Field(..., description="HTML snippet with <mark> highlighting")
    rank: float = Field(..., description="Relevance score")


class SearchResponse(BaseModel):
    """Full search response grouped by entity type."""

    model_config = ConfigDict(strict=True)

    query: str
    total: int
    results: list[SearchResult]
    groups: dict[str, int] = Field(
        ..., description="Count of results per entity_type"
    )
