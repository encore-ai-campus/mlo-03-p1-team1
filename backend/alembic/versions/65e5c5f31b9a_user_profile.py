"""Add optional user demographics without changing existing accounts."""
from alembic import op
import sqlalchemy as sa

revision = '65e5c5f31b9a'
down_revision = '30943449ef19'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('gender', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('age_recorded_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('residence', sa.String(30), nullable=True))
    op.add_column('users', sa.Column('occupation', sa.String(80), nullable=True))
    op.add_column('users', sa.Column('mbti', sa.String(4), nullable=True))
    op.create_check_constraint('ck_user_age', 'users', 'age BETWEEN 0 AND 120')


def downgrade():
    op.drop_constraint('ck_user_age', 'users', type_='check')
    for field in ('mbti', 'occupation', 'residence', 'age_recorded_at', 'age', 'gender'):
        op.drop_column('users', field)
