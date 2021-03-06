"""add emoji field

Revision ID: 56b367e3d0fc
Revises: 24588099b7d7
Create Date: 2022-07-22 22:05:44.651336

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '56b367e3d0fc'
down_revision = '24588099b7d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('categories', sa.Column('emoji', sa.String(length=1), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('categories', 'emoji')
    # ### end Alembic commands ###
