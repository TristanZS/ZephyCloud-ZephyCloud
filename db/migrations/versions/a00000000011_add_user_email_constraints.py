# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add user email constraints

Revision ID: a00000000011
Revises: a00000000010
Create Date: 2019-09-20 12:10:02.271248

"""

from alembic import op

# Revision identifiers, used by Alembic.
revision = 'a00000000011'
down_revision = 'a00000000010'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    conn.execute("""ALTER TABLE users ALTER COLUMN email SET NOT NULL""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_u_email_delete ON users (email)
                         WHERE delete_date IS NULL""")

def downgrade():
    conn = op.get_bind()

    conn.execute("""ALTER TABLE users ALTER COLUMN email DROP NOT NULL;""")
    conn.execute("""DROP INDEX IF EXISTS uidx_u_email_delete""")
