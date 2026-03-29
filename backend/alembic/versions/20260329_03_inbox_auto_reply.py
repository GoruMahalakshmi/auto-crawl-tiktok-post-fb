"""Add per-page AI reply settings and inbox message logs.

Revision ID: 20260329_03
Revises: 20260329_02
Create Date: 2026-03-29 23:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_03"
down_revision = "20260329_02"
branch_labels = None
depends_on = None


INTERACTION_STATUS = ("pending", "replied", "failed", "ignored")


def _inspector(bind):
    return sa.inspect(bind)


def _has_table(bind, table_name: str) -> bool:
    return _inspector(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector(bind).get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(item["name"] == index_name for item in _inspector(bind).get_indexes(table_name))


def _interaction_status_type(bind):
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(*INTERACTION_STATUS, name="interactionstatus", create_type=False)
    return sa.String()


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TYPE interactionstatus ADD VALUE IF NOT EXISTS 'ignored'"))

    if _has_table(bind, "facebook_pages"):
        additions = [
            ("comment_auto_reply_enabled", sa.Boolean(), sa.true()),
            ("comment_ai_prompt", sa.String(), None),
            ("message_auto_reply_enabled", sa.Boolean(), sa.false()),
            ("message_ai_prompt", sa.String(), None),
        ]
        for column_name, column_type, default_value in additions:
            if not _has_column(bind, "facebook_pages", column_name):
                kwargs = {"nullable": True}
                if default_value is not None:
                    kwargs["server_default"] = default_value
                op.add_column("facebook_pages", sa.Column(column_name, column_type, **kwargs))

    if not _has_table(bind, "inbox_message_logs"):
        uuid_type = postgresql.UUID(as_uuid=True) if bind.dialect.name == "postgresql" else sa.Uuid()
        op.create_table(
            "inbox_message_logs",
            sa.Column("id", uuid_type, primary_key=True, nullable=False),
            sa.Column("page_id", sa.String(), sa.ForeignKey("facebook_pages.page_id"), nullable=True),
            sa.Column("facebook_message_id", sa.String(), nullable=True),
            sa.Column("sender_id", sa.String(), nullable=True),
            sa.Column("recipient_id", sa.String(), nullable=True),
            sa.Column("user_message", sa.String(), nullable=True),
            sa.Column("ai_reply", sa.String(), nullable=True),
            sa.Column("facebook_reply_message_id", sa.String(), nullable=True),
            sa.Column("status", _interaction_status_type(bind), nullable=True),
            sa.Column("last_error", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("facebook_message_id"),
        )
        op.create_index("ix_inbox_message_logs_page_id", "inbox_message_logs", ["page_id"], unique=False)
        op.create_index("ix_inbox_message_logs_facebook_message_id", "inbox_message_logs", ["facebook_message_id"], unique=False)
        op.create_index("ix_inbox_message_logs_sender_id", "inbox_message_logs", ["sender_id"], unique=False)

    if _has_table(bind, "inbox_message_logs"):
        if not _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_page_id"):
            op.create_index("ix_inbox_message_logs_page_id", "inbox_message_logs", ["page_id"], unique=False)
        if not _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_facebook_message_id"):
            op.create_index("ix_inbox_message_logs_facebook_message_id", "inbox_message_logs", ["facebook_message_id"], unique=False)
        if not _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_sender_id"):
            op.create_index("ix_inbox_message_logs_sender_id", "inbox_message_logs", ["sender_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "inbox_message_logs"):
        op.drop_table("inbox_message_logs")
