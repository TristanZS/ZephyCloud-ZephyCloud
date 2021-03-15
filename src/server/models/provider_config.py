# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120


# Python core libs
import logging
import uuid
import copy
import math

# Third party libs
import requests

# Project libs
from lib import pg_util
from lib import util
import users
import currencies
import core.api_util

log = logging.getLogger("aziugo")

# ----------------------- Operations -----------------------------------------------------------------------------------

@core.api_util.need_db_context
def get_operation(provider_name, operation, user_rank=users.RANK_BRONZE, include_machines=False):
    g_db = core.api_util.DatabaseContext.get_conn()
    if not include_machines:
        return pg_util.row_to_dict(g_db.execute("""SELECT * FROM operations
                                                    WHERE operation_name = %s
                                                      AND provider_code = %s
                                                      AND user_rank = %s""",
                                                [operation, provider_name, user_rank]).fetchone())
    else:
        req = g_db.execute("""SELECT o.*, ARRAY_REMOVE(ARRAY_AGG(m.machine_code), NULL) AS machines
                                FROM operations AS o
                                LEFT JOIN operation_machine AS om 
                                       ON  o.operation_name = om.operation_name
                                LEFT JOIN machines AS m 
                                       ON  om.machine_uid = m.uid
                                       AND o.provider_code = m.provider_code
                                WHERE o.operation_name = %s
                                  AND o.provider_code = %s
                                  AND o.user_rank = %s  
                                GROUP BY o.id, o.provider_code, o.operation_name, o.user_rank""",
                           [operation, provider_name, user_rank]).fetchone()
        return pg_util.row_to_dict(req)


@core.api_util.need_db_context
def get_operation_by_id(operation_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM operations_history WHERE id = %s", [operation_id]).fetchone()


@core.api_util.need_db_context
def list_operations(provider_name, user_rank=users.RANK_BRONZE, include_machines=False, at=None, offset=0, limit=None,
                    order=None):
    if not include_machines:
        if not at:
            query = """SELECT * FROM operations
                        WHERE provider_code = %s
                          AND user_rank = %s"""
        else:
            query = """SELECT * FROM operations_history
                        WHERE provider_code = %s
                          AND user_rank = %s
                          AND start_time <= %s
                          AND (end_time > %s OR end_time IS NULL)"""
    elif not at:
        query = """SELECT o.*, ARRAY_REMOVE(ARRAY_AGG(m.machine_code), NULL) AS machines
                     FROM operations AS o
                     LEFT JOIN operation_machine AS om 
                            ON o.operation_name = om.operation_name
                     LEFT JOIN machines AS m 
                            ON om.machine_uid = m.uid
                           AND o.provider_code = m.provider_code
                    WHERE o.provider_code = %s
                      AND o.user_rank = %s  
                    GROUP BY o.id, o.provider_code, o.operation_name, o.user_rank"""
    else:
        query = """SELECT o.*, ARRAY_REMOVE(ARRAY_AGG(m.machine_code), NULL) AS machines
                     FROM operations_history AS o
                     LEFT JOIN operation_machine AS om 
                            ON o.operation_name = om.operation_name
                     LEFT JOIN machines_history AS m 
                            ON om.machine_uid = m.uid
                           AND o.provider_code = m.provider_code
                    WHERE o.provider_code = %s
                      AND o.user_rank = %s  
                      AND o.start_time <= %s
                      AND (o.end_time > %s OR o.end_time IS NULL)
                      AND m.start_time <= %s
                      AND (m.end_time > %s OR m.end_time IS NULL)
                    GROUP BY o.id, o.provider_code, o.operation_name, o.user_rank"""

    if order:
        if include_machines:
            query += " "+order.to_sql({"name": "operation_name", "fixed_price": "fixed_cost",
                                       "machine_limit": "cluster_limit"})
        else:
            query += " " + order.to_sql({"name": "o.operation_name", "fixed_price": "o.fixed_cost",
                                        "machine_limit": "o.cluster_limit"})

    if limit:
        query += " LIMIT "+str(int(limit))
    if offset:
        query += " OFFSET "+str(int(offset))
    g_db = core.api_util.DatabaseContext.get_conn()
    if not include_machines:
        if not at:
            return g_db.execute(query, [provider_name, user_rank]).fetchall()
        else:
            return g_db.execute(query, [provider_name, user_rank, at, at]).fetchall()

    if not at:
        req = g_db.execute(query, [provider_name, user_rank]).fetchall()
    else:
        req = g_db.execute(query, [provider_name, user_rank, at, at, at, at]).fetchall()
    return pg_util.all_to_dict(req)


@core.api_util.need_db_context
def set_operation_cost(provider_name, operation_name, cost):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        for rank in users.all_ranks():
            pg_util.hist_upsert(g_db, "operations", values={"fixed_cost": cost},
                                    where=[("operation_name", "=", operation_name),
                                       ("provider_code", "=", provider_name),
                                       ("user_rank", "=", rank)])


@core.api_util.need_db_context
def set_operation_cluster_limit(provider_name, operation_name, cluster_limit):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        for rank in users.all_ranks():
            pg_util.hist_upsert(g_db, "operations", values={"cluster_limit": cluster_limit},
                                where=[("operation_name", "=", operation_name),
                                       ("provider_code", "=", provider_name),
                                       ("user_rank", "=", rank)])


@core.api_util.need_db_context
def set_operation_machines(provider_name, operation_name, allowed_machines):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
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


@core.api_util.need_db_context
def add_machine_to_operation(provider_name, operation_name, machine_code):
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""INSERT INTO operation_machine (operation_name, machine_uid)
                         SELECT %s, uid
                           FROM machines
                          WHERE machine_code = %s
                            AND provider_code = %s""",
                 [operation_name, machine_code, provider_name])


# ----------------------- Machines -------------------------------------------------------------------------------------

@core.api_util.need_db_context
def get_machine(provider_name, machine_code):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM machines WHERE provider_code = %s AND machine_code = %s",
                        [provider_name, machine_code]).fetchone()


@core.api_util.need_db_context
def get_machine_by_uid(machine_uid):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM machines_history WHERE uid = %s", [machine_uid]).fetchone()


@core.api_util.need_db_context
def list_machines(provider_name, at=None, offset=0, limit=None, order=None):
    if at:
        query = """SELECT * 
                     FROM machines_history 
                    WHERE provider_code = %s
                      AND start_time <= %s
                      AND (end_time > %s OR end_time IS NULL)"""
    else:
        query = "SELECT * FROM machines WHERE provider_code = %s"
    if order:
        query += " "+order.to_sql({"name": "machine_code", "cores": "nbr_cores", "ram": "ram_size",
                                   "availability": "nbr_available"})
    if limit:
        query += " LIMIT "+str(int(limit))
    if offset:
        query += " OFFSET "+str(int(offset))
    g_db = core.api_util.DatabaseContext.get_conn()
    if at:
        result = g_db.execute(query, [provider_name, at, at]).fetchall()
    else:
        result = g_db.execute(query, [provider_name]).fetchall()
    if not result:
        return []
    return pg_util.all_to_dict(result)


@core.api_util.need_db_context
def list_machine_operations(provider_name, machine_code, user_rank=users.RANK_BRONZE, at=None):
    g_db = core.api_util.DatabaseContext.get_conn()
    if not at:
        query = """SELECT o.*
                     FROM operations AS o
                     LEFT JOIN operation_machine AS om 
                            ON o.operation_name = om.operation_name
                     LEFT JOIN machines AS m 
                            ON om.machine_uid = m.uid
                           AND o.provider_code = m.provider_code
                    WHERE o.provider_code = %s
                      AND o.user_rank = %s
                      AND m.machine_code = %s"""
        result = g_db.execute(query, [provider_name, user_rank, machine_code]).fetchall()
        if not result:
            return []
        return pg_util.all_to_dict(result)
    else:
        query = """SELECT o.*
                     FROM operations_history AS o
                     LEFT JOIN operation_machine AS om 
                            ON o.operation_name = om.operation_name
                     LEFT JOIN machines_history AS m 
                            ON om.machine_uid = m.uid
                           AND o.provider_code = m.provider_code
                    WHERE o.provider_code = %s
                      AND o.user_rank = %s  
                      AND m.machine_code = %s
                      AND o.start_time <= %s
                      AND (o.end_time > %s OR o.end_time IS NULL)
                      AND m.start_time <= %s
                      AND (m.end_time > %s OR m.end_time IS NULL)"""
    g_db = core.api_util.DatabaseContext.get_conn()
    if at:
        result = g_db.execute(query, [provider_name, user_rank, machine_code, at, at, at, at]).fetchall()
    else:
        result = g_db.execute(query, [provider_name, user_rank, machine_code]).fetchall()
    if not result:
        return []
    return pg_util.all_to_dict(result)


@core.api_util.need_db_context
def set_machine(provider_name, machine_code, nbr_cores, ram_size, nbr_available, provider_cost_per_sec,
                provider_currency, provider_sec_granularity, provider_min_sec_granularity):
    g_db = core.api_util.DatabaseContext.get_conn()
    result = pg_util.hist_upsert(g_db, "machines",
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


@core.api_util.need_db_context
def set_machine_and_prices(provider_name, machine_code, nbr_cores, ram_size, nbr_available, provider_cost_per_sec,
                           provider_currency, provider_sec_granularity, provider_min_sec_granularity,
                           price_sec_granularity, price_min_sec_granularity, prices, auto_update):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        set_machine(provider_name, machine_code, nbr_cores, ram_size, nbr_available, provider_cost_per_sec,
                    provider_currency, provider_sec_granularity, provider_min_sec_granularity)
        for rank, price in prices.items():
            set_machine_price(provider_name, machine_code, rank, price, price_sec_granularity,
                              price_min_sec_granularity, auto_update)


@core.api_util.need_db_context
def update_machine(provider_name, machine_code, params):
    log.error("SAM: update_params: "+repr(params))
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        update_params = {}
        for param in ["nbr_cores", "ram_size", "nbr_available"]:
            if param in params.keys():
                update_params[param] = params[param]
        if update_params:
            results = pg_util.hist_update(g_db, "machines", values=update_params, where=[
                                                        ("provider_code", "=", provider_name),
                                                        ("machine_code", "=", machine_code)
                                                    ])
            machine_uid = results[0]["uid"]
        else:
            result = get_machine(provider_name, machine_code)
            machine_uid = result["uid"]

        update_params = {}
        for param in ["provider_cost_per_sec", "provider_currency", "provider_sec_granularity",
                      "provider_min_sec_granularity"]:
            update_params[param[len('provider_'):]] = params[param]
        if update_params:
            pg_util.hist_upsert(g_db, "provider_costs", update_params,
                                where=[("machine_uid", "=", machine_uid)])
        update_params = {}
        for param in ["provider_min_sec_granularity", "price_sec_granularity"]:
            update_params[param[len('price_'):]] = params[param]

        for rank in users.all_ranks():
            rank_update_params = copy.deepcopy(update_params)
            if "prices" in params and rank in params['prices']:
                rank_update_params['sec_price'] = params['prices'][rank]
            if "auto_update" in params:
                rank_update_params['auto_update'] = params['auto_update']
            log.error("SAM: rank_update_params: "+repr(rank_update_params))
            if rank_update_params:
                pg_util.hist_upsert(g_db, "machine_prices", values=rank_update_params, where=[
                                            ("machine_uid", "=", machine_uid),
                                            ("user_rank", "=", rank)
                                         ])
        if "auto_update" in params.keys():
            with pg_util.Transaction(g_db):
                g_db.execute("""DELETE FROM machine_price_auto_update 
                                         WHERE machine_price_id NOT IN (
                                            SELECT id FROM machine_prices
                                            WHERE auto_update = TRUE
                                         )""")
                g_db.execute("""INSERT INTO machine_price_auto_update(machine_price_id, cost_id, to_zcoins) 
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
            if params["auto_update"] and "prices" not in params.keys():
                update_machine_prices()


@core.api_util.need_db_context
def get_machine_provider_cost(provider_name, machine_code, at=None):
    g_db = core.api_util.DatabaseContext.get_conn()
    if at is None:
        return g_db.execute("""SELECT pc.* 
                                       FROM machines AS m
                                       LEFT JOIN provider_costs AS pc ON pc.machine_uid = m.uid
                                      WHERE m.provider_code = %s
                                        AND m.machine_code = %s""", [provider_name, machine_code]).fetchone()
    else:
        return g_db.execute("""SELECT pc.* 
                                       FROM machines_history AS m
                                       LEFT JOIN provider_costs_history AS pc ON pc.machine_uid = m.uid
                                      WHERE m.provider_code = %s
                                        AND m.machine_code = %s
                                        AND m.start_time <= %s
                                        AND (m.end_time > %s OR m.end_time IS NULL)
                                        AND pc.start_time <= %s
                                        AND (pc.end_time > %s OR pc.end_time IS NULL)""",
                            [provider_name, machine_code, at, at, at, at]).fetchone()


@core.api_util.need_db_context
def get_machine_provider_cost_by_id(cost_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM provider_costs_history WHERE id = %s", [cost_id]).fetchone()


@core.api_util.need_db_context
def set_machine_provider_cost(machine_uid, provider_price, provider_currency, provider_sec_granularity=None,
                              provider_min_sec_granularity=None):
    g_db = core.api_util.DatabaseContext.get_conn()
    values = {
        "cost_per_sec": provider_price,
        "currency": provider_currency
    }
    if provider_sec_granularity is not None:
        values["sec_granularity"] = provider_sec_granularity
    if provider_min_sec_granularity is not None:
        values["min_sec_granularity"] = provider_min_sec_granularity
    can_insert = provider_sec_granularity is not None and provider_min_sec_granularity is not None
    if can_insert:
        pg_util.hist_upsert(g_db, "provider_costs", values=values, where=[("machine_uid", "=", machine_uid)])
    else:
        pg_util.hist_update(g_db, "provider_costs", values=values, where=[("machine_uid", "=", machine_uid)])


@core.api_util.need_db_context
def remove_machine(provider_name, machine_code):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        machine = get_machine(provider_name, machine_code)
        if not machine:
            return
        pg_util.hist_remove(g_db, "machines", where=[
            ("provider_code", "=", provider_name),
            ("machine_code", "=", machine_code),
        ])
        pg_util.hist_remove(g_db, "machine_prices", where=[
            ("machine_uid", "=", machine["uid"])
        ])
        pg_util.hist_remove(g_db, "provider_costs", where=[
            ("machine_uid", "=", machine["uid"])
        ])
        g_db.execute("""DELETE FROM operation_machine 
                              WHERE machine_uid IN (
                                        SELECT uid 
                                          FROM machines
                                         WHERE provider_code = %s
                                           AND machine_code = %s)""",
                           [provider_name, machine_code])


@core.api_util.need_db_context
def set_machine_price(provider_name, machine_code, user_rank, price, sec_granularity, min_sec_granularity=None,
                      auto_update=True):
    if min_sec_granularity is None:
        min_sec_granularity = sec_granularity
    machine = get_machine(provider_name, machine_code)
    if machine is None:
        raise RuntimeError("Unknown machine "+str(machine_code))
    if util.float_equals(price, 0) or price < 0:
        raise RuntimeError("A price should never be zero or less")
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        pg_util.hist_upsert(g_db, "machine_prices",
                            values={
                                "sec_price": price,
                                "sec_granularity": sec_granularity,
                                "min_sec_granularity": min_sec_granularity,
                                "auto_update": auto_update
                             },
                            where=[
                                 ("machine_uid", "=", machine["uid"]),
                                 ("user_rank", "=", user_rank)
                             ])
        g_db.execute("""DELETE FROM machine_price_auto_update 
                         WHERE machine_price_id NOT IN (
                            SELECT id FROM machine_prices
                            WHERE auto_update = TRUE
                         )""")
        g_db.execute("""INSERT INTO machine_price_auto_update(machine_price_id, cost_id, to_zcoins) 
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


@core.api_util.need_db_context
def update_provider_costs(provider_pricing_api, provider_name):
    if "://" not in provider_pricing_api:
        provider_pricing_api = "https://" + provider_pricing_api
    provider_pricing_api = provider_pricing_api.rstrip("/")

    provider = core.api_util.get_provider(provider_name)
    if provider.type in ("aws", "aws_spot"):
        machines = list_machines(provider.name)
        machine_uid_by_type = dict({m['machine_code']:m['uid'] for m in machines})
        r = requests.post(provider_pricing_api+ '/v2/search',
                          json={"regionCode": provider.region, "instanceType": machine_uid_by_type.keys()})

        if r.status_code < 200 or r.status_code > 299:
            raise RuntimeError("Unable to get aws instance prices: api call failed")
        result = r.json()
        if "meta" not in result.keys() or "success" not in result["meta"].keys() or result["meta"]["success"] != True:
            raise RuntimeError("Unable to get aws instance prices: api call failed")
        for data in result["data"]:
            machine_code = data["instance"]["instanceType"]
            if machine_code not in machine_uid_by_type.keys():
                continue
            cost = float(data["price"]["amount"]) / 3600 * core.api_util.PRICE_PRECISION
            if provider.type == "aws_spot":
                cost = cost/2.0
            cost = int(math.ceil(cost))
            currency = currencies.symbol_to_name(data["price"]["currency"])
            set_machine_provider_cost(machine_uid_by_type[machine_code], cost, currency)
    else:
        # We don't have method yet for other providers
        pass


@core.api_util.need_db_context
def update_machine_prices():
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        result = g_db.execute("""SELECT ref_mph.machine_uid AS machine_uid,
                                       ref_mph.user_rank AS user_rank,
                                       CAST(ROUND(CAST (ref_mph.sec_price AS FLOAT) / ref_pch.cost_per_sec / mpau.to_zcoins * new_pch.cost_per_sec * cer.to_zcoins) AS INT) AS new_sec_price
                                  FROM machine_price_auto_update AS mpau
                                  LEFT JOIN machine_prices_history AS ref_mph
                                         ON mpau.machine_price_id = ref_mph.id
                                  LEFT JOIN provider_costs_history AS ref_pch
                                         ON mpau.cost_id = ref_pch.id
                                  LEFT JOIN provider_costs_history AS new_pch
                                         ON ref_mph.machine_uid = new_pch.machine_uid
                                  LEFT JOIN currency_exchange_rates AS cer
                                         ON new_pch.currency = cer.currency
                                  LEFT JOIN machine_prices_history AS curr_mph
                                         ON ref_mph.machine_uid = curr_mph.machine_uid AND ref_mph.user_rank = curr_mph.user_rank
                                  WHERE new_pch.end_time IS NULL
                                    AND curr_mph.end_time IS NULL
                                    AND ref_pch.cost_per_sec != 0
                                    AND  mpau.to_zcoins != 0
                                    AND CAST(ROUND(CAST (ref_mph.sec_price AS FLOAT) / ref_pch.cost_per_sec / mpau.to_zcoins * new_pch.cost_per_sec * cer.to_zcoins) AS INT) != curr_mph.sec_price
                                  ORDER BY ref_mph.machine_uid, ref_mph.user_rank""").fetchall()

                                # Usefull columns meaning:
                                # ref_pch.currency AS currency,
                                # ref_pch.cost_per_sec AS ref_cost_per_sec,
                                # mpau.to_zcoins AS ref_to_zcoins,
                                # ref_mph.sec_price AS ref_sec_price,
                                # new_pch.cost_per_sec AS new_cost_per_sec,
                                # cer.to_zcoins AS new_to_zcoins,
                                # curr_mph.sec_price AS current_sec_price,

        for row in result:
            pg_util.hist_upsert(g_db, "machine_prices",
                                values={
                                    "sec_price": int(row["new_sec_price"]),
                                    "auto_priced": True
                                },
                                where=[
                                    ("machine_uid", "=", row["machine_uid"]),
                                    ("user_rank", "=", row["user_rank"])
                                ])


@core.api_util.need_db_context
def get_machine_price_by_id(machine_price_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM machine_prices_history WHERE id = %s", [machine_price_id]).fetchone()


@core.api_util.need_db_context
def get_machine_price(provider_name, machine_code, user_rank, at=None):
    g_db = core.api_util.DatabaseContext.get_conn()
    if at is None:
        return g_db.execute("""SELECT mp.*
                                 FROM machines AS m
                                 LEFT JOIN machine_prices AS mp
                                        ON m.uid = mp.machine_uid                          
                                WHERE m.machine_code = %s
                                  AND m.provider_code = %s
                                 AND mp.user_rank = %s""",
                            [machine_code, provider_name, user_rank]).fetchone()
    else:
        return g_db.execute("""SELECT mp.*
                                 FROM machines_history AS m
                                 LEFT JOIN machine_prices_history AS mp
                                        ON m.uid = mp.machine_uid                          
                                WHERE m.machine_code = %s
                                  AND m.provider_code = %s
                                  AND mp.user_rank = %s
                                  AND m.start_time <= %s
                                  AND (m.end_time > %s OR m.end_time IS NULL)
                                  AND mp.start_time <= %s
                                  AND (mp.end_time > %s OR mp.end_time IS NULL)""",
                            [machine_code, provider_name, user_rank, at, at, at, at]).fetchone()


@core.api_util.need_db_context
def list_machine_prices(provider_name, list_of_machine_codes, list_of_user_ranks):
    if not list_of_machine_codes or not list_of_user_ranks:
        return []
    query = """SELECT m.machine_code, mp.*
                 FROM machines AS m
                 LEFT JOIN machine_prices AS mp
                        ON m.uid = mp.machine_uid                          
                WHERE m.machine_code IN ({})
                  AND m.provider_code = %s
                  AND mp.user_rank IN ({})"""
    query = query.format(",".join(["%s"] * len(list_of_machine_codes)),
                         ",".join(["%s"] * len(list_of_user_ranks)))
    parameters = copy.copy(list_of_machine_codes)
    parameters.append(provider_name)
    parameters.extend(list_of_user_ranks)
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, parameters).fetchall()


@core.api_util.need_db_context
def set_spot_index(provider_name, machine_code, value):
    safe_value = max(0.0, min(1.0, float(value)))

    query = """INSERT INTO spot_indexes 
                    VALUES (%s, %s, %s)
               ON CONFLICT (provider_code, machine_code) 
                  DO UPDATE SET value = EXCLUDED.value"""
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute(query, [provider_name, machine_code, safe_value])


@core.api_util.need_db_context
def get_spot_index(provider_name, machine_code):
    query = """SELECT value 
                 FROM spot_indexes
                WHERE provider_code = %s
                  AND machine_code = %s"""
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(query, [provider_name, machine_code]).fetchone()
    if result is None:
        return 1.0
    return float(result['value'])
