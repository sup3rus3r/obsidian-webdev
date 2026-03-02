"""initial_schema

Revision ID: 05ef92fa7dfd
Revises: 
Create Date: 2026-02-28 16:43:40.029379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '05ef92fa7dfd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_index(op.f('ix_api_clients_id'), table_name='api_clients')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')


def downgrade() -> None:
    """Downgrade schema."""

    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=1)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_api_clients_id'), 'api_clients', ['id'], unique=False)
