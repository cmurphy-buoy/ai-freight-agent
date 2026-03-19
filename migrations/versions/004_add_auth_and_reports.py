"""add auth token to carrier_profiles

Revision ID: 004
Revises: 003
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'carrier_profiles',
        sa.Column('api_token', sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f('ix_carrier_profiles_api_token'),
        'carrier_profiles',
        ['api_token'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_carrier_profiles_api_token'), table_name='carrier_profiles')
    op.drop_column('carrier_profiles', 'api_token')
