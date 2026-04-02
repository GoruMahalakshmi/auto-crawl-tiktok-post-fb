"""affiliate comment multi-step sequence

Revision ID: 20260403_01
Revises: 20260402_01
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_01"
down_revision = "20260402_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "facebook_pages",
        sa.Column("affiliate_comment_target_count", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "facebook_pages",
        sa.Column("affiliate_comment_min_delay_seconds", sa.Integer(), nullable=False, server_default="60"),
    )
    op.add_column(
        "facebook_pages",
        sa.Column("affiliate_comment_max_delay_seconds", sa.Integer(), nullable=False, server_default="600"),
    )

    op.add_column("videos", sa.Column("affiliate_comment_fb_ids", sa.JSON(), nullable=True))
    op.add_column(
        "videos",
        sa.Column("affiliate_comment_target_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "videos",
        sa.Column("affiliate_comment_completed_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.alter_column("facebook_pages", "affiliate_comment_target_count", server_default=None)
    op.alter_column("facebook_pages", "affiliate_comment_min_delay_seconds", server_default=None)
    op.alter_column("facebook_pages", "affiliate_comment_max_delay_seconds", server_default=None)
    op.alter_column("videos", "affiliate_comment_target_count", server_default=None)
    op.alter_column("videos", "affiliate_comment_completed_count", server_default=None)


def downgrade() -> None:
    op.drop_column("videos", "affiliate_comment_completed_count")
    op.drop_column("videos", "affiliate_comment_target_count")
    op.drop_column("videos", "affiliate_comment_fb_ids")

    op.drop_column("facebook_pages", "affiliate_comment_max_delay_seconds")
    op.drop_column("facebook_pages", "affiliate_comment_min_delay_seconds")
    op.drop_column("facebook_pages", "affiliate_comment_target_count")
