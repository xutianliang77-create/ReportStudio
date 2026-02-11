from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class RunRequest:
    file: str
    prompt: str
    out_dir: str
    formats: list[str]
    topn: int = 10
    grain: str = "month"
    time_range: str | None = None


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    name: str
    kind: Literal["date", "number", "dimension", "unknown"]


@dataclass(frozen=True, slots=True)
class Artifact:
    format: Literal["xlsx", "pdf", "pptx"]
    path: str


@dataclass(frozen=True, slots=True)
class Spec:
    time_range: str
    topn: int
    date_column: str | None
    number_columns: list[str]
    dimension_columns: list[str]


@dataclass(frozen=True, slots=True)
class Summary:
    highlights: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Tables:
    trend: list[dict[str, Any]] = field(default_factory=list)
    breakdowns: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RunResult:
    artifacts: list[Artifact]
    summary: Summary
    spec: Spec
    warnings: list[str]
    tables: Tables = field(default_factory=Tables)
    meta: dict[str, Any] = field(default_factory=dict)
