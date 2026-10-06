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


def _create_inspection(client: TestClient, shift_id: str) -> dict:
    view_ids = ["top", "angle-1", "bottom"]
    response = client.post(
        "/api/v1/inspections",
        data={
            "sku_code": "FQC-DEMO-01",
            "station_id": "FQC-01",
            "shift_id": shift_id,
            "view_ids": json.dumps(view_ids),
        },
        files=[
            ("images", (f"{view_id}.png", _png_bytes(), "image/png"))
            for view_id in view_ids
        ],
    )
    assert response.status_code == 200
    return response.json()


def test_shift_history_scopes_items_and_applies_filters(client: TestClient):
    unreviewed = _create_inspection(client, "SHIFT-A-2026-10-02")
    reviewed = _create_inspection(client, "SHIFT-A-2026-10-02")
    _create_inspection(client, "SHIFT-B-2026-10-02")
    review_response = client.put(
        f"/api/v1/inspections/{reviewed['id']}/points/IP-003/review",
        json={"decision": "PASS"},
    )
    assert review_response.status_code == 200

    response = client.get("/api/v1/shifts/SHIFT-A-2026-10-02/inspections")
    assert response.status_code == 200
    history = response.json()
    assert history["shift"] == {"id": "SHIFT-A-2026-10-02", "label": "Shift A"}
    assert history["summary"] == {
        "inspected": 2,
        "pass": 0,
        "fail": 1,
        "required_review": 2,
    }
    assert {item["id"] for item in history["items"]} == {
        unreviewed["id"],
        reviewed["id"],
    }

    reviewed_item = next(item for item in history["items"] if item["id"] == reviewed["id"])
    assert reviewed_item == {
        "id": reviewed["id"],
        "sku_code": "FQC-DEMO-01",
        "inspected_at": reviewed["completed_at"],
        "result": "REVIEW",
        "required_review": True,
        "reviewed_points": 1,
        "confirmed_defects": 0,
    }

    filtered = client.get(
        "/api/v1/shifts/SHIFT-A-2026-10-02/inspections"
        "?result=REVIEW&reviewed=true"
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [reviewed["id"]]
    assert filtered.json()["summary"] == history["summary"]

    unreviewed_only = client.get(
        "/api/v1/shifts/SHIFT-A-2026-10-02/inspections?reviewed=false"
    )
    assert unreviewed_only.status_code == 200
    assert [item["id"] for item in unreviewed_only.json()["items"]] == [
        unreviewed["id"]
    ]


def test_shift_history_rejects_invalid_result_filter(client: TestClient):
    response = client.get(
        "/api/v1/shifts/SHIFT-A-2026-10-02/inspections?result=DEFECT"
    )

    assert response.status_code == 422