# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add job debug field

Revision ID: a00000000004
Revises: a00000000003
Create Date: 2018-05-09 12:10:02.271248

"""

from alembic import op
import os
import pickle

# Revision identifiers, used by Alembic.
revision = 'a00000000004'
down_revision = 'a00000000003'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')


def upgrade():
    conn = op.get_bind()

    conn.execute("""ALTER TABLE jobs ADD COLUMN debug BOOLEAN""")
    conn.execute("""UPDATE jobs SET debug = %s""", [False])

    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            for line in data:
                conn.execute("""UPDATE jobs SET debug = %s WHERE id = %s""", [line[0], line[1]])

    conn.execute("""ALTER TABLE jobs ALTER COLUMN debug SET NOT NULL""")
    conn.execute("""ALTER TABLE jobs ALTER COLUMN debug SET DEFAULT FALSE""")


def downgrade():
    conn = op.get_bind()

    results = conn.execute('SELECT debug, id FROM jobs').fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(results, f)

    conn.execute("ALTER TABLE jobs DROP COLUMN debug")
