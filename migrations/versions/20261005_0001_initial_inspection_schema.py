"""Create the initial inspection persistence schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261005_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("inspection_public_id_seq")))
    op.create_table(
        "inspections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("sku_code", sa.String(length=128), nullable=False),
        sa.Column("station_id", sa.String(length=128), nullable=False),
        sa.Column("shift_id", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("machine_result", sa.String(length=16), nullable=False),
        sa.Column("current_result", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("machine_result IN ('PASS', 'REVIEW', 'FAIL')", name="ck_inspections_machine_result"),
        sa.CheckConstraint("current_result IN ('PASS', 'REVIEW', 'FAIL')", name="ck_inspections_current_result"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_inspections_shift_completed", "inspections", ["shift_id", "completed_at"])
    op.create_index(
        "ix_inspections_shift_result_completed",
        "inspections",
        ["shift_id", "current_result", "completed_at"],
    )
    op.create_table(
        "inspection_views",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("inspection_id", sa.BigInteger(), nullable=False),
        sa.Column("view_id", sa.String(length=128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("current_image_ref", sa.Text(), nullable=False),
        sa.Column("golden_image_ref", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_views_position_nonnegative"),
        sa.CheckConstraint("width >= 0", name="ck_views_width_nonnegative"),
        sa.CheckConstraint("height >= 0", name="ck_views_height_nonnegative"),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id", "position", name="uq_views_inspection_position"),
        sa.UniqueConstraint("inspection_id", "view_id", name="uq_views_inspection_view"),
    )
    op.create_table(
        "inspection_points",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("inspection_id", sa.BigInteger(), nullable=False),
        sa.Column("point_code", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("target_ref", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("machine_result", sa.String(length=16), nullable=False),
        sa.Column("current_result", sa.String(length=16), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.CheckConstraint("machine_result IN ('PASS', 'REVIEW', 'FAIL')", name="ck_points_machine_result"),
        sa.CheckConstraint("current_result IN ('PASS', 'REVIEW', 'FAIL')", name="ck_points_current_result"),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id", "point_code", name="uq_points_inspection_code"),
    )
    op.create_table(
        "inspection_regions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("point_id", sa.BigInteger(), nullable=False),
        sa.Column("shape", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["point_id"], ["inspection_points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("point_id"),
    )
    op.create_table(
        "inspection_checks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("point_id", sa.BigInteger(), nullable=False),
        sa.Column("check_code", sa.String(length=96), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("group", sa.String(length=32), nullable=False),
        sa.Column("issue_type", sa.String(length=64), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.CheckConstraint("result IN ('PASS', 'REVIEW', 'FAIL')", name="ck_checks_result"),
        sa.ForeignKeyConstraint(["point_id"], ["inspection_points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("point_id", "check_code", name="uq_checks_point_code"),
    )
    op.create_table(
        "check_evidence",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("check_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["check_id"], ["inspection_checks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("check_id"),
    )
    op.create_table(
        "inspection_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("point_id", sa.BigInteger(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('PASS', 'FAIL')", name="ck_reviews_decision"),
        sa.ForeignKeyConstraint(["point_id"], ["inspection_points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_point_latest", "inspection_reviews", ["point_id", "reviewed_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_point_latest", table_name="inspection_reviews")
    op.drop_table("inspection_reviews")
    op.drop_table("check_evidence")
    op.drop_table("inspection_checks")
    op.drop_table("inspection_regions")
    op.drop_table("inspection_points")
    op.drop_table("inspection_views")
    op.drop_index("ix_inspections_shift_result_completed", table_name="inspections")
    op.drop_index("ix_inspections_shift_completed", table_name="inspections")
    op.drop_table("inspections")
    op.execute(sa.schema.DropSequence(sa.Sequence("inspection_public_id_seq")))