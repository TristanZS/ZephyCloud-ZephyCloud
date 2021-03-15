# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import logging

# Project specific libs
from lib import pg_util
import core.api_util
import projects
import jobs
import users

log = logging.getLogger("aziugo")

STATUS_PENDING = 1
STATUS_RUNNING = 2
STATUS_CANCELED = 3
STATUS_KILLED = 4
STATUS_COMPUTED = 5
STATUS_STOPPED = 6


def status_to_str(status):
    if int(status) == STATUS_PENDING:
        return "pending"
    elif int(status) == STATUS_RUNNING:
        return "computing"
    elif int(status) in (STATUS_CANCELED, STATUS_KILLED):
        return "canceled"
    elif int(status) == STATUS_COMPUTED:
        return "computed"
    elif int(status) == STATUS_STOPPED:
        return "stopped"
    else:
        raise RuntimeError("Unknown calc status "+repr(status))


def is_status_str(status_str):
    return status_str in ["pending", "computing", "canceled", "computed", "stopped"]


def str_to_status(status_str):
    if status_str == "pending":
        return STATUS_PENDING
    elif status_str == "computing":
        return STATUS_RUNNING
    elif status_str == "canceled":
        return STATUS_CANCELED
    elif status_str == "computed":
        return STATUS_COMPUTED
    elif status_str == "stopped":
        return STATUS_STOPPED
    else:
        raise RuntimeError("Unknown calculation status string "+repr(status_str))



@core.api_util.need_db_context
def create_calc(user_id, project_codename, mesh_id, calc_name, overwrite=True):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        project = projects.get_project(user_id, project_codename)
        if not project:
            raise RuntimeError("Unknown project " + project_codename)
        if overwrite:
            delete_calc(user_id, project_codename, calc_name)
        calc_id = g_db.execute("INSERT INTO calculations (project_uid, mesh_id, name) VALUES (%s, %s, %s) RETURNING id",
                               [project_codename, mesh_id, calc_name]).fetchval()
        return g_db.execute("SELECT * FROM calculations WHERE id = %s", [calc_id]).fetchone()


@core.api_util.need_db_context
def get_calc(user_id, project_codename, calc_id, include_deleted=False):
    g_db = core.api_util.DatabaseContext.get_conn()
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    query = """SELECT * FROM calculations WHERE project_uid = %s AND id = %s"""
    if not include_deleted:
        query += " AND delete_date IS NULL"
    return g_db.execute(query, [project_codename, calc_id]).fetchone()


@core.api_util.need_db_context
def get_calc_by_job_id(job_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM calculations WHERE job_id = %s", [job_id]).fetchone()


@core.api_util.need_db_context
def get_calc_by_name(user_id, project_codename, calc_name, include_deleted=False):
    g_db = core.api_util.DatabaseContext.get_conn()
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    query = """SELECT * FROM calculations WHERE project_uid = %s AND name = %s"""
    if not include_deleted:
        query += " AND delete_date IS NULL"
    return g_db.execute(query, [project_codename, calc_name]).fetchone()


@core.api_util.need_db_context
def charge_all(last_charge_limit):
    query = """INSERT INTO user_accounts (user_id, amount, description, job_id, price_snapshot)
                SELECT p.user_id AS user_id, o.fixed_cost * -1 AS amount, %s AS description, j.id AS job_id, 
                       ua.price_snapshot AS price_snapshot
                  FROM jobs AS j 
                  LEFT JOIN operations_history AS o ON j.operation_id = o.id 
                  LEFT JOIN calculations AS c ON c.job_id = j.id
                  LEFT JOIN projects AS p ON c.project_uid = p.uid
                  LEFT JOIN (
                             SELECT ua.* 
                              FROM user_accounts AS ua
                              RIGHT JOIN (
                                   SELECT ua.job_id, MAX(date) AS date
                                     FROM user_accounts AS ua
                                    WHERE ua.job_id IS NOT NULL
                                      AND ua.price_snapshot->'fix_price' IS NOT NULL
                                    GROUP BY ua.job_id
                              ) AS ua2 ON ua2.job_id = ua.job_id AND ua2.date = ua.date
                  ) AS ua ON ua.job_id = j.id
                 WHERE j.status = %s 
                   AND c.status = %s
                   AND j.operation_id IS NOT NULL
                   AND o.operation_name = %s
                   AND c.delete_date IS NULL
                   AND ua.date < %s
                   AND ua.date < now() - INTERVAL '7 DAYS'
    """
    user_id_list = set([])
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute(query, ["Calculation storage cost", jobs.JOB_STATUS_FINISHED, STATUS_COMPUTED, 'calc',
                            last_charge_limit])


@core.api_util.need_db_context
def list_calculations(user_id, project_codename, include_deleted=False, with_logs=False):
    if with_logs:
        query = """SELECT c.id AS id, c.project_uid AS project_uid, c.name AS name, c.mesh_id AS mesh_id,
                                  c.params_file_id AS params_file_id, c.status_file_id AS status_file_id, 
                                  c.result_file_id AS result_file_id, c.iterations_file_id AS iterations_file_id, 
                                  c.reduce_file_id AS reduce_file_id, c.internal_file_id AS internal_file_id,
                                  c.status AS status, c.job_id AS job_id, c.last_start_date AS last_start_date,
                                  c.last_stop_date AS last_stop_date, c.create_date AS create_date,
                                  c.delete_date AS delete_date, j.logs AS logs 
                             FROM calculations AS c 
                             LEFT JOIN jobs AS j ON c.job_id = j.id """
    else:
        query = """SELECT * FROM calculations AS c """
    query += " WHERE c.project_uid = %s "
    if not include_deleted:
        query += " AND c.delete_date IS NULL"
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, [project_codename]).fetchall()


@core.api_util.need_db_context
def delete_calc(user_id, project_codename, calc_name):
    running_calc_status = [STATUS_PENDING, STATUS_RUNNING]

    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    calculations = g_db.execute("""SELECT * 
                                     FROM calculations 
                                    WHERE project_uid = %s 
                                      AND name = %s 
                                      AND delete_date IS NULL""", [project_codename, calc_name]).fetchall()

    # Cancelling jobs
    running_job_ids = []
    for calc in calculations:
        if calc['status'] in running_calc_status and calc['job_id'] is not None:
            running_job_ids.append(calc['job_id'])
    if running_job_ids:
        log.info("Killing jobs " + repr(running_job_ids) +
                 " from deleting calc " + calc_name + "of project "+project_codename)
        jobs.cancel_jobs(running_job_ids)

    for calc in calculations:
        status_file_id = calc['status_file_id']
        result_file_id = calc['result_file_id']
        iterations_file_id = calc['iterations_file_id']
        reduce_file_id = calc['reduce_file_id']
        internal_file_id = calc['internal_file_id']
        if status_file_id is not None:
            projects.remove_file_from_project(user_id, project_codename, status_file_id)
        if result_file_id is not None:
            projects.remove_file_from_project(user_id, project_codename, result_file_id)
        if iterations_file_id is not None:
            projects.remove_file_from_project(user_id, project_codename, iterations_file_id)
        if reduce_file_id is not None:
            projects.remove_file_from_project(user_id, project_codename, reduce_file_id)
        if internal_file_id is not None:
            projects.remove_file_from_project(user_id, project_codename, internal_file_id)
        pg_util.delete_with_date(g_db, "calculations", calc['id'])


@core.api_util.need_db_context
def set_job(user_id, project_codename, calc_name, job_id):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""UPDATE calculations 
                           SET job_id = %s
                         WHERE project_uid = %s
                           AND name = %s
                           AND delete_date IS NULL""",
                       [job_id, project_codename, calc_name])


@core.api_util.need_db_context
def set_calc_status(user_id, project_codename, calc_name, status):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    if status == STATUS_RUNNING:
        g_db.execute("""UPDATE calculations 
                               SET status = %s,
                               last_start_date = now()
                             WHERE project_uid = %s
                               AND name = %s
                               AND delete_date IS NULL""",
                     [status, project_codename, calc_name])
    elif status == STATUS_STOPPED:
        g_db.execute("""UPDATE calculations 
                               SET status = %s,
                               last_stop_date = now()
                             WHERE project_uid = %s
                               AND name = %s
                               AND delete_date IS NULL""",
                     [status, project_codename, calc_name])
    else:
        g_db.execute("""UPDATE calculations 
                               SET status = %s
                             WHERE project_uid = %s
                               AND name = %s
                               AND delete_date IS NULL""",
                     [status, project_codename, calc_name])


@core.api_util.need_db_context
def save_calc_param_file(user_id, project_codename, calc_name, param_file):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    with projects.try_append_file_to_project(user_id, project_codename, param_file) as project_file:
        file_id = project_file['id']
        g_db.execute("""UPDATE calculations
                           SET params_file_id = %s
                         WHERE project_uid = %s
                           AND name = %s
                           AND delete_date IS NULL""", [file_id, project_codename, calc_name])


@core.api_util.need_db_context
def get_calc_status_file(user_id, project_codename, calc_id):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute("""SELECT status_file_id
                               FROM calculations
                              WHERE project_uid = %s
                                AND id = %s
                                AND delete_date IS NULL""", [project_codename, calc_id]).fetchone()
    if not result or result['status_file_id'] is None:
        return None
    return projects.get_file_by_id(user_id, project_codename, int(result['status_file_id']))


@core.api_util.need_db_context
def save_status_file(user_id, project_codename, calc_id, status_file_id):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""UPDATE calculations
                       SET status_file_id = %s
                     WHERE project_uid = %s
                       AND id = %s
                       AND delete_date IS NULL""", [status_file_id, project_codename, calc_id])


@core.api_util.need_db_context
def save_result_files(user_id, project_codename, calc_name, result_file_id, iterations_file_id=None,
                      reduce_file_id=None, internal_file_id=None):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    if internal_file_id:
        g_db.execute("""UPDATE calculations
                           SET result_file_id = %s,
                               iterations_file_id = %s,
                               reduce_file_id = %s,
                               internal_file_id = %s                               
                         WHERE project_uid = %s
                           AND name = %s
                           AND delete_date IS NULL""",
                     [result_file_id, iterations_file_id, reduce_file_id, internal_file_id, project_codename,
                      calc_name])
    else:
        g_db.execute("""UPDATE calculations
                           SET result_file_id = %s,
                               iterations_file_id = %s,
                               reduce_file_id = %s
                         WHERE project_uid = %s
                           AND name = %s
                           AND delete_date IS NULL""",
                     [result_file_id, iterations_file_id, reduce_file_id, project_codename, calc_name])


@core.api_util.need_db_context
def list_failed_and_dirty():
    select_query = """SELECT c.id AS id, c.project_uid AS project_uid, c.name AS name, j.user_id AS user_id
                        FROM calculations AS c
                        LEFT JOIN jobs AS j 
                               ON j.id = c.job_id
                       WHERE c.status IN (%s, %s)
                         AND (j.status = %s OR j.status = %s OR j.status = %s)"""
    query_args = [STATUS_PENDING, STATUS_RUNNING]
    query_args.extend([jobs.JOB_STATUS_CANCELED, jobs.JOB_STATUS_CANCELING, jobs.JOB_STATUS_KILLED])
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(select_query, query_args).fetchall()
    if not result:
        return []
    return result


@core.api_util.need_db_context
def get_project_calculations(user_id, project_codename, include_deleted=False, offset=0, limit=None, order=None):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    query = """SELECT * FROM calculations WHERE project_uid = %s"""
    if not include_deleted:
        query += " AND delete_date IS NULL"
    if order:
        query += " "+order.to_sql()
    if limit:
        query += " LIMIT "+str(int(limit))
    if offset:
        query += " OFFSET "+str(int(offset))
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, [project_codename]).fetchall()
