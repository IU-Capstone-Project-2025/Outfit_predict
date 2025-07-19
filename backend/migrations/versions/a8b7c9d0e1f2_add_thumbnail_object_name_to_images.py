"""add thumbnail_object_name to images

Revision ID: a8b7c9d0e1f2
Revises: 80c2334b9c61
Create Date: 2025-01-27 17:21:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8b7c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "80c2334b9c61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add thumbnail_object_name column to images table."""
    op.add_column(
        "images",
        sa.Column("thumbnail_object_name", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """Remove thumbnail_object_name column from images table."""
    op.drop_column("images", "thumbnail_object_name")
