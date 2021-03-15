# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add last_report Table

Revision ID: a00000000007
Revises: a00000000006
Create Date: 2019-05-20 12:10:02.271248

"""

from alembic import op
import os
import pickle

# Revision identifiers, used by Alembic.
revision = 'a00000000007'
down_revision = 'a00000000006'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')


def upgrade():
    conn = op.get_bind()
    conn.execute("CREATE TABLE IF NOT EXISTS last_report (report_date TIMESTAMP NOT NULL)")
    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            conn.execute("DELETE FROM last_report")
            for line in data:
                conn.execute("INSERT INTO last_report VALUES (%s)", [line[0]])


def downgrade():
    conn = op.get_bind()
    results = conn.execute('SELECT report_date FROM last_report').fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(results, f)
    conn.execute("DROP TABLE last_report")
