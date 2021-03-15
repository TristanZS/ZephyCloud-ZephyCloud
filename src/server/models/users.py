# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core lib
import hashlib
import datetime
import logging
import urllib

# Third party libs
import requests

# Project libs
from lib import util
from lib import type_util
from lib import pg_util
import core.api_util
import currencies


RANK_BRONZE = 1
RANK_SILVER = 2
RANK_GOLD = 3
RANK_ROOT = 4

log = logging.getLogger("aziugo")


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
        raise RuntimeError("Invalid rank: "+str(rank))


def str_to_rank(rank_str):
    rank_str = rank_str.strip().lower()
    if rank_str == "bronze":
        return RANK_BRONZE
    elif rank_str == "silver":
        return RANK_SILVER
    elif rank_str == "gold":
        return RANK_GOLD
    elif rank_str == "root":
        return RANK_ROOT
    else:
        raise RuntimeError("Invalid rank: " + str(rank_str))


def is_rank_str(var):
    try:
        str_to_rank(var)
        return True
    except RuntimeError:
        return False


def all_ranks():
    return RANK_BRONZE, RANK_SILVER, RANK_GOLD, RANK_ROOT


@core.api_util.need_db_context
def search(term, include_deleted=False):
    query_args = ['%' + term + '%', '%' + term + '%']
    query = """SELECT id, login, email, user_rank, create_date, delete_date 
                 FROM users 
                WHERE (
                    login LIKE %s
                    OR email LIKE %s"""
    if type_util.ll_int(term):
        query += " OR id = %s "
        query_args.append(int(term))
    query += ")"
    if include_deleted:
        query += " AND delete_date IS NULL"

    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.all_to_dict(g_db.execute(query, query_args).fetchall())


@core.api_util.need_db_context
def create_user(login, password, rank, email):
    """
    Create a new user

    :param login:           The user login
    :type login:            str
    :param password:        The user password
    :type password:         str
    :param rank:            The user rank. ex: RANK_GOLD
    :type rank:             int
    :param email:           The user email
    :type email:            str
    :return:                The created user, or None if it already exists
    :rtype:                 dict[str, any]|None
    """
    salt = util.generate_salt()
    h = hashlib.sha256()
    h.update(password)
    h.update(salt)
    hex_dig = h.hexdigest()

    log.info("Creating user "+repr(login))
    g_db = core.api_util.DatabaseContext.get_conn()
    user_id = None
    with g_db.cursor() as cur:
        try:
            cur.execute("""INSERT INTO users (login, pwd, salt, user_rank, email) 
                                VALUES (%s, %s, %s, %s, %s)
                           RETURNING id""",
                        [login, str(hex_dig), salt, rank, email])
            user_id = cur.fetchone()[0]
            g_db.commit()
        except pg_util.IntegrityError:
            log.warning("User creation failed: user "+str(login)+" ("+email+") already exists")
            return None
    if user_id is None:
        return None
    with g_db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", [user_id])
        return cur.fetchone()


@core.api_util.need_db_context
def reset_pwd(user_id):
    new_password = util.generate_salt()
    salt = util.generate_salt()
    h = hashlib.sha256()
    h.update(new_password)
    h.update(salt)
    hex_dig = h.hexdigest()

    log.info("Reset password for user id " + str(user_id))
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute("UPDATE users SET pwd = %s, salt = %s WHERE id = %s", [str(hex_dig), salt, user_id])
    return new_password


@core.api_util.need_db_context
def get_user(user_id=None, login=None, email=None, include_deleted=False):
    query_args = []
    conditions = []
    if user_id is not None:
        query_args.append(user_id)
        conditions.append("id = %s")
    if login is not None:
        query_args.append(login)
        conditions.append("login = %s")
    if email is not None:
        query_args.append(email)
        conditions.append("email = %s")
    if len(query_args) == 0:
        raise RuntimeError("No data to select user")
    if not include_deleted:
        conditions.append("delete_date IS NULL")

    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE "+" AND ".join(conditions), query_args)
        return cur.fetchone()


@core.api_util.need_db_context
def authenticate(login_or_email, password):
    """
    Checks if user:pass matches with database
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute("""SELECT * 
                        FROM users 
                       WHERE (
                                (login IS NOT NULL AND login = %s)
                                OR 
                                (email IS NOT NULL AND email = %s)
                             ) 
                         AND delete_date IS NULL""",
                    [login_or_email, login_or_email])
        user = cur.fetchone()
    if user is None:
        return None
    h = hashlib.sha256()
    h.update(password)
    h.update(user['salt'])

    if str(h.hexdigest()) != str(user['pwd']):
        return None
    return user


@core.api_util.need_db_context
def add_user_credits(amount, user_id, description):
    log.info("Adding "+str(amount)+" to user "+str(user_id)+". Reason: "+description)
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute("""INSERT INTO user_accounts (user_id, amount, description)
                            VALUES (%s, %s, %s)""",
                    [user_id, amount, description])
        g_db.commit()
    return get_credit(user_id)


@core.api_util.need_db_context
def get_credit(user_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute('SELECT COALESCE(SUM(amount), 0) as credit FROM user_accounts WHERE user_id = %s', [user_id])
        result = cur.fetchone()
    if result is None:
        return 0
    return int(result["credit"])


@core.api_util.need_db_context
def delete_user(user_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    pg_util.delete_with_date(g_db, "users", user_id)


@core.api_util.need_db_context
def set_user_rank(user_id, rank):
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("UPDATE users SET user_rank = %s WHERE id = %s", [rank, user_id])


@core.api_util.need_db_context
def get_users_with_amounts(include_deleted=False, offset=0, limit=None, order=None, filter=None, rank=None):
    count_key = None
    query = """ SELECT users.id, users.login, users.user_rank, users.delete_date, users.create_date, users.email,
                       COALESCE(SUM(user_accounts.amount), 0) as credit """
    if offset or limit:
        query += "     , count(*) OVER() AS pagination_full_count"
        count_key = "pagination_full_count"
    query += """  FROM users
                  LEFT JOIN user_accounts ON users.id = user_accounts.user_id\n"""

    conditions = []
    query_args = []
    if not include_deleted:
        conditions.append("delete_date IS NULL")
    if filter:
        if type_util.ll_int(filter):
            conditions.append("users.id = %s")
            query_args.append(filter)
        else:
            conditions.append("(users.login LIKE %s OR users.email LIKE %s)")
            query_args.extend(["%" + filter + "%", "%" + filter + "%"])
    if rank:
        conditions.append("users.user_rank = %s")
        query_args.append(rank)

    if conditions:
        query += " WHERE "+" AND ".join(conditions)+" "

    query += " GROUP BY users.id"
    if order:
        query += " "+order.to_sql({"user_id": "users.id", "login": "users.login", "rank": "users.user_rank",
                                   "credit": "credit"})
    if limit:
        query += " LIMIT "+str(int(limit))
    if offset:
        query += " OFFSET "+str(int(offset))
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute(query, query_args)
        return pg_util.PgList.from_result(cur.fetchall(), count_key)


@core.api_util.need_db_context
def charge_user_custom(user_id, amount, description, details):
    log.info("Charging user %s. Reason: %s" % (str(user_id), description))
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute("""INSERT INTO user_accounts (user_id, amount, description, price_snapshot)
                              VALUES (%s, %s, %s, %s, %s)""",
                    [user_id, int(amount)*-1, description, details])
        g_db.commit()


@core.api_util.need_db_context
def charge_user_fix_price(user_id, job_id, description):
    log.info("Charging user %s. Reason: %s" % (str(user_id), description))
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute("SELECT operation_id FROM jobs WHERE id = %s", [job_id])
        job = cur.fetchone()
        operation_id = job["operation_id"]
    with g_db.cursor() as cur:
        cur.execute("SELECT * FROM operations_history WHERE id = %s", [operation_id])
        fix_price = cur.fetchone()
        price_snapshot = {
            "fix_price": pg_util.row_to_dict(fix_price, datetime_to_int=True)
        }
    with g_db.cursor() as cur:
        cur.execute("""INSERT INTO user_accounts (user_id, amount, description, job_id, price_snapshot)
                              VALUES (%s, %s, %s, %s, %s)""",
                    [user_id, int(fix_price["fixed_cost"])*-1, description, job_id, price_snapshot])
        g_db.commit()


@core.api_util.need_db_context
def charge_user_computing(user_id, job_id, description):
    log.info("Charging user %s. Reason: %s" % (str(user_id), description))
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        with g_db.cursor() as cur:
            cur.execute("SELECT machine_price_id, start_time, nbr_machines FROM jobs WHERE id = %s", [job_id])
            job = pg_util.row_to_dict(cur.fetchone())
        with g_db.cursor() as cur:
            cur.execute("SELECT * FROM machine_prices_history WHERE id = %s", [job["machine_price_id"]])
            price = pg_util.row_to_dict(cur.fetchone())
        now = pg_util.get_now(g_db)
        with g_db.cursor() as cur:
            cur.execute("SELECT MAX(computing_end) FROM user_accounts WHERE job_id = %s", [job_id])
            last_comp = cur.fetchone()
            if last_comp is not None:
                last_comp = last_comp[0]

        if last_comp is None:
            start_time = job["start_time"] if job["start_time"] else now
            end_time = start_time+datetime.timedelta(seconds=price["min_sec_granularity"])
        else:
            start_time = last_comp
            end_time = start_time + datetime.timedelta(seconds=price["sec_granularity"])

        while end_time < now:
            end_time += datetime.timedelta(seconds=price["sec_granularity"])

        charged_price = (end_time - start_time).total_seconds()*int(price["sec_price"])*int(job["nbr_machines"])
        price_snapshot = {
            "price": pg_util.row_to_dict(price),
            "start_time": start_time,
            "end_time": end_time
        }
        with g_db.cursor() as cur:
            cur.execute("""INSERT INTO user_accounts (user_id, amount, description, job_id, price_snapshot, 
                                                       computing_start, computing_end)
                                  VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        [user_id, charged_price * -1, description, job_id, price_snapshot, start_time, end_time])
        return end_time


@core.api_util.need_db_context
def list_transactions(user_id=None, project_uid=None, job_id=None, offset=-1, limit=None, order=None, description=None):
    query = """SELECT ua.*, j.project_uid, u.login, u.email """
    if offset or limit:
        query += ", count(*) OVER() AS pagination_full_count"
    query += """ FROM user_accounts AS ua
                 LEFT JOIN jobs AS j ON ua.job_id = j.id
                 LEFT JOIN users AS u ON u.id = ua.user_id
            """
    where_conditions = []
    params = []
    if user_id:
        where_conditions.append("ua.user_id = %s")
        params.append(user_id)
    if project_uid:
        where_conditions.append("j.project_uid = %s")
        params.append(project_uid)
    if job_id:
        where_conditions.append("ua.job_id = %s")
        params.append(job_id)
    if description:
        where_conditions.append("ua.description = %s")
        params.append(description)

    if where_conditions:
        query += " WHERE "+" AND ".join(where_conditions)

    if order:
        query += " "+order.to_sql({"id": "ua.id", "amount": "ua.amount", "date": "ua.date", "job_id": "ua.job_id",
                                   "login": "u.login", "email": "u.email", "project_uid": "j.project_uid",
                                   "computing_start": "ua.computing_start", "computing_end": "ua.computing_end",
                                   "description": "ua.description"})
    if limit:
        query += " LIMIT "+str(int(limit))
    if offset:
        query += " OFFSET "+str(int(offset))
    count_key = "pagination_full_count" if offset or limit else None
    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.PgList.from_result(g_db.execute(query, params).fetchall(), count_key)


@core.api_util.need_db_context
def cancel_transactions(transaction_ids, reason):
    query = """INSERT INTO user_accounts (user_id, amount, job_id, description)
                    SELECT user_id, amount * -1, job_id, 'Cancel transaction ' || id || ": " || %s
                      FROM user_accounts 
                     WHERE id IN ("""+", ".join(["%s"]*len(transaction_ids))+""")"""
    user_id_list = set([])
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute(query, [reason] + transaction_ids)


@core.api_util.need_db_context
def get_report(from_date, to_date, user_id=None, order_by=None):
    overview_query_args = [core.api_util.PRICE_PRECISION, from_date, core.api_util.PRICE_PRECISION, to_date]
    overview_query = """SELECT U.id AS user_id, 
                               U.login, 
                               U.email,
                               COALESCE(T1.previous_balance, 0) AS previous_balance,
                               COALESCE(T2.current_balance, 0) AS current_balance
                        FROM users AS u
                        LEFT JOIN (
                            SELECT UA.user_id, SUM(UA.amount) / %s AS previous_balance
                            FROM user_accounts AS UA 
                            WHERE UA.date < %s
                            GROUP BY UA.user_id
                        ) AS T1 ON T1.user_id = U.id
                        LEFT JOIN (
                            SELECT UA.user_id, SUM(UA.amount) / %s AS current_balance
                            FROM user_accounts AS UA 
                            WHERE UA.date < %s
                            GROUP BY UA.user_id
                        ) AS T2 ON T2.user_id = U.id"""

    details_query_args = [core.api_util.PRICE_PRECISION, from_date, to_date, from_date, to_date, from_date, to_date]
    details_query = """SELECT UA.user_id, 
                              MAX(UA.date) as date,
                              SUM(UA.amount) / %s AS amount,
                              UA.description, 
                              J.project_uid AS project,
                              SUM(J.cores_per_sec) AS cores_per_sec,
                              MAX(P.mesh_count) AS mesh_count,
                              MAX(P.calc_count) AS calc_count
                         FROM user_accounts AS UA 
                         LEFT JOIN (
                            SELECT jobs.*,
                              GREATEST(
                                        MAX(MPH.min_sec_granularity), 
                                        (CEIL(EXTRACT(EPOCH FROM (MAX(jobs.end_time) - MIN(jobs.start_time)))::integer / MAX(MPH.sec_granularity)) * MAX(MPH.sec_granularity))::integer
                                      ) * MAX(jobs.nbr_machines) * MAX(MH.nbr_cores) AS cores_per_sec
                              FROM jobs 
                              LEFT JOIN machine_prices_history AS MPH 
                                   ON MPH.id = jobs.machine_price_id      
                              LEFT JOIN machines_history AS MH 
                                   ON MH.uid = MPH.machine_uid
                              GROUP BY jobs.id
                            ) AS J ON J.id = UA.job_id 
                         LEFT JOIN (
                            SELECT projects.uid, 
                                   COUNT(DISTINCT M.id) as mesh_count,
                                   COUNT(DISTINCT C.id) as calc_count
                              FROM projects 
                              LEFT JOIN meshes AS M ON M.project_uid = projects.uid 
                              LEFT JOIN calculations AS C ON C.project_uid = projects.uid
                             WHERE M.status != 1
                               AND (M.delete_date IS NULL OR M.delete_date >= %s)
                               AND M.create_date <= %s
                               AND C.status != 1
                               AND (C.delete_date IS NULL OR C.delete_date >= %s)
                               AND C.create_date <= %s
                             GROUP BY projects.uid
                            ) AS P ON P.uid = J.project_uid
                        WHERE UA.date > %s
                          AND UA.date <= %s """
    if user_id is not None:
        overview_query += " WHERE U.id = %s"
        overview_query_args.append(user_id)
        details_query += " AND UA.user_id = %s "
        details_query_args.append(user_id)
    details_query += """GROUP BY J.project_uid, UA.description, UA.user_id"""
    if order_by is None or order_by == "project":
        details_query += " ORDER BY user_id, project NULLS FIRST, date DESC, description"
    elif order_by == "date":
        details_query += " ORDER BY user_id, date DESC, project NULLS FIRST, description"
    elif order_by == "description":
        details_query += " ORDER BY user_id, description, date DESC, project NULLS FIRST"

    g_db = core.api_util.DatabaseContext.get_conn()
    by_user_id = {}
    with g_db.cursor() as cur:
        cur.execute(overview_query, overview_query_args)
        for row in cur:
            by_user_id[row["user_id"]] = pg_util.row_to_dict(row)
            by_user_id[row["user_id"]]['details'] = []

    with g_db.cursor() as cur:
        cur.execute(details_query, details_query_args)
        for row in cur:
            row_info = pg_util.row_to_dict(row)
            user_id = row_info["user_id"]
            if "cloud computation cost" not in row_info['description'].lower():
                del row_info['cores_per_sec']
            if "calculation storage cost" not in row_info['description'].lower():
                del row_info['calc_count']
            if "mesh storage cost" not in row_info['description'].lower():
                del row_info['mesh_count']
            del row_info["user_id"]
            by_user_id[user_id]['details'].append(row_info)
    return by_user_id


@core.api_util.need_db_context
def save_report_date(report_date):
    g_db = core.api_util.DatabaseContext.get_conn()

    with pg_util.Transaction(g_db):
        with g_db.cursor() as cur:
            cur.execute("DELETE FROM last_report")
            cur.execute("INSERT INTO last_report (report_date) VALUES (%s)", [report_date])


@core.api_util.need_db_context
def get_report_date(default=None):
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute('SELECT report_date FROM last_report')
        row = cur.fetchone()
        if not row:
            return default
        return row[0]


@core.api_util.need_db_context
def get_benefits(from_date, to_date, currency=None, user_id=None):
    conf = core.api_util.get_conf()
    default_currency = conf.get('currency', 'main_currency')
    if currency is None:
        currency = default_currency
    zephycoins_to_currency = 1.0 / currencies.get_currencies_to_zc()[currency] / core.api_util.PRICE_PRECISION
    query_args = [currency, core.api_util.OPENFOAM_DONATION_RATIO, core.api_util.PRICE_PRECISION]
    currency_sql = ""

    for specific_currency, rate in currencies.get_currencies_ratio(currency).items():
        currency_sql += " WHEN %s THEN %s "
        query_args.extend([specific_currency, rate])

    query_args.extend([zephycoins_to_currency, from_date, to_date]*2)

    query = """SELECT U.login, 
                      U.id AS user_id, 
                      U.email AS email,
                      COALESCE(T3.factured_computation, 0) AS factured_computation,
                      COALESCE(T3.computation_cost, 0) AS computation_cost,
                      COALESCE(T3.openfoam_commission, 0) AS openfoam_commission,
                      COALESCE(T2.factured_storage, 0) AS factured_storage,
                      (
                        COALESCE(T3.factured_computation, 0) - COALESCE(T3.computation_cost, 0) - 
                        COALESCE(T3.openfoam_commission, 0) + COALESCE(T2.factured_storage, 0)
                      ) AS benefits,
                      %s AS currency
                  FROM users AS U
                  LEFT JOIN (
                    SELECT T1.user_id, 
                           SUM(T1.price) AS factured_computation, 
                           SUM(T1.cost) AS computation_cost,
                           SUM(T1.price) * %s AS openfoam_commission
                      FROM (
                            SELECT J.user_id, 
                                   (J.nbr_machines
                                    * GREATEST(
                                        PCH.min_sec_granularity, 
                                        (CEIL(EXTRACT(EPOCH FROM (J.end_time - J.start_time))::numeric / PCH.sec_granularity) * PCH.sec_granularity)::integer
                                      )
                                    * PCH.cost_per_sec::numeric 
                                    / %s * CASE PCH.currency """ + currency_sql + """ ELSE 0 END
                                   ) AS cost,
                                   (SUM(UA.amount::numeric) * %s * -1 ) AS price
                              FROM user_accounts AS UA 
                              LEFT JOIN jobs AS J ON J.id = UA.job_id 
                              LEFT JOIN provider_costs_history AS PCH ON PCH.id = J.provider_cost_id
                              LEFT JOIN machine_prices_history AS MPH ON MPH.id = J.machine_price_id
                              WHERE UA.computing_start IS NOT NULL
                                AND UA.date > %s
                                AND UA.date <= %s
                              GROUP BY J.id, PCH.id, MPH.id, J.user_id
                       ) AS T1
                    GROUP BY T1.user_id
                ) AS T3 ON T3.user_id = U.id
                FULL JOIN (
                    SELECT UA.user_id, SUM(UA.amount::numeric * %s * -1 ) AS factured_storage
                      FROM user_accounts AS UA
                     WHERE UA.computing_start IS NULL
                       AND UA.job_id IS NOT NULL
                       AND UA.date > %s
                       AND UA.date <= %s
                      GROUP BY UA.user_id
                 ) AS T2 ON T3.user_id = T2.user_id"""

    if user_id is not None:
        query += " WHERE U.id = %s"
        query_args.append(user_id)
    else:
        query += """ WHERE T3.factured_computation IS NOT NULL 
                       AND T3.computation_cost IS NOT NULL
                       AND T3.openfoam_commission IS NOT NULL
                       AND T2.factured_storage IS NOT NULL"""

    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        return pg_util.all_to_dict(cur.execute(query, query_args).fetchall())
