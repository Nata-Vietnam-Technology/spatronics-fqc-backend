# Defines rules for deciding whether inspection checks require review.
from collections.abc import Iterable

from app.domain.inspection.enums import InspectionResult

_SEVERITY = {
    InspectionResult.PASS: 0,
    InspectionResult.REVIEW: 1,
    InspectionResult.FAIL: 2,
}


def worst_result(results: Iterable[InspectionResult]) -> InspectionResult:
    values = tuple(results)
    if not values:
        raise ValueError("At least one inspection result is required")

    return max(values, key=_SEVERITY.__getitem__)
