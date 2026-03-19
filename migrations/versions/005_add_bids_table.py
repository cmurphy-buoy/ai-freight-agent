"""add bids table

Revision ID: 005
Revises: 004
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bids',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('carrier_id', sa.Integer(), nullable=False),
        sa.Column('load_id', sa.String(50), nullable=False),
        sa.Column('broker_name', sa.String(200), nullable=False),
        sa.Column('broker_mc', sa.String(6), nullable=False),
        sa.Column('origin_city', sa.String(100), nullable=False),
        sa.Column('origin_state', sa.String(2), nullable=False),
        sa.Column('destination_city', sa.String(100), nullable=False),
        sa.Column('destination_state', sa.String(2), nullable=False),
        sa.Column('miles', sa.Integer(), nullable=False),
        sa.Column('listed_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('bid_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('bid_rate_per_mile', sa.Numeric(5, 2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'submitted', 'accepted', 'rejected', 'expired', 'withdrawn', name='bidstatus'), nullable=True),
        sa.Column('auto_bid', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['carrier_id'], ['carrier_profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('bids')
    sa.Enum(name='bidstatus').drop(op.get_bind(), checkfirst=True)
