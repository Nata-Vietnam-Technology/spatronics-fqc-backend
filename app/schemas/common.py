from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceValue(APIModel):
    label: str
    value: str | int | float
    unit: str | None = None


class InspectionEvidence(APIModel):
    expected: list[EvidenceValue]
    observed: list[EvidenceValue]
    difference: list[EvidenceValue] | None = None


NormalizedCoordinate = Annotated[float, Field(ge=0, le=1)]


class BoundingBoxRegion(APIModel):
    kind: Literal["bbox"]
    view_id: str
    x: NormalizedCoordinate
    y: NormalizedCoordinate
    width: NormalizedCoordinate
    height: NormalizedCoordinate


class NormalizedPoint(APIModel):
    x: NormalizedCoordinate
    y: NormalizedCoordinate


class PolygonRegion(APIModel):
    kind: Literal["polygon"]
    view_id: str
    points: list[NormalizedPoint]


InspectionRegion = Annotated[
    BoundingBoxRegion | PolygonRegion,
    Field(discriminator="kind"),
]