"""Member preferences, venue coordinates, attendance and collection audit."""
from alembic import op
import sqlalchemy as sa

revision = '51c0a298b710'
down_revision = '30943449ef19'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('preferences', sa.JSON(), nullable=True))
    op.execute("UPDATE users SET preferences = '{}' WHERE preferences IS NULL")
    op.alter_column('users', 'preferences', existing_type=sa.JSON(), nullable=False)
    op.add_column('contents', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('contents', sa.Column('longitude', sa.Float(), nullable=True))
    op.create_table('visits',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('content_id', sa.Integer(), sa.ForeignKey('contents.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('visited_at', sa.DateTime(), nullable=False))
    op.create_table('collection_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('collected_count', sa.Integer(), nullable=False),
        sa.Column('error_code', sa.String(100), nullable=False))


def downgrade():
    op.drop_table('collection_runs')
    op.drop_table('visits')
    op.drop_column('contents', 'longitude')
    op.drop_column('contents', 'latitude')
    op.drop_column('users', 'preferences')
