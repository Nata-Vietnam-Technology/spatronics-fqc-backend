# Coordinates inspection creation, image storage, engine results, and persistence.
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.domain.inspection.enums import ViewSide
from app.domain.inspection.result import (
    calculate_inspection_result,
    calculate_point_result,
)
from app.domain.inspection_engine.interfaces import InspectionEngine
from app.domain.inspection_engine.types import (
    EngineBoundingBox,
    EngineCheck,
    EngineEvidenceValue,
    EnginePoint,
    EnginePolygon,
    InspectionEngineInput,
)
from app.infrastructure.storage.interfaces import ImageStorage
from app.repositories.inspection_repository import InspectionRepository
from app.schemas.common import EvidenceValue, InspectionEvidence
from app.schemas.inspection import (
    Inspection,
    InspectionCheck,
    InspectionPoint,
    InspectionView,
)
from app.services.inspection_summary import summarize_points


@dataclass(frozen=True, slots=True)
class UploadedImage:
    filename: str
    content: bytes


class InspectionInputError(ValueError):
    pass


class InspectionService:
    def __init__(
        self,
        *,
        repository: InspectionRepository,
        image_storage: ImageStorage,
        inspection_engine: InspectionEngine,
    ) -> None:
        self._repository = repository
        self._image_storage = image_storage
        self._inspection_engine = inspection_engine

    def create_inspection(
        self,
        *,
        sku_code: str,
        station_id: str,
        shift_id: str,
        view_ids_json: str,
        images: list[UploadedImage],
    ) -> Inspection:
        view_ids = _parse_view_ids(view_ids_json)
        self._validate_views(view_ids, images)

        inspection_id = self._repository.allocate_inspection_id()
        views: list[InspectionView] = []
        try:
            views = self._store_views(inspection_id, view_ids, images)
            engine_output = self._inspection_engine.inspect(
                InspectionEngineInput(view_ids=tuple(view_ids))
            )
            points = [
                self._build_point(engine_point) for engine_point in engine_output.points
            ]
            inspection = self._build_inspection(
                inspection_id=inspection_id,
                sku_code=sku_code,
                station_id=station_id,
                shift_id=shift_id,
                views=views,
                points=points,
            )
            self._repository.save(inspection)
        except Exception:
            self._delete_stored_images(views)
            raise
        return inspection

    @staticmethod
    def _validate_views(view_ids: list[str], images: list[UploadedImage]) -> None:
        if len(view_ids) < 3:
            raise InspectionInputError("At least three views are required")
        if len(view_ids) != len(images):
            raise InspectionInputError("Each view_id must have exactly one image")
        if len(set(view_ids)) != len(view_ids):
            raise InspectionInputError("view_ids must be unique")

    def _store_views(
        self,
        inspection_id: str,
        view_ids: list[str],
        images: list[UploadedImage],
    ) -> list[InspectionView]:
        views: list[InspectionView] = []
        try:
            for view_id, uploaded_image in zip(view_ids, images, strict=True):
                stored_image = self._image_storage.store(
                    inspection_id=inspection_id,
                    view_id=view_id,
                    filename=uploaded_image.filename,
                    content=uploaded_image.content,
                )
                views.append(
                    InspectionView(
                        id=view_id,
                        label=_view_label(view_id),
                        side=_view_side(view_id),
                        current_image_url=stored_image.url,
                        current_image_key=stored_image.key,
                        golden_image_url=_golden_image_url(view_id, stored_image.url),
                        width=stored_image.width,
                        height=stored_image.height,
                    )
                )
        except Exception:
            self._delete_stored_images(views)
            raise
        return views

    def _build_point(self, engine_point: EnginePoint) -> InspectionPoint:
        results = calculate_point_result(check.result for check in engine_point.checks)
        checks = [self._build_check(check) for check in engine_point.checks]
        return InspectionPoint(
            id=engine_point.id,
            target_ref=engine_point.target_ref,
            target_type=engine_point.target_type,
            machine_result=results.machine_result,
            current_result=results.current_result,
            requires_review=engine_point.requires_review,
            region=self._region_dict(engine_point.region),
            checks=checks,
            review=None,
        )

    @staticmethod
    def _build_check(check: EngineCheck) -> InspectionCheck:
        return InspectionCheck(
            id=check.id,
            group=check.group,
            issue_type=check.issue_type,
            result=check.result,
            evidence=InspectionEvidence(
                expected=[_evidence_value(value) for value in check.evidence.expected],
                observed=[_evidence_value(value) for value in check.evidence.observed],
                difference=(
                    [_evidence_value(value) for value in check.evidence.difference]
                    if check.evidence.difference is not None
                    else None
                ),
            ),
        )

    @staticmethod
    def _region_dict(
        region: EngineBoundingBox | EnginePolygon | None,
    ) -> dict[str, Any] | None:
        if isinstance(region, EngineBoundingBox):
            return {
                "kind": "bbox",
                "view_id": region.view_id,
                "x": region.x,
                "y": region.y,
                "width": region.width,
                "height": region.height,
            }
        if isinstance(region, EnginePolygon):
            return {
                "kind": "polygon",
                "view_id": region.view_id,
                "points": [{"x": x, "y": y} for x, y in region.points],
            }
        return None

    @staticmethod
    def _build_inspection(
        *,
        inspection_id: str,
        sku_code: str,
        station_id: str,
        shift_id: str,
        views: list[InspectionView],
        points: list[InspectionPoint],
    ) -> Inspection:
        timestamp = datetime.now(timezone.utc)
        return Inspection(
            id=inspection_id,
            sku_code=sku_code,
            station_id=station_id,
            shift_id=shift_id,
            started_at=timestamp,
            completed_at=timestamp,
            machine_result=calculate_inspection_result(
                point.machine_result for point in points
            ),
            current_result=calculate_inspection_result(
                point.current_result for point in points
            ),
            views=views,
            points=points,
            summary=summarize_points(points),
        )

    def get_inspection(self, inspection_id: str) -> Inspection | None:
        return self._repository.get_by_id(inspection_id)

    def _delete_stored_images(self, views: list[InspectionView]) -> None:
        for view in views:
            if view.current_image_key is not None:
                try:
                    self._image_storage.delete(view.current_image_key)
                except OSError:
                    continue


def _parse_view_ids(view_ids_json: str) -> list[str]:
    try:
        value = json.loads(view_ids_json)
    except json.JSONDecodeError as error:
        if "," not in view_ids_json or "[" in view_ids_json or "]" in view_ids_json:
            raise InspectionInputError(
                "view_ids must be a JSON array of strings"
            ) from error
        value = [item.strip() for item in view_ids_json.split(",")]

    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InspectionInputError("view_ids must be a JSON array of strings")
    if any(not item or item != item.strip() for item in value):
        raise InspectionInputError("view_ids must not contain blank or padded IDs")
    return value


def _evidence_value(value: EngineEvidenceValue) -> EvidenceValue:
    return EvidenceValue(label=value.label, value=value.value, unit=value.unit)


def _view_label(view_id: str) -> str:
    labels = {"top": "Top", "angle-1": "Angle 1", "bottom": "Bottom"}
    return labels.get(view_id, view_id.replace("-", " ").title())


def _view_side(view_id: str) -> ViewSide:
    sides = {"top": ViewSide.FRONT, "bottom": ViewSide.BACK}
    return sides.get(view_id, ViewSide.UNKNOWN)


def _golden_image_url(view_id: str, uploaded_image_url: str) -> str:
    known_views = {"top", "angle-1", "bottom"}
    if view_id in known_views:
        return f"/mock/pcb/golden-{view_id}.jpg"
    return uploaded_image_url
