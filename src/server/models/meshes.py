# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import logging

# Project specific libs
from lib import pg_util
import core.api_util
import jobs
import projects
import calc
import users

log = logging.getLogger("aziugo")

STATUS_PENDING = 1
STATUS_RUNNING = 2
STATUS_CANCELED = 3
STATUS_KILLED = 4
STATUS_COMPUTED = 5


def status_to_str(status):
    if int(status) == STATUS_PENDING:
        return "pending"
    elif int(status) == STATUS_RUNNING:
        return "computing"
    elif int(status) in (STATUS_CANCELED, STATUS_KILLED):
        return "canceled"
    elif int(status) == STATUS_COMPUTED:
        return "computed"
    else:
        raise RuntimeError("Unknown mesh status "+repr(status))


def is_status_str(status_str):
    return status_str in ["pending", "computing", "canceled", "computed"]


def str_to_status(status_str):
    if status_str == "pending":
        return STATUS_PENDING
    elif status_str == "computing":
        return STATUS_RUNNING
    elif status_str == "canceled":
        return STATUS_CANCELED
    elif status_str == "computed":
        return STATUS_COMPUTED
    else:
        raise RuntimeError("Unknown mesh status string "+repr(status_str))


@core.api_util.need_db_context
def get_mesh(user_id, project_codename, mesh_name, include_deleted=False):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    query = """SELECT * FROM meshes WHERE project_uid = %s AND name = %s"""
    if not include_deleted:
        query += " AND delete_date IS NULL"
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, [project_codename, mesh_name]).fetchone()


@core.api_util.need_db_context
def get_mesh_by_job_id(job_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM meshes WHERE job_id = %s", [job_id]).fetchone()


@core.api_util.need_db_context
def get_mesh_by_id(mesh_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT * FROM meshes WHERE id = %s", [mesh_id]).fetchone()


@core.api_util.need_db_context
def list_meshes(user_id, project_codename, include_deleted=False):
    if include_deleted:
        query = "SELECT * FROM meshes WHERE project_uid = %s"
    else:
        query = "SELECT * FROM meshes WHERE project_uid = %s AND delete_date IS NULL"
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, [project_codename]).fetchall()


@core.api_util.need_db_context
def get_project_meshes(user_id, project_codename, include_deleted=False, offset=0, limit=None, order=None):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    query = """SELECT * FROM meshes WHERE project_uid = %s"""
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


@core.api_util.need_db_context
def charge_all(last_charge_limit):
    query = """INSERT INTO user_accounts (user_id, amount, description, job_id, price_snapshot)
                SELECT p.user_id AS user_id, o.fixed_cost * -1 AS amount, %s AS description, j.id AS job_id, 
                       ua.price_snapshot AS price_snapshot
                  FROM jobs AS j 
                  LEFT JOIN operations_history AS o ON j.operation_id = o.id 
                  LEFT JOIN meshes AS m ON m.job_id = j.id
                  LEFT JOIN projects AS p ON m.project_uid = p.uid
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
                   AND m.status = %s
                   AND j.operation_id IS NOT NULL
                   AND o.operation_name = %s
                   AND m.delete_date IS NULL
                   AND ua.date < %s
                   AND ua.date < now() - INTERVAL '7 DAYS'
    """
    user_id_list = set([])
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute(query, ['Mesh storage cost', jobs.JOB_STATUS_FINISHED, STATUS_COMPUTED, 'mesh', last_charge_limit])


@core.api_util.need_db_context
def create_mesh(user_id, project_codename, mesh_name, overwrite=True):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        project = projects.get_project(user_id, project_codename)
        if not project:
            raise RuntimeError("Unknown project " + project_codename)
        if overwrite:
            log.warning("Deleting mesh " + mesh_name + " from overwrite")
            delete_mesh(user_id, project_codename, mesh_name)
        mesh_id = g_db.execute("INSERT INTO meshes (project_uid, name) VALUES (%s, %s) RETURNING id",
                               [project_codename, mesh_name]).fetchval()
        return g_db.execute("SELECT * FROM meshes WHERE id = %s", [mesh_id]).fetchone()


@core.api_util.need_db_context
def save_mesh_files(user_id, project_codename, mesh_name, mesh_file_id, preview_file_id=None):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""UPDATE meshes 
                       SET result_file_id = %s,
                           preview_file_id = %s
                     WHERE project_uid = %s
                       AND name = %s
                       AND delete_date IS NULL""",
                 [mesh_file_id, preview_file_id, project_codename, mesh_name])


@core.api_util.need_db_context
def set_job(user_id, project_codename, mesh_name, job_id):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""UPDATE meshes 
                           SET job_id = %s
                         WHERE project_uid = %s
                           AND name = %s
                           AND delete_date IS NULL""",
                       [job_id, project_codename, mesh_name])


@core.api_util.need_db_context
def set_mesh_status(user_id, project_codename, mesh_name, status):
    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""UPDATE meshes 
                           SET status = %s
                         WHERE project_uid = %s
                           AND name = %s
                           AND delete_date IS NULL""",
                       [status, project_codename, mesh_name])


@core.api_util.need_db_context
def delete_mesh(user_id, project_codename, mesh_name):
    running_calc_status = [calc.STATUS_PENDING, calc.STATUS_RUNNING]
    running_mesh_status = [STATUS_PENDING, STATUS_RUNNING]

    project = projects.get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    proj_meshes = g_db.execute("""SELECT * FROM meshes WHERE project_uid = %s AND name = %s AND delete_date IS NULL""",
                               [project_codename, mesh_name]).fetchall()

    # Cancelling computations
    mesh_ids = [m['id'] for m in proj_meshes]
    if not mesh_ids:
        return
    calculations = g_db.execute("""SELECT * 
                                     FROM calculations 
                                    WHERE project_uid = %s
                                      AND mesh_id IN ("""+", ".join(["%s"]*len(mesh_ids))+""") 
                                      AND delete_date IS NULL""", [project_codename]+mesh_ids).fetchall()
    running_job_ids = [m['job_id'] for m in proj_meshes if m['status'] in running_mesh_status]
    running_job_ids += [c['job_id'] for c in calculations if c['status'] in running_calc_status]
    if running_job_ids:
        log.info("killing jobs " + repr(running_job_ids) + " from deleting mesh " + mesh_name +
                 " of project " + project_codename)
        jobs.cancel_jobs(running_job_ids)

    # Cleaning calculations
    for proj_calc in calculations:
        status_file_id = proj_calc['status_file_id']
        result_file_id = proj_calc['result_file_id']
        iterations_file_id = proj_calc['iterations_file_id']
        reduce_file_id = proj_calc['reduce_file_id']
        internal_file_id = proj_calc['internal_file_id']
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
        pg_util.delete_with_date(g_db, "calculations", proj_calc['id'])

    # Cleaning meshes
    for proj_mesh in proj_meshes:
        file_id = proj_mesh['result_file_id']
        if file_id is not None:
            projects.remove_file_from_project(user_id, project_codename, file_id)
        pg_util.delete_with_date(g_db, "meshes", proj_mesh['id'])


@core.api_util.need_db_context
def list_failed_and_dirty():
    select_query = """SELECT m.id AS id, m.project_uid AS project_uid, m.name AS name, j.user_id AS user_id
                        FROM meshes AS m
                        LEFT JOIN jobs AS j 
                               ON j.id = m.job_id
                       WHERE m.status IN (%s, %s)
                         AND (j.status = %s OR j.status = %s OR j.status = %s)"""
    query_args = [STATUS_PENDING, STATUS_RUNNING]
    query_args.extend([jobs.JOB_STATUS_CANCELED, jobs.JOB_STATUS_CANCELING, jobs.JOB_STATUS_KILLED])
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(select_query, query_args).fetchall()
    if not result:
        return []
    return result


