# Defines the data models for inspections, views, points, checks, and reviews.
from datetime import datetime

from pydantic import Field

from app.domain.inspection.enums import (
    InspectionGroup,
    InspectionResult,
    InspectionTargetType,
    IssueType,
    ViewSide,
)
from app.schemas.common import APIModel, InspectionEvidence, InspectionRegion
from app.schemas.review import ReviewRecord


class InspectionView(APIModel):
    id: str
    label: str
    side: ViewSide
    current_image_url: str
    current_image_key: str | None = Field(default=None, exclude=True)
    golden_image_url: str
    width: int = Field(ge=0)
    height: int = Field(ge=0)


class InspectionCheck(APIModel):
    id: str
    group: InspectionGroup
    issue_type: IssueType | None
    result: InspectionResult
    evidence: InspectionEvidence


class InspectionPoint(APIModel):
    id: str
    target_ref: str
    target_type: InspectionTargetType
    machine_result: InspectionResult
    current_result: InspectionResult
    requires_review: bool
    region: InspectionRegion | None
    checks: list[InspectionCheck]
    review: ReviewRecord | None


class InspectionSummary(APIModel):
    total_points: int = Field(ge=0)
    pass_: int = Field(alias="pass", ge=0)
    review: int = Field(ge=0)
    fail: int = Field(ge=0)
    reviewed: int = Field(ge=0)
    unresolved_reviews: int = Field(ge=0)

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }


class Inspection(APIModel):
    id: str
    sku_code: str
    station_id: str
    shift_id: str
    started_at: datetime
    completed_at: datetime | None
    machine_result: InspectionResult
    current_result: InspectionResult
    views: list[InspectionView]
    points: list[InspectionPoint]
    summary: InspectionSummary

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }
