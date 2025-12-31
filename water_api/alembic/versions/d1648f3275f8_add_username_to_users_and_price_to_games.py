"""add username to users and price to games

Revision ID: d1648f3275f8
Revises: 94364f1d7882
Create Date: 2025-12-31 16:48:58.964812

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1648f3275f8"
down_revision: Union[str, Sequence[str], None] = "94364f1d7882"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add price column to games (with server default for existing rows)
    op.add_column(
        "games",
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
    )
    # Remove server default after migration (optional, keeps model as source of truth)
    op.alter_column("games", "price", server_default=None)

    # Add username column to users (nullable first)
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))

    # Generate usernames for existing users based on email
    op.execute("UPDATE users SET username = split_part(email, '@', 1) WHERE username IS NULL")

    # Make username NOT NULL and add unique index
    op.alter_column("users", "username", nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
    op.drop_column("games", "price")
