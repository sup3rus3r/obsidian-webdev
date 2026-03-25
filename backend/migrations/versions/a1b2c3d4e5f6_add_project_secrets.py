"""add_project_secrets

Revision ID: a1b2c3d4e5f6
Revises: c5753dca4238
Create Date: 2026-03-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c5753dca4238'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_secrets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('secret_type', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('encrypted_value', sa.Text(), nullable=False),
        sa.Column('public_value', sa.Text(), nullable=True),
        sa.Column('key_version', sa.Integer(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'project_id', 'secret_type', name='uq_project_secrets_user_project_type'),
    )
    op.create_index('ix_project_secrets_user_id', 'project_secrets', ['user_id'])
    op.create_index('ix_project_secrets_project_id', 'project_secrets', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_project_secrets_project_id', table_name='project_secrets')
    op.drop_index('ix_project_secrets_user_id', table_name='project_secrets')
    op.drop_table('project_secrets')
