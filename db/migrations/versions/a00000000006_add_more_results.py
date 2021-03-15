# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add more results

Revision ID: a00000000006
Revises: a00000000005
Create Date: 2019-01-23 12:10:02.271248

"""

from alembic import op
import os
import pickle

# Revision identifiers, used by Alembic.
revision = 'a00000000006'
down_revision = 'a00000000005'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')


def upgrade():
    conn = op.get_bind()

    conn.execute("""ALTER TABLE calculations ADD COLUMN iterations_file_id BIGINT DEFAULT NULL""")
    conn.execute("""ALTER TABLE calculations ADD COLUMN reduce_file_id BIGINT DEFAULT NULL""")

    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            for line in data:
                query = """UPDATE calculations SET 
                                iterations_file_id = %s, 
                                reduce_file_id = %s
                            WHERE id = %s"""
                conn.execute(query, [line[0], line[1], line[3]])


def downgrade():
    conn = op.get_bind()

    results = conn.execute("""SELECT iterations_file_id, reduce_file_id, id 
                                FROM calculations
                                WHERE iterations_file_id IS NOT NULL
                                   OR reduce_file_id IS NOT NULL""").fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(results, f)

    conn.execute("ALTER TABLE calculations DROP COLUMN iterations_file_id")
    conn.execute("ALTER TABLE calculations DROP COLUMN reduce_file_id")
