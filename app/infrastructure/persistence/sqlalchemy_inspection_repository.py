# Implements inspection persistence and queries using SQLAlchemy.
from datetime import datetime, timezone

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.domain.inspection.enums import InspectionResult
from app.infrastructure.persistence.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.models import (
    INSPECTION_ID_SEQUENCE,
    InspectionCheckRow,
    InspectionEvidenceRow,
    InspectionPointRow,
    InspectionRegionRow,
    InspectionReviewRow,
    InspectionRow,
    InspectionViewRow,
)
from app.application.ports.inspection_repository import InspectionRepository
from app.schemas.common import InspectionEvidence, InspectionRegion
from app.schemas.inspection import (
    Inspection,
    InspectionCheck,
    InspectionPoint,
    InspectionSummary,
    InspectionView,
)
from app.schemas.review import ReviewRecord

REGION_ADAPTER = TypeAdapter(InspectionRegion)


class SqlAlchemyInspectionRepository(InspectionRepository):
    def __init__(
        self, session_factory: sessionmaker[Session], dialect_name: str
    ) -> None:
        self._session_factory = session_factory
        self._dialect_name = dialect_name

    @classmethod
    def from_url(cls, database_url: str) -> "SqlAlchemyInspectionRepository":
        engine = create_database_engine(database_url)
        return cls(create_session_factory(engine), engine.dialect.name)

    @classmethod
    def from_engine(cls, engine) -> "SqlAlchemyInspectionRepository":
        return cls(create_session_factory(engine), engine.dialect.name)

    def allocate_inspection_id(self) -> str:
        with self._session_factory() as session:
            if self._dialect_name == "postgresql":
                next_id = session.scalar(select(INSPECTION_ID_SEQUENCE.next_value()))
            elif self._dialect_name == "sqlite":
                next_id = session.scalar(
                    select(func.coalesce(func.max(InspectionRow.id), 0) + 1)
                )
            else:
                raise NotImplementedError(
                    f"Inspection ID allocation is unsupported for {self._dialect_name}"
                )
        return f"INS-{next_id:05d}"

    def save(self, inspection: Inspection) -> None:
        with self._session_factory.begin() as session:
            row = session.scalar(
                select(InspectionRow)
                .where(InspectionRow.public_id == inspection.id)
                .options(
                    selectinload(InspectionRow.views),
                    selectinload(InspectionRow.points).selectinload(
                        InspectionPointRow.region
                    ),
                    selectinload(InspectionRow.points)
                    .selectinload(InspectionPointRow.checks)
                    .selectinload(InspectionCheckRow.evidence),
                    selectinload(InspectionRow.points).selectinload(
                        InspectionPointRow.reviews
                    ),
                )
            )
            if row is None:
                row = InspectionRow(public_id=inspection.id)
                session.add(row)

            row.sku_code = inspection.sku_code
            row.station_id = inspection.station_id
            row.shift_id = inspection.shift_id
            row.started_at = inspection.started_at
            row.completed_at = inspection.completed_at
            row.machine_result = inspection.machine_result.value
            row.current_result = inspection.current_result.value

            self._sync_views(row, inspection)
            self._sync_points(row, inspection)

    def get_by_id(self, inspection_id: str) -> Inspection | None:
        with self._session_factory() as session:
            row = self._load_inspection(session, inspection_id)
            return _to_schema(row) if row is not None else None

    def get_by_shift(self, shift_id: str) -> list[Inspection]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(InspectionRow)
                .where(InspectionRow.shift_id == shift_id)
                .options(*_inspection_load_options())
                .order_by(InspectionRow.completed_at, InspectionRow.id)
            ).all()
            return [_to_schema(row) for row in rows]

    def _load_inspection(
        self, session: Session, inspection_id: str
    ) -> InspectionRow | None:
        return session.scalar(
            select(InspectionRow)
            .where(InspectionRow.public_id == inspection_id)
            .options(*_inspection_load_options())
        )

    @staticmethod
    def _sync_points(row: InspectionRow, inspection: Inspection) -> None:
        incoming_by_id = {point.id: point for point in inspection.points}
        existing_by_id = {point.point_code: point for point in row.points}
        row.points[:] = [
            point for point in row.points if point.point_code in incoming_by_id
        ]

        for position, point in enumerate(inspection.points):
            point_row = existing_by_id.get(point.id)
            if point_row is None:
                point_row = InspectionPointRow(point_code=point.id)
                row.points.append(point_row)

            point_row.position = position
            point_row.target_ref = point.target_ref
            point_row.target_type = point.target_type.value
            point_row.machine_result = point.machine_result.value
            point_row.current_result = point.current_result.value
            point_row.requires_review = point.requires_review

            region = (
                point.region.model_dump(mode="json")
                if point.region is not None
                else None
            )
            if region is None:
                point_row.region = None
            elif point_row.region is None:
                point_row.region = InspectionRegionRow(shape=region)
            else:
                point_row.region.shape = region

            SqlAlchemyInspectionRepository._sync_checks(point_row, point)
            SqlAlchemyInspectionRepository._append_review(point_row, point.review)

    @staticmethod
    def _sync_views(row: InspectionRow, inspection: Inspection) -> None:
        incoming_by_id = {view.id: view for view in inspection.views}
        existing_by_id = {view.view_id: view for view in row.views}
        row.views[:] = [view for view in row.views if view.view_id in incoming_by_id]

        for position, view in enumerate(inspection.views):
            view_row = existing_by_id.get(view.id)
            if view_row is None:
                view_row = InspectionViewRow(view_id=view.id)
                row.views.append(view_row)
            view_row.position = position
            view_row.label = view.label
            view_row.side = view.side.value
            view_row.current_image_ref = (
                view.current_image_key or view.current_image_url
            )
            view_row.golden_image_ref = view.golden_image_url
            view_row.width = view.width
            view_row.height = view.height

    @staticmethod
    def _sync_checks(point_row: InspectionPointRow, point: InspectionPoint) -> None:
        incoming_by_id = {check.id: check for check in point.checks}
        existing_by_id = {check.check_code: check for check in point_row.checks}
        point_row.checks[:] = [
            check for check in point_row.checks if check.check_code in incoming_by_id
        ]

        for position, check in enumerate(point.checks):
            check_row = existing_by_id.get(check.id)
            if check_row is None:
                check_row = InspectionCheckRow(check_code=check.id)
                point_row.checks.append(check_row)

            check_row.position = position
            check_row.group_name = check.group.value
            check_row.issue_type = check.issue_type.value if check.issue_type else None
            check_row.result = check.result.value
            payload = check.evidence.model_dump(mode="json", exclude_none=True)
            if check_row.evidence is None:
                check_row.evidence = InspectionEvidenceRow(payload=payload)
            else:
                check_row.evidence.payload = payload

    @staticmethod
    def _append_review(
        point_row: InspectionPointRow,
        review: ReviewRecord | None,
    ) -> None:
        if review is None:
            return
        latest = max(
            point_row.reviews,
            key=lambda item: (_utc(item.reviewed_at), item.id or 0),
            default=None,
        )
        if latest is not None and (
            _utc(latest.reviewed_at) == _utc(review.reviewed_at)
            and latest.decision == review.decision.value
            and latest.note == review.note
        ):
            return
        point_row.reviews.append(
            InspectionReviewRow(
                decision=review.decision.value,
                note=review.note,
                reviewed_at=review.reviewed_at,
            )
        )


def _inspection_load_options():
    return (
        selectinload(InspectionRow.views),
        selectinload(InspectionRow.points).selectinload(InspectionPointRow.region),
        selectinload(InspectionRow.points)
        .selectinload(InspectionPointRow.checks)
        .selectinload(InspectionCheckRow.evidence),
        selectinload(InspectionRow.points).selectinload(InspectionPointRow.reviews),
    )


def _to_schema(row: InspectionRow) -> Inspection:
    points = [
        InspectionPoint(
            id=point.point_code,
            target_ref=point.target_ref,
            target_type=point.target_type,
            machine_result=point.machine_result,
            current_result=point.current_result,
            requires_review=point.requires_review,
            region=(
                REGION_ADAPTER.validate_python(point.region.shape)
                if point.region is not None
                else None
            ),
            checks=[
                InspectionCheck(
                    id=check.check_code,
                    group=check.group_name,
                    issue_type=check.issue_type,
                    result=check.result,
                    evidence=InspectionEvidence.model_validate(check.evidence.payload),
                )
                for check in point.checks
            ],
            review=_latest_review(point),
        )
        for point in row.points
    ]
    return Inspection(
        id=row.public_id,
        sku_code=row.sku_code,
        station_id=row.station_id,
        shift_id=row.shift_id,
        started_at=_utc(row.started_at),
        completed_at=_utc(row.completed_at) if row.completed_at is not None else None,
        machine_result=row.machine_result,
        current_result=row.current_result,
        views=[
            InspectionView(
                id=view.view_id,
                label=view.label,
                side=view.side,
                current_image_url=_image_url(view.current_image_ref),
                current_image_key=(
                    view.current_image_ref
                    if view.current_image_ref.startswith("inspections/")
                    else None
                ),
                golden_image_url=view.golden_image_ref,
                width=view.width,
                height=view.height,
            )
            for view in row.views
        ],
        points=points,
        summary=_summarize(points),
    )


def _latest_review(point: InspectionPointRow) -> ReviewRecord | None:
    latest = max(
        point.reviews,
        key=lambda item: (_utc(item.reviewed_at), item.id or 0),
        default=None,
    )
    if latest is None:
        return None
    return ReviewRecord(
        decision=latest.decision,
        note=latest.note,
        reviewed_at=_utc(latest.reviewed_at),
    )


def _summarize(points: list[InspectionPoint]) -> InspectionSummary:
    return InspectionSummary(
        total_points=len(points),
        pass_=sum(point.current_result is InspectionResult.PASS for point in points),
        review=sum(point.current_result is InspectionResult.REVIEW for point in points),
        fail=sum(point.current_result is InspectionResult.FAIL for point in points),
        reviewed=sum(point.review is not None for point in points),
        unresolved_reviews=sum(
            point.requires_review and point.review is None for point in points
        ),
    )


def _utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def _image_url(image_ref: str) -> str:
    if image_ref.startswith("inspections/"):
        return f"/api/v1/images/{image_ref}"
    return image_ref
