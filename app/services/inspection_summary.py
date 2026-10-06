from collections.abc import Sequence

from app.domain.inspection.enums import InspectionResult
from app.schemas.inspection import InspectionPoint, InspectionSummary


def summarize_points(points: Sequence[InspectionPoint]) -> InspectionSummary:
    return InspectionSummary(
        total_points=len(points),
        pass_=sum(point.current_result is InspectionResult.PASS for point in points),
        review=sum(point.current_result is InspectionResult.REVIEW for point in points),
        fail=sum(point.current_result is InspectionResult.FAIL for point in points),
        reviewed=sum(point.review is not None for point in points),
        unresolved_reviews=sum(
            point.requires_review and point.review is None for point in points
        ),
    )