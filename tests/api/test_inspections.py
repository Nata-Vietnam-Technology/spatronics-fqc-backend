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


def _files(view_ids: list[str]) -> list[tuple[str, tuple[str, bytes, str]]]:
    content = _png_bytes()
    return [
        ("images", (f"{view_id}.png", content, "image/png"))
        for view_id in view_ids
    ]


def _form(
    view_ids: list[str],
    shift_id: str = "SHIFT-A-2026-10-02",
) -> dict[str, str]:
    import json

    return {
        "sku_code": "FQC-DEMO-01",
        "station_id": "FQC-01",
        "shift_id": shift_id,
        "view_ids": json.dumps(view_ids),
    }


def test_create_then_get_returns_full_contract_inspection(client: TestClient):
    view_ids = ["top", "angle-1", "bottom"]
    created = client.post(
        "/api/v1/inspections",
        data=_form(view_ids),
        files=_files(view_ids),
    )

    assert created.status_code == 200
    inspection = created.json()
    assert inspection["id"].startswith("INS-")
    assert [view["id"] for view in inspection["views"]] == view_ids
    assert all(view["width"] == 8 and view["height"] == 6 for view in inspection["views"])
    assert inspection["views"][0]["current_image_url"].startswith("data:image/png;base64,")
    assert inspection["views"][0]["golden_image_url"] == "/mock/pcb/golden-top.jpg"
    assert len(inspection["points"]) == 4
    assert sum(point["requires_review"] for point in inspection["points"]) == 3
    assert inspection["points"][0]["machine_result"] == "REVIEW"
    assert inspection["points"][2]["machine_result"] == "FAIL"
    assert inspection["machine_result"] == "FAIL"
    assert inspection["summary"] == {
        "total_points": 4,
        "pass": 1,
        "review": 2,
        "fail": 1,
        "reviewed": 0,
        "unresolved_reviews": 3,
    }
    assert "status" not in inspection

    fetched = client.get(f"/api/v1/inspections/{inspection['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == inspection


def test_create_supports_more_than_three_views(client: TestClient):
    view_ids = ["top", "angle-1", "bottom", "auxiliary-1"]

    response = client.post(
        "/api/v1/inspections",
        data=_form(view_ids),
        files=_files(view_ids),
    )

    assert response.status_code == 200
    assert [view["id"] for view in response.json()["views"]] == view_ids


def test_create_accepts_swagger_serialized_view_ids(client: TestClient):
    form = _form(["top", "angle-1", "bottom"])
    form["view_ids"] = "top,angle-1,bottom"

    response = client.post(
        "/api/v1/inspections",
        data=form,
        files=_files(["top", "angle-1", "bottom"]),
    )

    assert response.status_code == 200
    assert [view["id"] for view in response.json()["views"]] == [
        "top",
        "angle-1",
        "bottom",
    ]


@pytest.mark.parametrize(
    ("view_ids", "image_ids", "expected_detail"),
    [
        (["top", "bottom"], ["top", "bottom"], "At least three views are required"),
        (["top", "angle-1", "bottom"], ["top", "bottom"], "Each view_id must have exactly one image"),
        (["top", "top", "bottom"], ["top", "top", "bottom"], "view_ids must be unique"),
    ],
)
def test_create_rejects_invalid_view_image_mapping(
    client: TestClient,
    view_ids: list[str],
    image_ids: list[str],
    expected_detail: str,
):
    response = client.post(
        "/api/v1/inspections",
        data=_form(view_ids),
        files=_files(image_ids),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail


def test_create_rejects_invalid_view_ids_json(client: TestClient):
    form = _form(["top", "angle-1", "bottom"])
    form["view_ids"] = "not-json"

    response = client.post(
        "/api/v1/inspections",
        data=form,
        files=_files(["top", "angle-1", "bottom"]),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "view_ids must be a JSON array of strings"


def test_get_missing_inspection_returns_contract_404(client: TestClient):
    response = client.get("/api/v1/inspections/INS-MISSING")

    assert response.status_code == 404
    assert response.json() == {"detail": "Inspection not found"}


def test_create_rejects_non_image_upload(client: TestClient):
    view_ids = ["top", "angle-1", "bottom"]
    files = [
        ("images", (f"{view_id}.png", b"not-an-image", "image/png"))
        for view_id in view_ids
    ]

    response = client.post(
        "/api/v1/inspections",
        data=_form(view_ids),
        files=files,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Uploaded file is not a valid supported image"