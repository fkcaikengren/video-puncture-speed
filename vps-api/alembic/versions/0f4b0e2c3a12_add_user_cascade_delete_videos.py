"""add user cascade delete videos

Revision ID: 0f4b0e2c3a12
Revises: ba0dfd7cca85
Create Date: 2026-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0f4b0e2c3a12"
down_revision: Union[str, None] = "ba0dfd7cca85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("videos_user_id_fkey", "videos", type_="foreignkey")
    op.create_foreign_key(
        "videos_user_id_fkey",
        "videos",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("videos_user_id_fkey", "videos", type_="foreignkey")
    op.create_foreign_key(
        "videos_user_id_fkey",
        "videos",
        "users",
        ["user_id"],
        ["id"],
    )

