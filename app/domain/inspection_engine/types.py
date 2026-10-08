# Defines typed inputs and outputs exchanged with inspection engines.
from dataclasses import dataclass, field
from typing import Literal

from app.domain.inspection.enums import (
    InspectionGroup,
    InspectionResult,
    InspectionTargetType,
    IssueType,
)


@dataclass(frozen=True, slots=True)
class InspectionEngineInput:
    view_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EngineEvidenceValue:
    label: str
    value: str | int | float
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class EngineEvidence:
    expected: tuple[EngineEvidenceValue, ...]
    observed: tuple[EngineEvidenceValue, ...]
    difference: tuple[EngineEvidenceValue, ...] | None = None


@dataclass(frozen=True, slots=True)
class EngineCheck:
    id: str
    group: InspectionGroup
    issue_type: IssueType | None
    result: InspectionResult
    evidence: EngineEvidence


@dataclass(frozen=True, slots=True)
class EngineBoundingBox:
    kind: Literal["bbox"] = field(default="bbox", init=False)
    view_id: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class EnginePolygon:
    kind: Literal["polygon"] = field(default="polygon", init=False)
    view_id: str
    points: tuple[tuple[float, float], ...]


EngineRegion = EngineBoundingBox | EnginePolygon


@dataclass(frozen=True, slots=True)
class EnginePoint:
    id: str
    target_ref: str
    target_type: InspectionTargetType
    requires_review: bool
    region: EngineRegion | None
    checks: tuple[EngineCheck, ...]


@dataclass(frozen=True, slots=True)
class InspectionEngineOutput:
    points: tuple[EnginePoint, ...]
