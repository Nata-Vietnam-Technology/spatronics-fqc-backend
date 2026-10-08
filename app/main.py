# Creates the FastAPI app, wires dependencies, and registers API routes.
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.images import router as images_router
from app.api.v1.inspections import router as inspections_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.shifts import router as shifts_router
from app.infrastructure.persistence.sqlalchemy_inspection_repository import (
    SqlAlchemyInspectionRepository,
)
from app.infrastructure.storage.data_uri_image_storage import DataUriImageStorage
from app.infrastructure.storage.interfaces import ImageStorage
from app.infrastructure.storage.local_file_image_storage import LocalFileImageStorage
from app.infrastructure.vision.mock_inspection_engine import MockInspectionEngine
from app.repositories.inspection_repository import InspectionRepository
from app.services.inspection_service import InspectionService
from app.services.review_service import ReviewService
from app.services.shift_service import ShiftService

DEFAULT_DATABASE_URL = "postgresql+psycopg://fqc:fqc_dev_only@localhost:5433/fqc"


def create_app(
    repository: InspectionRepository | None = None,
    image_storage: ImageStorage | None = None,
) -> FastAPI:
    application = FastAPI(
        title="FQC Inspection API",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    database_url = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
    if repository is None:
        repository = SqlAlchemyInspectionRepository.from_url(database_url)
    if image_storage is None:
        image_storage = (
            LocalFileImageStorage.from_environment()
            if isinstance(repository, SqlAlchemyInspectionRepository)
            else DataUriImageStorage()
        )
    application.state.inspection_service = InspectionService(
        repository=repository,
        image_storage=image_storage,
        inspection_engine=MockInspectionEngine(),
    )
    application.state.image_storage = image_storage
    application.state.review_service = ReviewService(repository)
    application.state.shift_service = ShiftService(repository)
    application.include_router(inspections_router)
    application.include_router(images_router)
    application.include_router(reviews_router)
    application.include_router(shifts_router)
    return application


app = create_app()
