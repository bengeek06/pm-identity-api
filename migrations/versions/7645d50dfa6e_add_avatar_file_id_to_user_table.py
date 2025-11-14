"""Add avatar_file_id to user table

Revision ID: 7645d50dfa6e
Revises: 3950c1dd0418
Create Date: 2025-11-09 03:43:30.407359

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7645d50dfa6e"
down_revision = "3950c1dd0418"
branch_labels = None
depends_on = None


def upgrade():
    # Add avatar_file_id column to user table
    op.add_column(
        "user",
        sa.Column("avatar_file_id", sa.String(length=255), nullable=True),
    )


def downgrade():
    # Remove avatar_file_id column from user table
    op.drop_column("user", "avatar_file_id")
