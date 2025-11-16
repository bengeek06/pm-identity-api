"""fix: rename is_verifed to is_verified

Revision ID: 5f663632a5e8
Revises: 7645d50dfa6e
Create Date: 2025-11-16 21:26:24.923631

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "5f663632a5e8"
down_revision = "7645d50dfa6e"
branch_labels = None
depends_on = None


def upgrade():
    # Rename is_verifed column to is_verified
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column("is_verifed", new_column_name="is_verified")


def downgrade():
    # Rename is_verified column back to is_verifed
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column("is_verified", new_column_name="is_verifed")
