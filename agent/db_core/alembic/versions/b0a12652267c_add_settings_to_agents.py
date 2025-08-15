"""Add settings to agents

Revision ID: b0a12652267c
Revises: b98676d99e72
Create Date: 2025-08-06 04:56:59.071399

"""
from typing import Sequence, Union
import sqlalchemy.dialects.postgresql as psql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0a12652267c'
down_revision: Union[str, Sequence[str], None] = 'b98676d99e72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('agents', sa.Column('settings', psql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))

def downgrade() -> None:
    """Downgrade schema."""
    pass
