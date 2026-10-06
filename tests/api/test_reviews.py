import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.infrastructure.persistence.in_memory_inspection_repository import (
    InMemoryInspectionRepository,
)
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(repository=InMemoryInspectionRepository()))


def _png_bytes() -> bytes:
    image = Image.new("RGB", (8, 6), color=(40, 80, 120))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_inspection(client: TestClient) -> dict:
    view_ids = ["top", "angle-1", "bottom"]
    response = client.post(
        "/api/v1/inspections",
        data={
            "sku_code": "FQC-DEMO-01",
            "station_id": "FQC-01",
            "shift_id": "SHIFT-A-2026-10-02",
            "view_ids": json.dumps(view_ids),
        },
        files=[
            ("images", (f"{view_id}.png", _png_bytes(), "image/png"))
            for view_id in view_ids
        ],
    )
    assert response.status_code == 200
    return response.json()


def test_pass_review_preserves_machine_result_and_recalculates_summary(
    client: TestClient,
):
    inspection = _create_inspection(client)
    response = client.put(
        f"/api/v1/inspections/{inspection['id']}/points/IP-001/review",
        json={"decision": "PASS", "note": "Accepted after visual check"},
    )

    assert response.status_code == 200
    updated = response.json()
    point = next(point for point in updated["points"] if point["id"] == "IP-001")
    assert point["machine_result"] == "REVIEW"
    assert point["current_result"] == "PASS"
    assert point["review"]["decision"] == "PASS"
    assert point["review"]["note"] == "Accepted after visual check"
    assert point["review"]["reviewed_at"]
    assert updated["machine_result"] == inspection["machine_result"]
    assert updated["summary"] == {
        "total_points": 4,
        "pass": 2,
        "review": 1,
        "fail": 1,
        "reviewed": 1,
        "unresolved_reviews": 2,
    }
    assert updated["current_result"] == "FAIL"


def test_third_review_required_point_can_be_marked_pass(client: TestClient):
    inspection = _create_inspection(client)
    response = client.put(
        f"/api/v1/inspections/{inspection['id']}/points/IP-003/review",
        json={"decision": "PASS"},
    )

    assert response.status_code == 200
    point = next(point for point in response.json()["points"] if point["id"] == "IP-003")
    assert point["requires_review"] is True
    assert point["machine_result"] == "FAIL"
    assert point["current_result"] == "PASS"
    assert point["review"]["decision"] == "PASS"


def test_fail_review_overrides_passed_point_without_changing_machine_result(
    client: TestClient,
):
    inspection = _create_inspection(client)
    response = client.put(
        f"/api/v1/inspections/{inspection['id']}/points/IP-002/review",
        json={"decision": "FAIL"},
    )

    assert response.status_code == 200
    point = next(point for point in response.json()["points"] if point["id"] == "IP-002")
    assert point["machine_result"] == "PASS"
    assert point["current_result"] == "FAIL"
    assert point["review"]["note"] is None


def test_latest_review_replaces_previous_review(client: TestClient):
    inspection = _create_inspection(client)
    path = f"/api/v1/inspections/{inspection['id']}/points/IP-002/review"
    first = client.put(path, json={"decision": "FAIL"})
    latest = client.put(path, json={"decision": "PASS", "note": None})

    assert first.status_code == 200
    assert latest.status_code == 200
    updated = latest.json()
    point = next(point for point in updated["points"] if point["id"] == "IP-002")
    assert point["machine_result"] == "PASS"
    assert point["current_result"] == "PASS"
    assert point["review"]["decision"] == "PASS"
    assert updated["summary"]["reviewed"] == 1


def test_review_returns_not_found_for_missing_inspection(client: TestClient):
    response = client.put(
        "/api/v1/inspections/INS-MISSING/points/IP-001/review",
        json={"decision": "PASS"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Inspection not found"}


def test_review_returns_not_found_for_missing_point(client: TestClient):
    inspection = _create_inspection(client)
    response = client.put(
        f"/api/v1/inspections/{inspection['id']}/points/IP-MISSING/review",
        json={"decision": "PASS"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Inspection point not found"}


def test_review_rejects_legacy_defect_decision(client: TestClient):
    inspection = _create_inspection(client)
    response = client.put(
        f"/api/v1/inspections/{inspection['id']}/points/IP-001/review",
        json={"decision": "DEFECT"},
    )

    assert response.status_code == 422