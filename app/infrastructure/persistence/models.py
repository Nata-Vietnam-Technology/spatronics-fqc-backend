# Defines SQLAlchemy tables for inspections, views, points, checks, and reviews.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base

INSPECTION_ID_SEQUENCE = Sequence("inspection_public_id_seq")
JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")
INTERNAL_ID = BigInteger().with_variant(Integer, "sqlite")


class InspectionRow(Base):
    __tablename__ = "inspections"
    __table_args__ = (
        CheckConstraint(
            "machine_result IN ('PASS', 'REVIEW', 'FAIL')",
            name="ck_inspections_machine_result",
        ),
        CheckConstraint(
            "current_result IN ('PASS', 'REVIEW', 'FAIL')",
            name="ck_inspections_current_result",
        ),
        Index("ix_inspections_shift_completed", "shift_id", "completed_at"),
        Index(
            "ix_inspections_shift_result_completed",
            "shift_id",
            "current_result",
            "completed_at",
        ),
    )

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    sku_code: Mapped[str] = mapped_column(String(128), nullable=False)
    station_id: Mapped[str] = mapped_column(String(128), nullable=False)
    shift_id: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    machine_result: Mapped[str] = mapped_column(String(16), nullable=False)
    current_result: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    views: Mapped[list[InspectionViewRow]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        order_by="InspectionViewRow.position",
    )
    points: Mapped[list[InspectionPointRow]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        order_by="InspectionPointRow.position",
    )


class InspectionViewRow(Base):
    __tablename__ = "inspection_views"
    __table_args__ = (
        UniqueConstraint("inspection_id", "view_id", name="uq_views_inspection_view"),
        UniqueConstraint(
            "inspection_id", "position", name="uq_views_inspection_position"
        ),
        CheckConstraint("position >= 0", name="ck_views_position_nonnegative"),
        CheckConstraint("width >= 0", name="ck_views_width_nonnegative"),
        CheckConstraint("height >= 0", name="ck_views_height_nonnegative"),
    )

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    view_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    current_image_ref: Mapped[str] = mapped_column(Text, nullable=False)
    golden_image_ref: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    inspection: Mapped[InspectionRow] = relationship(back_populates="views")


class InspectionPointRow(Base):
    __tablename__ = "inspection_points"
    __table_args__ = (
        UniqueConstraint(
            "inspection_id", "point_code", name="uq_points_inspection_code"
        ),
        CheckConstraint(
            "machine_result IN ('PASS', 'REVIEW', 'FAIL')",
            name="ck_points_machine_result",
        ),
        CheckConstraint(
            "current_result IN ('PASS', 'REVIEW', 'FAIL')",
            name="ck_points_current_result",
        ),
    )

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    point_code: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    target_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    machine_result: Mapped[str] = mapped_column(String(16), nullable=False)
    current_result: Mapped[str] = mapped_column(String(16), nullable=False)
    requires_review: Mapped[bool] = mapped_column(nullable=False)

    inspection: Mapped[InspectionRow] = relationship(back_populates="points")
    region: Mapped[InspectionRegionRow | None] = relationship(
        back_populates="point", cascade="all, delete-orphan", uselist=False
    )
    checks: Mapped[list[InspectionCheckRow]] = relationship(
        back_populates="point",
        cascade="all, delete-orphan",
        order_by="InspectionCheckRow.position",
    )
    reviews: Mapped[list[InspectionReviewRow]] = relationship(
        back_populates="point",
        cascade="all, delete-orphan",
        order_by="InspectionReviewRow.id",
    )


class InspectionRegionRow(Base):
    __tablename__ = "inspection_regions"

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_points.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    shape: Mapped[dict] = mapped_column(JSON_DOCUMENT, nullable=False)

    point: Mapped[InspectionPointRow] = relationship(back_populates="region")


class InspectionCheckRow(Base):
    __tablename__ = "inspection_checks"
    __table_args__ = (
        UniqueConstraint("point_id", "check_code", name="uq_checks_point_code"),
        CheckConstraint(
            "result IN ('PASS', 'REVIEW', 'FAIL')",
            name="ck_checks_result",
        ),
    )

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_points.id", ondelete="CASCADE"), nullable=False
    )
    check_code: Mapped[str] = mapped_column(String(96), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    group_name: Mapped[str] = mapped_column("group", String(32), nullable=False)
    issue_type: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(16), nullable=False)

    point: Mapped[InspectionPointRow] = relationship(back_populates="checks")
    evidence: Mapped[InspectionEvidenceRow | None] = relationship(
        back_populates="check", cascade="all, delete-orphan", uselist=False
    )


class InspectionEvidenceRow(Base):
    __tablename__ = "check_evidence"

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    check_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_checks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSON_DOCUMENT, nullable=False)

    check: Mapped[InspectionCheckRow] = relationship(back_populates="evidence")


class InspectionReviewRow(Base):
    __tablename__ = "inspection_reviews"
    __table_args__ = (
        CheckConstraint("decision IN ('PASS', 'FAIL')", name="ck_reviews_decision"),
        Index("ix_reviews_point_latest", "point_id", "reviewed_at", "id"),
    )

    id: Mapped[int] = mapped_column(INTERNAL_ID, primary_key=True)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_points.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    point: Mapped[InspectionPointRow] = relationship(back_populates="reviews")
