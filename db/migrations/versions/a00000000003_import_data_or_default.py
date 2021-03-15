# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Import data or default values

Revision ID: a00000000003
Revises: a00000000002
Create Date: 2018-05-07 22:22:04.315349

"""

from alembic import op, context
import math
import os
import json
import sys
import datetime
import hashlib
import string
import random


# Revision identifiers, used by Alembic.
revision = 'a00000000003'
down_revision = 'a00000000002'
branch_labels = None
depends_on = None


# Default values constants
RANK_BRONZE = 1
RANK_SILVER = 2
RANK_GOLD = 3
RANK_ROOT = 4

AWS_GRANULARITY = 1
AWS_MIN_GRANULARITY = 60
ZEPHYCLOUD_GRANULARITY = 300

FIX_PRICES = {
    "anal": 0.10,
    "mesh": 0.05,
    "calc": 0.05,
    "rose": 0.05,
    "extra": 0.05,
    "assess": 0.05,
}

CLUSTER_LIMITS = {
    "anal": 1,
    "mesh": 1,
    "calc": 20,
    "rose": 1,
    "extra": 1,
    "assess": 1,
}

NEW_USERS = [{'login': 'tristan', 'pwd': 'tristan', 'rank': 3},
             {'login': 'sam', 'pwd': 'sam', 'rank': 3}]

AWS_WEST_MACHINES = {
    "c5.xlarge": {
        "cpu": 4,
        "ram": 8,
        "available": 400
    },
    "c5.2xlarge": {
        "cpu": 8,
        "ram": 16,
        "available": 400
    },
    "c5.4xlarge": {
        "cpu": 16,
        "ram": 32,
        "available": 400
    },
    "c5.9xlarge": {
        "cpu": 36,
        "ram": 72,
        "available": 400
    },
    "c5.18xlarge": {
        "cpu": 72,
        "ram": 144,
        "available": 400
    }
}

AWS_WEST_OLD_MACHINES = {
    "c4.xlarge": {
        "cpu": 4,
        "ram": 7.5,
        "available": 400
    },
    "c4.2xlarge": {
        "cpu": 8,
        "ram": 15,
        "available": 400
    },
    "c4.4xlarge": {
        "cpu": 16,
        "ram": 30,
        "available": 400
    },
    "c4.8xlarge": {
        "cpu": 36,
        "ram": 60,
        "available": 400
    },
    "x1.16xlarge": {
        "cpu": 64,
        "ram": 976,
        "available": 10
    }
}

AWS_WEST_VERY_OLD_MACHINES = {
    "c3.xlarge": {
        "cpu": 4,
        "ram": 7.5,
        "available": 400
    },
    "c3.2xlarge": {
        "cpu": 8,
        "ram": 15,
        "available": 400
    },
    "c3.4xlarge": {
        "cpu": 16,
        "ram": 30,
        "available": 400
    },
    "c3.8xlarge": {
        "cpu": 32,
        "ram": 60,
        "available": 400
    }
}

# aws_eu_old

AWS_CHINA_MACHINES = {
    "c4.2xlarge": {
        "cpu": 4,
        "ram": 15,
        "available": 400
    },
    "c4.4xlarge": {
        "cpu": 16,
        "ram": 30,
        "available": 400
    },
    "c4.8xlarge": {
        "cpu": 36,
        "ram": 60,
        "available": 400
    },
    "x1.16xlarge": {
        "cpu": 64,
        "ram": 976,
        "available": 10
    }
}

# prices are in dollar per hour
COST_PER_HOUR_EU = {
    "c5.xlarge": 0.192,
    "c5.2xlarge": 0.384,
    "c5.4xlarge": 0.768,
    "c5.9xlarge": 1.728,
    "c5.18xlarge": 3.456,
    "c4.xlarge": 0.226,
    "c4.2xlarge": 0.453,
    "c4.4xlarge": 0.905,
    "c4.8xlarge": 1.811,
    "x1.16xlarge": 8.003,
    "c3.xlarge": 0.239,
    "c3.2xlarge": 0.478,
    "c3.4xlarge": 0.956,
    "c3.8xlarge": 1.912
}

# prices are in yuan per hour
COST_PER_HOUR_CN = {
    "c4.2xlarge": 4.535,
    "c4.4xlarge": 9.071,
    "c4.8xlarge": 18.141,
    "x1.16xlarge": 137.752
}


SECURITY_MARGIN = 0.05
DONATION_RATIO = 0.05
DOLLAR_TO_EURO = 0.85
YUAN_TO_EURO = 0.13
WEST_PRICE = 4
CHINA_PRICE = 30

WEST_MARGIN = {
    'root': 1,
    'gold': 2,
    'silver': 4,
    'bronze': 10
}
CHINA_MARGIN = {
    'root': 1,
    'gold': 2,
    'silver': 10,
    'bronze': 30
}

DOCKER_MACHINES = {
    "docker": {
        "cpu": 2,
        "ram": 1,
        "available": 10
    },
    "docker_2": {
        "cpu": 4,
        "ram": 2,
        "available": 10
    }
}

# Fake dollar per hour
COST_PER_HOUR_DOCKER = {
    "docker": 0.192,
    "docker_2": 0.384,
}


def map_values(row, fields, table=None):
    result = []
    for field in fields:
        if row[field] is None:
            result.append(row[field])
        elif field in ('create_date', 'delete_date', 'change_date', 'start_time', 'end_time', 'computing_start',
                       'computing_end', 'date', 'last_start_date', 'last_stop_date'):
            result.append(datetime.datetime.utcfromtimestamp(int(float(row[field]))))
        else:
            result.append(row[field])
    return result


class SaltChars(object):
    chars = string.ascii_letters + string.digits


def generate_salt(length=12):
    """
    Generate a new salt string

    :param length:      The length of the salt to generate. Optional, default 12
    :type length:       int
    :return:            the generated salt
    :rtype:             str
    """
    salt = ''
    for i in range(length):
        salt += SaltChars.chars[random.randint(0, len(SaltChars.chars) - 1)]
    return salt




def upgrade():
    import core.api_util
    import lib.pg_util
    import sqlite3
    import logging
    import uuid

    def all_ranks():
        return RANK_BRONZE, RANK_SILVER, RANK_GOLD, RANK_ROOT

    def rank_to_str(rank):
        if rank == RANK_BRONZE:
            return "bronze"
        elif rank == RANK_SILVER:
            return "silver"
        elif rank == RANK_GOLD:
            return "gold"
        elif rank == RANK_ROOT:
            return "root"
        else:
            raise RuntimeError("Invalid rank: " + str(rank))

    def add_user_credits(amount, user_id, description):
        g_db = core.api_util.DatabaseContext.get_conn()
        with g_db.cursor() as cur:
            cur.execute("""INSERT INTO user_accounts (user_id, amount, description)
                                VALUES (%s, %s, %s)""",
                        [user_id, amount, description])
            g_db.commit()

    def get_machine(provider_name, machine_code):
        g_db = core.api_util.DatabaseContext.get_conn()
        return g_db.execute("SELECT * FROM machines WHERE provider_code = %s AND machine_code = %s",
                            [provider_name, machine_code]).fetchone()

    def list_machines(provider_name):
        g_db = core.api_util.DatabaseContext.get_conn()
        query = "SELECT * FROM machines WHERE provider_code = %s"
        result = g_db.execute(query, [provider_name]).fetchall()
        if not result:
            return []
        return lib.pg_util.all_to_dict(result)

    def set_machine_provider_cost(machine_uid, provider_price, provider_currency, provider_sec_granularity,
                                  provider_min_sec_granularity):
        g_db = core.api_util.DatabaseContext.get_conn()
        lib.pg_util.hist_upsert(g_db, "provider_costs",
                                values={
                                    "cost_per_sec": provider_price,
                                    "currency": provider_currency,
                                    "sec_granularity": provider_sec_granularity,
                                    "min_sec_granularity": provider_min_sec_granularity
                                },
                                where=[("machine_uid", "=", machine_uid)])

    def set_machine(provider_name, machine_code, nbr_cores, ram_size, nbr_available, provider_cost_per_sec,
                    provider_currency, provider_sec_granularity, provider_min_sec_granularity):
        g_db = core.api_util.DatabaseContext.get_conn()
        result = lib.pg_util.hist_upsert(g_db, "machines",
                                         values={
                                             "nbr_cores": nbr_cores,
                                             "ram_size": ram_size,
                                             "nbr_available": nbr_available,
                                         },
                                         where=[
                                             ("provider_code", "=", provider_name),
                                             ("machine_code", "=", machine_code)
                                         ],
                                         default_values={"uid": str(uuid.uuid4())})
        set_machine_provider_cost(result["uid"], provider_cost_per_sec, provider_currency, provider_sec_granularity,
                                  provider_min_sec_granularity)

    def set_machine_price(provider_name, machine_code, user_rank, price, sec_granularity, min_sec_granularity=None):
        if min_sec_granularity is None:
            min_sec_granularity = sec_granularity
        machine = get_machine(provider_name, machine_code)
        if machine is None:
            raise RuntimeError("Unknown machine " + str(machine_code))
        g_db = core.api_util.DatabaseContext.get_conn()
        with lib.pg_util.Transaction(g_db):
            lib.pg_util.hist_upsert(g_db, "machine_prices",
                                    values={
                                        "sec_price": price,
                                        "sec_granularity": sec_granularity,
                                        "min_sec_granularity": min_sec_granularity,
                                    },
                                    where=[
                                        ("machine_uid", "=", machine["uid"]),
                                        ("user_rank", "=", user_rank)
                                    ])

    def set_operation_cost(provider_name, operation_name, cost):
        g_db = core.api_util.DatabaseContext.get_conn()
        with lib.pg_util.Transaction(g_db):
            for rank in all_ranks():
                lib.pg_util.hist_upsert(g_db, "operations", values={"fixed_cost": cost},
                                    where=[("operation_name", "=", operation_name),
                                           ("provider_code", "=", provider_name),
                                           ("user_rank", "=", rank)])

    def set_operation_cluster_limit(provider_name, operation_name, cluster_limit):
        g_db = core.api_util.DatabaseContext.get_conn()
        with lib.pg_util.Transaction(g_db):
            for rank in all_ranks():
                lib.pg_util.hist_upsert(g_db, "operations", values={"cluster_limit": cluster_limit},
                                    where=[("operation_name", "=", operation_name),
                                           ("provider_code", "=", provider_name),
                                           ("user_rank", "=", rank)])

    def set_operation_machines(provider_name, operation_name, allowed_machines):
        g_db = core.api_util.DatabaseContext.get_conn()
        with lib.pg_util.Transaction(g_db):
            machines = list_machines(provider_name)
            existing_machine_codes = [m["machine_code"] for m in machines]
            for machine_code in allowed_machines:
                if machine_code not in existing_machine_codes:
                    raise RuntimeError("Unknown machine " + machine_code)
            count_op = g_db.execute("""SELECT count(*) 
                                               FROM operations
                                              WHERE operation_name = %s""",
                                    [operation_name]).fetchval()
            if count_op == 0:
                raise RuntimeError("Unknown operation " + str(operation_name))

            g_db.execute("""DELETE FROM operation_machine 
                                  WHERE operation_name = %s
                                    AND machine_uid IN (
                                           SELECT uid 
                                             FROM machines
                                            WHERE provider_code = %s)""",
                         [operation_name, provider_name])
            g_db.executemany("""INSERT INTO operation_machine (operation_name, machine_uid)
                                     SELECT %s, uid
                                       FROM machines
                                      WHERE machine_code = %s
                                        AND provider_code = %s""",
                             [(operation_name, x, provider_name) for x in allowed_machines])

    old_sqlite3_db_path = context.get_context().config.get_main_option("sqlite3_db_path")
    if old_sqlite3_db_path and os.path.exists(old_sqlite3_db_path):
        old_conn = sqlite3.connect(os.path.abspath(old_sqlite3_db_path))
        old_conn.row_factory = sqlite3.Row

        cursor = old_conn.cursor()

        all_tables = ["users", "machines", "machines_history", "machine_prices", "machine_prices_history",
                      "provider_costs", "provider_costs_history", "operations", "operations_history",
                      "operation_machine", "projects", "projects_history", "project_files", "user_accounts", "jobs",
                      "task_queue", "meshes", "calculations", "time_metrics"]

        tables_with_sequence = ["users", "machines_history", "machine_prices_history", "provider_costs_history",
                                "operations_history", "projects_history", "project_files", "user_accounts", "jobs",
                                "meshes", "calculations"]
        g_db = core.api_util.DatabaseContext.get_conn()
        for table in all_tables:
            cursor.execute("SELECT * FROM "+table)
            fields = [f[0] for f in cursor.description]
            if "delete_random" in fields:
                fields.remove("delete_random")

            try:
                if table in tables_with_sequence:
                    g_db.execute("BEGIN")
                    g_db.execute("LOCK TABLE "+table+" IN EXCLUSIVE MODE;")

                for result in cursor:
                    query = "INSERT INTO " + table + " ("+", ".join(fields)+") " + \
                            "     OVERRIDING SYSTEM VALUE " + \
                            "     VALUES (" + ", ".join(["%s"]*len(fields))+")"

                    values = map_values(result, fields, table)
                    try:
                        g_db.execute(query, values)
                    except:
                        logging.getLogger("alembic.runtime.migration").error("error while executing:")
                        logging.getLogger("alembic.runtime.migration").error(query)
                        logging.getLogger("alembic.runtime.migration").error(repr(values))
                        raise

                if table in tables_with_sequence:
                    g_db.execute("""SELECT setval(pg_get_serial_sequence('"""+table+"""', 'id'), 
                                                        COALESCE(MAX(id), 0) +1,
                                                        false)
                                            FROM """+table)
            except Exception:
                if table in tables_with_sequence:
                    g_db.execute("ROLLBACK")
                raise
            if table in "tables_with_sequence":
                g_db.execute("COMMIT")

        old_conn.close()
        return

    for user in NEW_USERS:
        g_db = core.api_util.DatabaseContext.get_conn()
        salt = generate_salt()
        h = hashlib.sha256()
        h.update(user['pwd'])
        h.update(salt)
        hex_dig = h.hexdigest()

        user_id = None
        with g_db.cursor() as cur:
            cur.execute("""INSERT INTO users (login, pwd, salt, user_rank) 
                                    VALUES (%s, %s, %s, %s)
                               RETURNING id""",
                        [user['login'], str(hex_dig), salt, user['rank']])
            user_id = cur.fetchone()[0]
            g_db.commit()
        add_user_credits(core.api_util.price_from_float(500), user_id, "Initial credit for users")

    try:
        providers = json.loads(context.get_context().config.get_main_option("providers"))
    except StandardError as e:
        sys.stderr.write(os.linesep + "Warning: "+str(e)+os.linesep)
        sys.stderr.flush()
        providers = None

    if not providers:
        providers = ["docker_local"]

    if "aws_eu" in providers:
        for machine, details in AWS_WEST_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_EU[machine] / 3600)
            set_machine("aws_eu", machine, details["cpu"],
                        core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                        cost, core.api_util.CURRENCY_DOLLAR,
                        AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            set_machine("aws_eu_spot", machine, details["cpu"],
                        core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                        int(math.ceil(float(cost) / 2)), core.api_util.CURRENCY_DOLLAR,
                        AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            if machine not in COST_PER_HOUR_EU.keys():
                continue
            ref_price = float(COST_PER_HOUR_EU[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in all_ranks():
                rank_str = rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                set_machine_price("aws_eu", machine, rank, price, ZEPHYCLOUD_GRANULARITY)
                set_machine_price("aws_eu_spot", machine, rank, math.ceil(price / 2), ZEPHYCLOUD_GRANULARITY)

        for operation, price in FIX_PRICES.items():
            set_operation_cost("aws_eu", operation, core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_eu", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("aws_eu", operation, AWS_WEST_MACHINES.keys())
            set_operation_cost("aws_eu_spot", operation, core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_eu_spot", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("aws_eu_spot", operation, AWS_WEST_MACHINES.keys())

    if "aws_eu_old" in providers:
        for machine, details in AWS_WEST_OLD_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_EU[machine] / 3600)
            set_machine("aws_eu_old", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            set_machine("aws_eu_old_spot", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               int(math.ceil(float(cost) / 2)), core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_EU[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in all_ranks():
                rank_str = rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                set_machine_price("aws_eu_old", machine, rank, price, ZEPHYCLOUD_GRANULARITY)
                set_machine_price("aws_eu_old_spot", machine, rank, math.ceil(price / 2),
                                                         ZEPHYCLOUD_GRANULARITY)
        for operation, price in FIX_PRICES.items():
            set_operation_cost("aws_eu_old", operation, core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_eu_old", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("aws_eu_old", operation, AWS_WEST_OLD_MACHINES.keys())
            set_operation_cost("aws_eu_old_spot", operation,
                                                      core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_eu_old_spot", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("aws_eu_old_spot", operation, AWS_WEST_OLD_MACHINES.keys())

    if "aws_eu_very_old" in providers:
        for machine, details in AWS_WEST_VERY_OLD_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_EU[machine] / 3600)
            set_machine("aws_eu_very_old", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            set_machine("aws_eu_very_old_spot", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               int(math.ceil(float(cost) / 2)), core.api_util.CURRENCY_DOLLAR,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_EU[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in all_ranks():
                rank_str = rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                set_machine_price("aws_eu_very_old", machine, rank, price,
                                                         ZEPHYCLOUD_GRANULARITY)
                set_machine_price("aws_eu_very_old_spot", machine, rank, math.ceil(price / 2),
                                                         ZEPHYCLOUD_GRANULARITY)
        for operation, price in FIX_PRICES.items():
            set_operation_cost("aws_eu_very_old", operation,
                                                      core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_eu_very_old", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("aws_eu_very_old", operation,
                                                          AWS_WEST_VERY_OLD_MACHINES.keys())
            set_operation_cost("aws_eu_very_old_spot", operation,
                                                      core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_eu_very_old_spot", operation,
                                                               CLUSTER_LIMITS[operation])
            set_operation_machines("aws_eu_very_old_spot", operation,
                                                          AWS_WEST_VERY_OLD_MACHINES.keys())

    if "aws_cn" in providers:
        for machine, details in AWS_CHINA_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_CN[machine] / 3600)
            set_machine("aws_cn", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_YUAN,
                                               AWS_GRANULARITY, AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_CN[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in all_ranks():
                rank_str = rank_to_str(rank)
                if rank_str not in CHINA_MARGIN:
                    pass
                float_price = ref_price * float(CHINA_MARGIN[rank_str]) * YUAN_TO_EURO / float(CHINA_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                set_machine_price("aws_cn", machine, rank, price, ZEPHYCLOUD_GRANULARITY)

        for operation, price in FIX_PRICES.items():
            set_operation_cost("aws_cn", operation, core.api_util.price_from_float(price))
            set_operation_cluster_limit("aws_cn", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("aws_cn", operation, AWS_CHINA_MACHINES.keys())

    if "docker_local" in providers:
        for machine, details in DOCKER_MACHINES.items():
            cost = core.api_util.price_from_float(COST_PER_HOUR_DOCKER[machine] / 3600)
            set_machine("docker_local", machine, details["cpu"],
                                               core.api_util.gbytes_to_bytes(details["ram"]), details["available"],
                                               cost, core.api_util.CURRENCY_DOLLAR, AWS_GRANULARITY,
                                               AWS_MIN_GRANULARITY)
            ref_price = float(COST_PER_HOUR_DOCKER[machine]) * (1.0 + SECURITY_MARGIN + DONATION_RATIO)
            for rank in all_ranks():
                rank_str = rank_to_str(rank)
                if rank_str not in WEST_MARGIN:
                    pass
                float_price = ref_price * float(WEST_MARGIN[rank_str]) * DOLLAR_TO_EURO / float(WEST_PRICE)
                price = core.api_util.price_from_float(float_price / 3600)
                set_machine_price("docker_local", machine, rank, price, ZEPHYCLOUD_GRANULARITY)

        for operation, price in FIX_PRICES.items():
            set_operation_cost("docker_local", operation, core.api_util.price_from_float(price))
            set_operation_cluster_limit("docker_local", operation, CLUSTER_LIMITS[operation])
            set_operation_machines("docker_local", operation, DOCKER_MACHINES.keys())


def downgrade():
    conn = op.get_bind()
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM machines")
    conn.execute("DELETE FROM machines_history")
    conn.execute("DELETE FROM operation_machine")
    conn.execute("DELETE FROM machine_prices")
    conn.execute("DELETE FROM machine_prices_history")
