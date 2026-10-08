# Defines response models for shift history and its inspection summary.
from datetime import datetime

from pydantic import Field

from app.domain.inspection.enums import InspectionResult
from app.schemas.common import APIModel


class ShiftInfo(APIModel):
    id: str
    label: str


class ShiftHistorySummary(APIModel):
    inspected: int = Field(ge=0)
    pass_: int = Field(alias="pass", ge=0)
    fail: int = Field(ge=0)
    required_review: int = Field(ge=0)

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }


class ShiftHistoryItem(APIModel):
    id: str
    sku_code: str
    inspected_at: datetime
    result: InspectionResult
    required_review: bool
    reviewed_points: int = Field(ge=0)
    confirmed_defects: int = Field(ge=0)


class ShiftHistoryResponse(APIModel):
    shift: ShiftInfo
    summary: ShiftHistorySummary
    items: list[ShiftHistoryItem]
