# Defines API endpoints for retrieving inspection history for a shift.
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.domain.inspection.enums import InspectionResult
from app.schemas.shift import ShiftHistoryResponse
from app.services.shift_service import ShiftService

router = APIRouter(prefix="/api/v1/shifts", tags=["shifts"])


def get_shift_service(request: Request) -> ShiftService:
    return request.app.state.shift_service


@router.get("/{shift_id}/inspections", response_model=ShiftHistoryResponse)
def get_shift_inspections(
    shift_id: str,
    service: Annotated[ShiftService, Depends(get_shift_service)],
    result: InspectionResult | None = None,
    reviewed: bool | None = None,
) -> ShiftHistoryResponse:
    return service.get_inspections(
        shift_id=shift_id,
        result=result,
        reviewed=reviewed,
    )
