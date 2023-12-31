"""add column to enrollment

Revision ID: 543a76480cd6
Revises: 7fc6891b06ec
Create Date: 2023-06-19 12:23:11.562924

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '543a76480cd6'
down_revision = '7fc6891b06ec'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('comment', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_column('comment')

    # ### end Alembic commands ###
