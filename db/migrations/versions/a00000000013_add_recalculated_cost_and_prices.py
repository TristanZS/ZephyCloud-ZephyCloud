# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add recalculated cost and prices

Revision ID: a00000000013
Revises: a00000000012
Create Date: 2019-12-20 12:11:02.271248

"""

from alembic import op

# Revision identifiers, used by Alembic.
revision = 'a00000000013'
down_revision = 'a00000000012'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    conn.execute("""ALTER TABLE machine_prices_history ADD COLUMN auto_update BOOL NOT NULL DEFAULT TRUE""")
    conn.execute("""ALTER TABLE machine_prices_history ADD COLUMN auto_priced BOOL NOT NULL DEFAULT FALSE""")

    conn.execute("""ALTER TABLE machine_prices ADD COLUMN auto_update BOOL NOT NULL DEFAULT TRUE""")
    conn.execute("""ALTER TABLE machine_prices ADD COLUMN auto_priced BOOL NOT NULL DEFAULT FALSE""")

    conn.execute("""CREATE TABLE machine_price_auto_update (
                            machine_price_id    BIGINT NOT NULL,
                            cost_id             BIGINT NOT NULL,
                            to_zcoins           FLOAT NOT NULL
                    )""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uidx_mpau_id ON machine_price_auto_update(machine_price_id)""")
    conn.execute("""INSERT INTO machine_price_auto_update(machine_price_id, cost_id, to_zcoins) 
                        SELECT mp.id AS machine_price_id, 
                               pc.id AS cost_id, 
                               cer.to_zcoins AS to_zcoins
                          FROM machine_prices AS mp
                          LEFT JOIN provider_costs AS pc
                                 ON mp.machine_uid = pc.machine_uid
                          JOIN currency_exchange_rates AS cer
                                 ON pc.currency = cer.currency
                          WHERE mp.auto_update = TRUE
                            AND mp.id NOT IN (
                                SELECT machine_price_id 
                                  FROM machine_price_auto_update )""")

def downgrade():
    conn = op.get_bind()

    conn.execute("""DROP TABLE machine_price_auto_update;""")

    conn.execute("""ALTER TABLE machine_prices DROP COLUMN auto_priced""")
    conn.execute("""ALTER TABLE machine_prices DROP COLUMN auto_update""")
    conn.execute("""ALTER TABLE machine_prices_history DROP COLUMN auto_priced""")
    conn.execute("""ALTER TABLE machine_prices_history DROP COLUMN auto_update""")


