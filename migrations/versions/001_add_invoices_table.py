"""add invoices table

Revision ID: 001
Revises: None
Create Date: 2026-03-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('carrier_id', sa.Integer(), nullable=False),
        sa.Column('load_reference', sa.String(length=100), nullable=True),
        sa.Column('broker_name', sa.String(length=200), nullable=False),
        sa.Column('broker_mc', sa.String(length=6), nullable=False),
        sa.Column('origin_city', sa.String(length=100), nullable=False),
        sa.Column('origin_state', sa.String(length=2), nullable=False),
        sa.Column('destination_city', sa.String(length=100), nullable=False),
        sa.Column('destination_state', sa.String(length=2), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('rate_per_mile', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('miles', sa.Integer(), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'sent', 'outstanding', 'paid', 'overdue', 'factored', 'disputed', name='invoicestatus'), nullable=False),
        sa.Column('factoring_company', sa.String(length=200), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('payment_reference', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['carrier_id'], ['carrier_profiles.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('invoices')
    op.execute('DROP TYPE IF EXISTS invoicestatus')
