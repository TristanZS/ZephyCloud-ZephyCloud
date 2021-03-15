# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add user email column

Revision ID: a00000000009
Revises: a00000000008
Create Date: 2019-09-20 12:10:02.271248

"""

from alembic import op
import os
import pickle

# Revision identifiers, used by Alembic.
revision = 'a00000000009'
down_revision = 'a00000000008'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0] + '.pickle')


def upgrade():
    conn = op.get_bind()

    # Add column without contraints
    conn.execute("""ALTER TABLE users ADD COLUMN email TEXT DEFAULT NULL""")

    # Restore backups if we have them
    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            for line in data:
                conn.execute("""UPDATE users SET email = %s WHERE id = %s AND email IS NULL""", [line[0], line[1]])

def downgrade():
    conn = op.get_bind()

    emails = conn.execute('SELECT email, id FROM users').fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(emails, f)

    conn.execute("ALTER TABLE users DROP COLUMN email")
