"""add chat system schema

Revision ID: b98676d99e72
Revises: 756c955076b1
Create Date: 2025-08-05 18:45:48.686744

"""
from typing import Sequence, Union
import os
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b98676d99e72'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    sql_file = os.path.join(os.path.dirname(__file__), '0002_add_chat_schema.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        op.execute(f.read())

def downgrade() -> None:
    """Downgrade schema."""
    pass
