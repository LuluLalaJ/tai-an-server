"""simplify enrollment status

Revision ID: 7fc6891b06ec
Revises: c85b6dba8f44
Create Date: 2023-06-19 10:05:57.517433

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7fc6891b06ec'
down_revision = 'c85b6dba8f44'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.Enum('registered', 'waitlisted', name='enrollment_status'), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_column('status')

    # ### end Alembic commands ###
