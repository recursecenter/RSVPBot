"""rename table to events

Revision ID: 753e7343bbf9
Revises: ca2cae2681ac
Create Date: 2017-05-18 10:48:31.944823

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '753e7343bbf9'
down_revision = 'ca2cae2681ac'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('event', 'events')


def downgrade():
    op.rename_table('events', 'event')
