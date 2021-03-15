# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Initial migration

Revision ID: e00000000009
Revises: 
Create Date: 2017-04-01 18:12:41.973199

"""
# Allow to include our own source code
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e00000000009'
down_revision = None
branch_labels = None
depends_on = None


# This stage is an empty database.
# It ensure there is nothing in the database


def upgrade():
    # Clean all tables (except alembic one)
    conn = op.get_bind()
    result = conn.execute("""
              SELECT name 
                FROM sqlite_master 
               WHERE type = 'table'
                 AND name NOT IN ('alembic_version', 'sqlite_sequence')""").fetchall()
    for line in result:
        conn.execute("DROP TABLE '" + line[0] + "'")


def downgrade():
    # Clean all tables (except alembic one)
    conn = op.get_bind()
    result = conn.execute("""
          SELECT name 
            FROM sqlite_master 
           WHERE type = 'table' 
             AND name NOT IN ('alembic_version', 'sqlite_sequence')""").fetchall()
    for line in result:
        conn.execute("DROP TABLE '"+line[0]+"'")

