# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Create worker table

Revision ID: a00000000016
Revises: a00000000015
Create Date: 2020-01-19 12:11:02.271249

"""

from alembic import op

# Revision identifiers, used by Alembic.
revision = 'a00000000016'
down_revision = 'a00000000015'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    conn.execute(""" CREATE TABLE IF NOT EXISTS workers (
                                            worker_id           TEXT NOT NULL PRIMARY KEY,
                                            job_id              BIGINT NOT NULL,
                                            port                INT NOT NULL
                                    )""")


def downgrade():
    conn = op.get_bind()
    conn.execute("DROP TABLE workers")
