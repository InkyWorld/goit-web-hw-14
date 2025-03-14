"""Change date_of_birth column to Date

Revision ID: 891c79e22a29
Revises: 5a6a2843c158
Create Date: 2025-02-20 14:03:51.501312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '891c79e22a29'
down_revision: Union[str, None] = '5a6a2843c158'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Alter the column using the USING clause for explicit casting
    op.execute('''
        ALTER TABLE contacts 
        ALTER COLUMN date_of_birth TYPE DATE
        USING date_of_birth::DATE;
    ''')

def downgrade():
    # If downgrading, revert the column back to VARCHAR(10) with casting to string
    op.execute('''
        ALTER TABLE contacts 
        ALTER COLUMN date_of_birth TYPE VARCHAR(10)
        USING date_of_birth::VARCHAR;
    ''')