# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Add currency exchange rate table

Revision ID: a00000000012
Revises: a00000000011
Create Date: 2019-12-20 12:10:02.271248

"""

from alembic import op
import os, pickle, json

# Revision identifiers, used by Alembic.
revision = 'a00000000012'
down_revision = 'a00000000011'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')

DOLLAR_TO_EURO = 0.85
YUAN_TO_EURO = 0.13
WEST_PRICE = 4.0
CHINA_PRICE = 30.0

def upgrade():
    conn = op.get_bind()

    conn.execute("""CREATE TABLE currency_exchange_rates (
                                    currency                    TEXT NOT NULL PRIMARY KEY,
                                    to_zcoins                   FLOAT NOT NULL,
                                    is_fixed                    BOOL DEFAULT FALSE  
                    ) """)
    if os.path.exists(bkp_data_file):
        with open(bkp_data_file, 'r') as f:
            data = pickle.load(f)
            for line in data:
                query = """INSERT INTO currency_exchange_rates VALUES (%s, %s, %s)"""
                conn.execute(query, [line[0], line[1], line[2]])
    else:
        if "MIGRATION_PROVIDERS" in os.environ and os.environ["MIGRATION_PROVIDERS"].strip():
            providers = json.loads(os.environ["MIGRATION_PROVIDERS"].strip())
        else:
            providers = ["docker_local"]

        if "aws_cn" in providers:
            conn.execute("""INSERT INTO currency_exchange_rates VALUES (%s, %s, %s)""", ["yuan", 1.0/CHINA_PRICE, True])
            conn.execute("""INSERT INTO currency_exchange_rates VALUES (%s, %s)""", ["euro", 1.0/CHINA_PRICE / YUAN_TO_EURO])
            conn.execute("""INSERT INTO currency_exchange_rates VALUES (%s, %s)""", ["dollar", 1.0/CHINA_PRICE / YUAN_TO_EURO * DOLLAR_TO_EURO])

        else:
            conn.execute("""INSERT INTO currency_exchange_rates VALUES (%s, %s, %s)""", ["euro", 1.0/WEST_PRICE, True])
            conn.execute("""INSERT INTO currency_exchange_rates VALUES (%s, %s)""", ["dollar", 1.0/WEST_PRICE * DOLLAR_TO_EURO])
            conn.execute("""INSERT INTO currency_exchange_rates VALUES (%s, %s)""", ["yuan", 1.0/WEST_PRICE * YUAN_TO_EURO])

def downgrade():
    conn = op.get_bind()

    results = conn.execute('SELECT currency, to_zcoins, is_fixed FROM currency_exchange_rates').fetchall()
    with open(bkp_data_file, 'w') as f:
        pickle.dump(results, f)

    conn.execute("""DROP TABLE currency_exchange_rates""")
