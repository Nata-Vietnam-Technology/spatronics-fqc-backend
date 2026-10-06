import pytest
from pydantic import ValidationError

from app.schemas.common import BoundingBoxRegion, PolygonRegion
from app.schemas.inspection import InspectionPoint, InspectionSummary
from app.schemas.review import ReviewRequest
from app.schemas.shift import ShiftHistorySummary


def test_bbox_region_uses_tagged_flat_contract_shape():
    region = BoundingBoxRegion.model_validate(
        {
            "kind": "bbox",
            "view_id": "top",
            "x": 0.42,
            "y": 0.31,
            "width": 0.08,
            "height": 0.05,
        }
    )

    assert region.kind == "bbox"


def test_polygon_region_uses_tagged_contract_shape():
    region = PolygonRegion.model_validate(
        {
            "kind": "polygon",
            "view_id": "top",
            "points": [{"x": 0.2, "y": 0.3}, {"x": 0.4, "y": 0.5}],
        }
    )

    assert region.kind == "polygon"


@pytest.mark.parametrize(
    "region",
    [
        {
            "kind": "bbox",
            "view_id": "top",
            "x": 0.1,
            "y": 0.2,
            "width": 0.3,
            "height": 0.4,
        },
        {
            "kind": "polygon",
            "view_id": "top",
            "points": [{"x": 0.1, "y": 0.2}, {"x": 0.3, "y": 0.4}],
        },
    ],
)
def test_inspection_point_parses_tagged_region_union(region):
    point = InspectionPoint.model_validate(
        {
            "id": "IP-001",
            "target_ref": "R12",
            "target_type": "component",
            "machine_result": "PASS",
            "current_result": "PASS",
            "requires_review": False,
            "region": region,
            "checks": [],
            "review": None,
        }
    )

    assert point.region is not None
    assert point.region.kind == region["kind"]


def test_bbox_coordinates_must_be_normalized():
    with pytest.raises(ValidationError):
        BoundingBoxRegion.model_validate(
            {
                "kind": "bbox",
                "view_id": "top",
                "x": 1.1,
                "y": 0.2,
                "width": 0.1,
                "height": 0.1,
            }
        )


def test_review_request_accepts_fail_not_defect():
    request = ReviewRequest.model_validate({"decision": "FAIL"})

    assert request.decision.value == "FAIL"
    with pytest.raises(ValidationError):
        ReviewRequest.model_validate({"decision": "DEFECT"})


def test_summary_pass_field_keeps_public_json_name():
    summary = InspectionSummary.model_validate(
        {
            "total_points": 1,
            "pass": 1,
            "review": 0,
            "fail": 0,
            "reviewed": 0,
            "unresolved_reviews": 0,
        }
    )

    assert summary.model_dump(by_alias=True)["pass"] == 1


def test_shift_summary_pass_field_keeps_public_json_name():
    summary = ShiftHistorySummary.model_validate(
        {"inspected": 1, "pass": 1, "fail": 0, "required_review": 0}
    )

    assert summary.model_dump(by_alias=True)["pass"] == 1