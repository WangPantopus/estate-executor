"""Search-related Pydantic schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchEntityType = Literal["matter", "task", "asset", "document", "communication"]


class SearchResult(BaseModel):
    """A single search result."""

    model_config = ConfigDict(from_attributes=True)

    entity_type: SearchEntityType
    entity_id: str
    matter_id: str
    title: str
    subtitle: str | None = None
    snippet: str = Field(..., description="HTML snippet with <mark> highlighting")
    rank: float = Field(..., description="Relevance score")


class SearchResponse(BaseModel):
    """Full search response grouped by entity type."""

    model_config = ConfigDict(from_attributes=True)

    query: str
    total: int
    results: list[SearchResult]
    groups: dict[str, int] = Field(
        ..., description="Count of results per entity_type"
    )
