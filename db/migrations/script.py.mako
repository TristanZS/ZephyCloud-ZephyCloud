# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

import os
import pickle
from alembic import op
${imports if imports else ""}

# Revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

# Define backup file
data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')

# Function to implement to make changes to the database structure/data
def upgrade():
    # You can do import of project source code here
    # ex: import lib.utils

    conn = op.get_bind()
    ${upgrades if upgrades else "pass"}
    
    # You can use raw SQL to generate tables, or whatever
    #
    # conn.execute(""" CREATE TABLE table_example (
    #                        id INTEGER PRIMARY KEY AUTOINCREMENT,
    #                        data TEXT NOT NULL
    #             )""")

    # You can restore backuped data if any:
    #
    # if os.path.exists(bkp_data_file):
    #     with open(bkp_data_file, 'r') as f:
    #         data = pickle.load(f)
    #     for line in data:
    #         conn.execute("""INSERT INTO table_example (id, data) VALUES (?, ?)""", line)


# Function to implement to reverse changes defined in the upgrade() function
def downgrade():
    # You can do import of project source code here
    # ex: import lib.utils

    conn = op.get_bind()
    ${downgrades if downgrades else "pass"}

    # You can save old table data like this:
    #
    # results = conn.execute('SELECT * FROM table_example').fetchall()
    # with open(bkp_data_file, 'w') as f:
    #    pickle.dump(results, f)

    # And then you can remove table or column:
    #
    # conn.execute("DROP TABLE table_example")


