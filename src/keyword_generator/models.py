from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ParserType(str, Enum):
    generic = "generic"
    json_path = "json_path"
    html = "html"
    text = "text"
    csv = "csv"
    regex = "regex"


class ParserDefinition(BaseModel):
    type: ParserType
    expression: str | None = None
    attribute: str | None = None
    transforms: list[str] = Field(default_factory=lambda: ["strip"])


class RequestDefinition(BaseModel):
    method: str = "GET"
    url: str
    query: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=10, gt=0, le=120)

    @field_validator("method")
    @classmethod
    def get_only(cls, value: str) -> str:
        if value.upper() != "GET":
            raise ValueError("only GET requests are currently supported")
        return "GET"


class SourceDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    name: str
    enabled: bool = True
    request: RequestDefinition
    parser: ParserDefinition
    tags: list[str] = Field(default_factory=list)
    deprecated: bool = False


class SourceConfig(BaseModel):
    version: int = 1
    sources: list[SourceDefinition]

    @model_validator(mode="after")
    def unique_ids(self) -> "SourceConfig":
        ids = [source.id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("source IDs must be unique")
        return self


class PlannedRequest(BaseModel):
    request_id: str
    source_id: str
    seed: str
    url: str
    query: dict[str, str]
    headers: dict[str, str]
    timeout_seconds: float


class RawKeyword(BaseModel):
    phrase: str
    source_id: str
    seed: str
    request_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KeywordRecord(BaseModel):
    keyword_id: str
    phrase: str
    normalized_phrase: str
    display_phrase: str
    language: str | None = None
    country: str | None = None
    seed_terms: set[str] = Field(default_factory=set)
    expansions: set[str] = Field(default_factory=set)
    source_ids: set[str] = Field(default_factory=set)
    request_ids: set[str] = Field(default_factory=set)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    occurrences: int = 1
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    score_components: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
