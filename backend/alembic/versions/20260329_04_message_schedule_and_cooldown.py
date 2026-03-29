"""Add inbox auto-reply schedule and cooldown settings.

Revision ID: 20260329_04
Revises: 20260329_03
Create Date: 2026-03-29 23:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260329_04"
down_revision = "20260329_03"
branch_labels = None
depends_on = None


def _inspector(bind):
    return sa.inspect(bind)


def _has_table(bind, table_name: str) -> bool:
    return _inspector(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector(bind).get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "facebook_pages"):
        return

    additions = [
        ("message_reply_schedule_enabled", sa.Boolean(), sa.false()),
        ("message_reply_start_time", sa.String(), sa.text("'08:00'")),
        ("message_reply_end_time", sa.String(), sa.text("'22:00'")),
        ("message_reply_cooldown_minutes", sa.Integer(), sa.text("0")),
    ]
    for column_name, column_type, default_value in additions:
        if not _has_column(bind, "facebook_pages", column_name):
            op.add_column(
                "facebook_pages",
                sa.Column(column_name, column_type, nullable=True, server_default=default_value),
            )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "facebook_pages"):
        return

    for column_name in [
        "message_reply_cooldown_minutes",
        "message_reply_end_time",
        "message_reply_start_time",
        "message_reply_schedule_enabled",
    ]:
        if _has_column(bind, "facebook_pages", column_name):
            op.drop_column("facebook_pages", column_name)
