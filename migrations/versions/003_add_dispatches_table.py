"""add dispatches table

Revision ID: 003
Revises: 002
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dispatches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('truck_id', sa.Integer(), nullable=False),
        sa.Column('carrier_id', sa.Integer(), nullable=False),
        sa.Column('driver_name', sa.String(length=200), nullable=False),
        sa.Column('driver_phone', sa.String(length=20), nullable=True),
        sa.Column('status', sa.Enum('assigned', 'en_route_pickup', 'at_pickup', 'loaded', 'en_route_delivery', 'at_delivery', 'delivered', 'cancelled', name='dispatchstatus'), nullable=False),
        sa.Column('pickup_confirmation', sa.String(length=100), nullable=True),
        sa.Column('delivery_confirmation', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('picked_up_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['truck_id'], ['trucks.id']),
        sa.ForeignKeyConstraint(['carrier_id'], ['carrier_profiles.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_id'),
    )


def downgrade() -> None:
    op.drop_table('dispatches')
    op.execute('DROP TYPE IF EXISTS dispatchstatus')
