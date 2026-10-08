# Calculates results for inspection checks, points, and full inspections.
from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.inspection.enums import InspectionResult, ReviewDecision
from app.domain.inspection.rules import worst_result


@dataclass(frozen=True, slots=True)
class PointResults:
    machine_result: InspectionResult
    current_result: InspectionResult


def calculate_point_result(
    check_results: Iterable[InspectionResult],
    latest_review: ReviewDecision | None = None,
) -> PointResults:
    machine_result = worst_result(check_results)
    current_result = (
        InspectionResult(latest_review.value)
        if latest_review is not None
        else machine_result
    )
    return PointResults(
        machine_result=machine_result,
        current_result=current_result,
    )


def calculate_inspection_result(
    point_results: Iterable[InspectionResult],
) -> InspectionResult:
    return worst_result(point_results)
