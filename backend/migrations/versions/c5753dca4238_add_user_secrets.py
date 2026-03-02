"""add_user_secrets

Revision ID: c5753dca4238
Revises: 05ef92fa7dfd
Create Date: 2026-02-28 16:52:39.806081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5753dca4238'
down_revision: Union[str, Sequence[str], None] = '05ef92fa7dfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table('user_secrets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('provider', sa.String(length=50), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('encrypted_value', sa.Text(), nullable=False),
    sa.Column('key_version', sa.Integer(), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'provider', name='uq_user_secrets_user_provider')
    )
    op.create_index(op.f('ix_user_secrets_user_id'), 'user_secrets', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(op.f('ix_user_secrets_user_id'), table_name='user_secrets')
    op.drop_table('user_secrets')
