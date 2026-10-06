import pytest

from app.domain.inspection.enums import InspectionResult, ReviewDecision
from app.domain.inspection.result import (
    PointResults,
    calculate_inspection_result,
    calculate_point_result,
)
from app.domain.inspection.rules import worst_result


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ([InspectionResult.PASS, InspectionResult.PASS], InspectionResult.PASS),
        ([InspectionResult.PASS, InspectionResult.REVIEW], InspectionResult.REVIEW),
        ([InspectionResult.REVIEW, InspectionResult.FAIL], InspectionResult.FAIL),
    ],
)
def test_worst_result_uses_contract_severity_order(results, expected):
    assert worst_result(results) is expected


def test_worst_result_requires_at_least_one_value():
    with pytest.raises(ValueError, match="At least one"):
        worst_result([])


def test_point_review_overrides_current_result_without_changing_machine_result():
    results = calculate_point_result(
        [InspectionResult.FAIL, InspectionResult.PASS],
        ReviewDecision.PASS,
    )

    assert results == PointResults(
        machine_result=InspectionResult.FAIL,
        current_result=InspectionResult.PASS,
    )


def test_fail_review_resolves_point_to_fail():
    results = calculate_point_result(
        [InspectionResult.PASS, InspectionResult.REVIEW],
        ReviewDecision.FAIL,
    )

    assert results.current_result is InspectionResult.FAIL
    assert results.machine_result is InspectionResult.REVIEW


def test_point_without_review_uses_worst_check_result():
    results = calculate_point_result(
        [InspectionResult.PASS, InspectionResult.REVIEW]
    )

    assert results.current_result is InspectionResult.REVIEW
    assert results.machine_result is InspectionResult.REVIEW


def test_inspection_result_uses_worst_point_result():
    assert calculate_inspection_result(
        [InspectionResult.PASS, InspectionResult.REVIEW]
    ) is InspectionResult.REVIEW