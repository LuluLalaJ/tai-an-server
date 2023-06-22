"""add credit history


Revision ID: 03d8e78b330c
Revises: 543a76480cd6
Create Date: 2023-06-22 17:08:14.202761

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03d8e78b330c'
down_revision = '543a76480cd6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('lessoncredithistories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('old_credit', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('new_credit', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('memo', sa.String(), nullable=True),
    sa.Column('student_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], name=op.f('fk_lessoncredithistories_student_id_students')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lessoncredithistories'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('lessoncredithistories')
    # ### end Alembic commands ###