"""change phone to string

Revision ID: 9f5f5ac09f7d
Revises: f1dd3c65a5aa
Create Date: 2023-06-12 16:05:41.980590

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f5f5ac09f7d'
down_revision = 'f1dd3c65a5aa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.alter_column('phone',
               existing_type=sa.INTEGER(),
               type_=sa.String(),
               existing_nullable=True)

    with op.batch_alter_table('teachers', schema=None) as batch_op:
        batch_op.alter_column('phone',
               existing_type=sa.INTEGER(),
               type_=sa.String(),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('teachers', schema=None) as batch_op:
        batch_op.alter_column('phone',
               existing_type=sa.String(),
               type_=sa.INTEGER(),
               existing_nullable=True)

    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.alter_column('phone',
               existing_type=sa.String(),
               type_=sa.INTEGER(),
               existing_nullable=True)

    # ### end Alembic commands ###
