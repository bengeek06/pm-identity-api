"""add password reset otp table

Revision ID: 3c0ce317ded6
Revises: 9748d4f19f62
Create Date: 2025-11-22 05:14:39.919013

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c0ce317ded6'
down_revision = '9748d4f19f62'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'password_reset_otp',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('otp_code', sa.String(255), nullable=False),  # Hashed OTP
        sa.Column('attempts', sa.Integer, default=0, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('used_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_password_reset_otp_user_id', 'password_reset_otp', ['user_id'])
    op.create_index('ix_password_reset_otp_expires_at', 'password_reset_otp', ['expires_at'])


def downgrade():
    op.drop_index('ix_password_reset_otp_expires_at')
    op.drop_index('ix_password_reset_otp_user_id')
    op.drop_table('password_reset_otp')
