# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Initial migration

Revision ID: a00000000001
Revises: 
Create Date: 2017-04-01 18:12:41.973199

"""
# Allow to include our own source code
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a00000000001'
down_revision = None
branch_labels = None
depends_on = None


# This stage is an empty database.
# It ensure there is nothing in the database


def upgrade():
    # Clean all tables (except alembic one)
    conn = op.get_bind()
    result = conn.execute("""SELECT table_schema, table_name 
                               FROM information_schema.tables 
                              WHERE table_schema = '?' 
                              ORDER BY table_schema, table_name""", ['public']).fetchall()
    for line in result:
        if line[0] == "alembic_version":
            continue
        conn.execute("DROP TABLE IF EXISTS ? CASCADE", [line[0]])


def downgrade():
    # Clean all tables (except alembic one)
    conn = op.get_bind()
    result = conn.execute("""SELECT table_schema, table_name 
                               FROM information_schema.tables 
                              WHERE table_schema = '?' 
                              ORDER BY table_schema, table_name""", ['public']).fetchall()
    for line in result:
        if line[0] == "alembic_version":
            continue
        conn.execute("DROP TABLE IF EXISTS ? CASCADE", [line[0]])



