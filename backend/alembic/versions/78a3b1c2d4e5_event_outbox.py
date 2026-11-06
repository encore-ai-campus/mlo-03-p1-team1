"""Durable delivery of committed behavior events to MongoDB."""
from alembic import op
import sqlalchemy as sa

revision = '78a3b1c2d4e5'
down_revision = '65e5c5f31b9a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'event_outbox',
        sa.Column('event_id', sa.String(36), sa.ForeignKey('behavior_events.event_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.String(80), nullable=True),
    )
    op.create_index('ix_outbox_pending', 'event_outbox', ['delivered_at', 'next_attempt_at'])


def downgrade():
    op.drop_table('event_outbox')
