# Applies review decisions to inspection points and persists the updated inspection.
from datetime import datetime, timezone

from app.domain.inspection.enums import InspectionResult
from app.domain.inspection.result import calculate_inspection_result
from app.application.ports.inspection_repository import InspectionRepository
from app.schemas.inspection import Inspection
from app.schemas.review import ReviewRecord, ReviewRequest
from app.application.services.inspection_summary import summarize_points


class InspectionNotFoundError(LookupError):
    pass


class InspectionPointNotFoundError(LookupError):
    pass


class ReviewService:
    def __init__(self, repository: InspectionRepository) -> None:
        self._repository = repository

    def review_point(
        self,
        *,
        inspection_id: str,
        point_id: str,
        request: ReviewRequest,
    ) -> Inspection:
        inspection = self._repository.get_by_id(inspection_id)
        if inspection is None:
            raise InspectionNotFoundError

        point_index = next(
            (
                index
                for index, point in enumerate(inspection.points)
                if point.id == point_id
            ),
            None,
        )
        if point_index is None:
            raise InspectionPointNotFoundError

        reviewed_point = inspection.points[point_index].model_copy(
            update={
                "current_result": InspectionResult(request.decision.value),
                "review": ReviewRecord(
                    decision=request.decision,
                    note=request.note,
                    reviewed_at=datetime.now(timezone.utc),
                ),
            }
        )
        points = list(inspection.points)
        points[point_index] = reviewed_point
        updated_inspection = inspection.model_copy(
            update={
                "current_result": calculate_inspection_result(
                    point.current_result for point in points
                ),
                "points": points,
                "summary": summarize_points(points),
            }
        )
        self._repository.save(updated_inspection)
        return updated_inspection
