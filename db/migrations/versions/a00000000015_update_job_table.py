# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Update job table

Revision ID: a00000000015
Revises: a00000000014
Create Date: 2020-01-19 12:11:02.271248

"""

from alembic import op

# Revision identifiers, used by Alembic.
revision = 'a00000000015'
down_revision = 'a00000000014'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    conn.execute("""ALTER TABLE jobs ADD COLUMN launch_params JSON NOT NULL DEFAULT '{}'""")
    conn.execute("""ALTER TABLE jobs ALTER COLUMN operation_id SET NOT NULL""")
    conn.execute("""ALTER TABLE jobs ADD COLUMN should_start BOOLEAN NOT NULL DEFAULT FALSE""")
    conn.execute("""ALTER TABLE jobs ADD COLUMN should_cancel BOOLEAN NOT NULL DEFAULT FALSE""")
    conn.execute("""ALTER TABLE jobs ADD COLUMN run_job_pid INT DEFAULT NULL""")
    conn.execute("""ALTER TABLE jobs ADD COLUMN monitoring_port INT DEFAULT NULL""")


def downgrade():
    conn = op.get_bind()
    conn.execute("""ALTER TABLE jobs DROP COLUMN monitoring_port""")
    conn.execute("""ALTER TABLE jobs DROP COLUMN run_job_pid""")
    conn.execute("""ALTER TABLE jobs DROP COLUMN should_cancel""")
    conn.execute("""ALTER TABLE jobs DROP COLUMN should_start""")
    conn.execute("""ALTER TABLE jobs ALTER COLUMN operation_id DROP NOT NULL""")
    conn.execute("""ALTER TABLE jobs DROP COLUMN launch_params""")
