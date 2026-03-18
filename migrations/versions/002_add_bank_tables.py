"""add bank_connections and bank_transactions tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bank_connections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('carrier_id', sa.Integer(), nullable=False),
        sa.Column('institution_name', sa.String(length=200), nullable=False),
        sa.Column('account_name', sa.String(length=200), nullable=False),
        sa.Column('account_mask', sa.String(length=4), nullable=False),
        sa.Column('connection_type', sa.Enum('plaid', 'manual', name='connectiontype'), nullable=False),
        sa.Column('plaid_access_token', sa.String(length=200), nullable=True),
        sa.Column('plaid_item_id', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['carrier_id'], ['carrier_profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'bank_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bank_connection_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_deposit', sa.Boolean(), nullable=False),
        sa.Column('is_reconciled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('matched_invoice_id', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bank_connection_id'], ['bank_connections.id']),
        sa.ForeignKeyConstraint(['matched_invoice_id'], ['invoices.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )


def downgrade() -> None:
    op.drop_table('bank_transactions')
    op.drop_table('bank_connections')
    op.execute('DROP TYPE IF EXISTS connectiontype')
