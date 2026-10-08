# Checks SQLAlchemy inspection persistence, retrieval, and shift filtering.
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models import InspectionReviewRow, InspectionViewRow
from app.infrastructure.persistence.sqlalchemy_inspection_repository import (
    SqlAlchemyInspectionRepository,
)
from app.infrastructure.storage.local_file_image_storage import LocalFileImageStorage
from app.main import create_app


def _png_bytes() -> bytes:
    image = Image.new("RGB", (8, 6), color=(40, 80, 120))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_database_repository_round_trips_inspections_reviews_and_shift_history(
    tmp_path,
):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = SqlAlchemyInspectionRepository(
        session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        dialect_name="sqlite",
    )
    image_storage = LocalFileImageStorage(tmp_path / "private-images")
    client = TestClient(create_app(repository=repository, image_storage=image_storage))
    view_ids = ["top", "angle-1", "bottom"]
    files = [
        ("images", (f"{view_id}.png", _png_bytes(), "image/png"))
        for view_id in view_ids
    ]
    created_response = client.post(
        "/api/v1/inspections",
        data={
            "sku_code": "FQC-DEMO-01",
            "station_id": "FQC-01",
            "shift_id": "SHIFT-DB-TEST",
            "view_ids": '["top", "angle-1", "bottom"]',
        },
        files=files,
    )

    assert created_response.status_code == 200
    created = created_response.json()
    inspection_id = created["id"]
    assert inspection_id == "INS-00001"

    fetched = client.get(f"/api/v1/inspections/{inspection_id}")
    assert fetched.status_code == 200
    assert fetched.json() == created
    image_url = created["views"][0]["current_image_url"]
    assert image_url.startswith("/api/v1/images/inspections/INS-00001/views/")
    downloaded_image = client.get(image_url)
    assert downloaded_image.status_code == 200
    assert downloaded_image.content == _png_bytes()

    with sessionmaker(bind=engine)() as session:
        stored_key = session.scalar(select(InspectionViewRow.current_image_ref))
    assert stored_key.startswith("inspections/INS-00001/views/")
    assert not stored_key.startswith("data:")

    point_id = created["points"][0]["id"]
    review_path = f"/api/v1/inspections/{inspection_id}/points/{point_id}/review"
    first_review = client.put(review_path, json={"decision": "PASS", "note": "checked"})
    second_review = client.put(
        review_path, json={"decision": "FAIL", "note": "recheck"}
    )
    assert first_review.status_code == 200
    assert second_review.status_code == 200
    assert (
        second_review.json()["points"][0]["machine_result"]
        == created["points"][0]["machine_result"]
    )
    assert second_review.json()["points"][0]["review"]["decision"] == "FAIL"

    with sessionmaker(bind=engine)() as session:
        review_count = session.scalar(
            select(func.count()).select_from(InspectionReviewRow)
        )
    assert review_count == 2

    history = client.get("/api/v1/shifts/SHIFT-DB-TEST/inspections")
    assert history.status_code == 200
    assert [item["id"] for item in history.json()["items"]] == [inspection_id]
    assert client.get("/api/v1/shifts/OTHER/inspections").json()["items"] == []
    engine.dispose()
