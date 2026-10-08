# Defines API endpoints for submitting inspection review decisions.
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.inspection import Inspection
from app.schemas.review import ReviewRequest
from app.application.services.review_service import (
    InspectionNotFoundError,
    InspectionPointNotFoundError,
    ReviewService,
)

router = APIRouter(prefix="/api/v1/inspections", tags=["reviews"])


def get_review_service(request: Request) -> ReviewService:
    return request.app.state.review_service


@router.put("/{inspection_id}/points/{point_id}/review", response_model=Inspection)
def review_point(
    inspection_id: str,
    point_id: str,
    review_request: ReviewRequest,
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> Inspection:
    try:
        return service.review_point(
            inspection_id=inspection_id,
            point_id=point_id,
            request=review_request,
        )
    except InspectionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Inspection not found") from error
    except InspectionPointNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Inspection point not found",
        ) from error
