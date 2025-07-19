"""add clothing_type to images

Revision ID: b1d2e3f4g5h6
Revises: c8e9f1a2b3d4
Create Date: 2025-01-27 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d2e3f4g5h6"
down_revision: Union[str, Sequence[str], None] = "c8e9f1a2b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add clothing_type column to images table."""
    op.add_column(
        "images",
        sa.Column("clothing_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """Remove clothing_type column from images table."""
    op.drop_column("images", "clothing_type")
