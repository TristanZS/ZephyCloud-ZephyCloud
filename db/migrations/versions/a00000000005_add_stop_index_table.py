# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add spot index table

Revision ID: a00000000005
Revises: a00000000004
Create Date: 2018-13-09 12:10:02.271248

"""

from alembic import op
import os
import pickle

# Revision identifiers, used by Alembic.
revision = 'a00000000005'
down_revision = 'a00000000004'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')


def upgrade():
    conn = op.get_bind()

    conn.execute(""" CREATE TABLE IF NOT EXISTS spot_indexes (
                                        provider_code             TEXT NOT NULL,
                                        machine_code              TEXT NOT NULL,
                                        value                     FLOAT NOT NULL DEFAULT 1.0
                                )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_si_pc_mc ON spot_indexes(provider_code, machine_code)""")

    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            for line in data:
                query = """INSERT INTO spot_indexes 
                                VALUES (%s, %s, %s)
                           ON CONFLICT (provider_code, machine_code) 
                              DO UPDATE SET value = EXCLUDED.value"""
                conn.execute(query, [line[0], line[1], line[3]])


def downgrade():
    conn = op.get_bind()

    results = conn.execute('SELECT provider_code, machine_code, value FROM spot_indexes').fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(results, f)

    conn.execute("DROP TABLE spot_indexes")
