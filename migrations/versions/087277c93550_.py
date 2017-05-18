"""add title to event

Revision ID: 087277c93550
Revises: d4d0517e8385
Create Date: 2017-05-16 12:07:21.806860

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '087277c93550'
down_revision = 'd4d0517e8385'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('event', sa.Column('title', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('event', 'title')
    # ### end Alembic commands ###
