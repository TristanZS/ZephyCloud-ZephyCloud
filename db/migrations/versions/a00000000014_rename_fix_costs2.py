# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Rename fix costs, version 2

Revision ID: a00000000014
Revises: a00000000013
Create Date: 2019-12-20 12:11:02.271248

"""

from alembic import op
import pickle, os

# Revision identifiers, used by Alembic.
revision = 'a00000000014'
down_revision = 'a00000000013'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')

def upgrade():
    conn = op.get_bind()

    results = conn.execute("""SELECT id, description
                                FROM user_accounts""").fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(results, f)

    conn.execute("""UPDATE user_accounts
                       SET description = %s
                     WHERE description = %s""",
                 ["Mesh storage cost", "Mesh fixed cost"])
    conn.execute("""UPDATE user_accounts
                       SET description = %s
                     WHERE description = %s""",
                 ["Mesh storage cost", "mesh fixed cost"])

def downgrade():
    conn = op.get_bind()

    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            for line in data:
                query = """UPDATE user_accounts SET description = %s
                            WHERE id = %s"""
                conn.execute(query, [line[1], line[0]])


