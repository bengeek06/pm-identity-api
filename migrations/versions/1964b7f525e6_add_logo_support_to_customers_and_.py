"""add_logo_support_to_customers_and_subcontractors

Revision ID: 1964b7f525e6
Revises: 9d10e1359386
Create Date: 2025-11-21 19:23:11.329107

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1964b7f525e6'
down_revision = '9d10e1359386'
branch_labels = None
depends_on = None


def upgrade():
    # Add logo fields to customer table
    op.add_column('customer', sa.Column('logo_file_id', sa.String(length=36), nullable=True))
    op.add_column('customer', sa.Column('has_logo', sa.Boolean(), nullable=False, server_default='0'))
    
    # Add logo fields to subcontractor table
    op.add_column('subcontractor', sa.Column('logo_file_id', sa.String(length=36), nullable=True))
    op.add_column('subcontractor', sa.Column('has_logo', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Remove logo fields from subcontractor table
    op.drop_column('subcontractor', 'has_logo')
    op.drop_column('subcontractor', 'logo_file_id')
    
    # Remove logo fields from customer table
    op.drop_column('customer', 'has_logo')
    op.drop_column('customer', 'logo_file_id')
