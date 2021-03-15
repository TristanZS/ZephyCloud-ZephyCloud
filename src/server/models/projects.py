# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core api
import os
import uuid
import contextlib
import logging

# Project specific libs
from lib import pg_util
from lib import error_util
import core.storages
import core.api_util
import jobs


PROJECT_STATUS_PENDING = 1
PROJECT_STATUS_RAW = 2
PROJECT_STATUS_ANALYSING = 3
PROJECT_STATUS_ANALYSED = 4

PROJECT_FILE_RAW = "project.zip"
PROJECT_FILE_ANALYSED = "anal.zip"

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

log = logging.getLogger("aziugo")


def project_status_to_str(status):
    if status == PROJECT_STATUS_PENDING:
        return "pending"
    if status == PROJECT_STATUS_RAW:
        return "raw"
    elif status == PROJECT_STATUS_ANALYSING:
        return "analysing"
    elif status == PROJECT_STATUS_ANALYSED:
        return "analysed"
    else:
        raise RuntimeError("Unknown project status "+repr(status))


def str_to_project_status(status_str):
    if status_str == "pending":
        return PROJECT_STATUS_PENDING
    if status_str == "raw":
        return PROJECT_STATUS_RAW
    elif status_str == "analysing":
        return PROJECT_STATUS_ANALYSING
    elif status_str == "analysed":
        return PROJECT_STATUS_ANALYSED
    else:
        raise RuntimeError("Unknown project status string "+repr(status_str))


def is_status_str(status_str):
    try:
        str_to_project_status(status_str)
        return True
    except RuntimeError:
        return False


@core.api_util.need_db_context
def search(term, include_deleted=False):
    if include_deleted:
        query = """SELECT DISTINCT ON ("uid") *
                     FROM projects_history
                    WHERE uid LIKE %s
                    ORDER BY uid, end_time DESC NULLS FIRST"""
    else:
        query = """SELECT DISTINCT ON ("uid") *
                     FROM projects
                    WHERE uid LIKE %s"""
    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.all_to_dict(g_db.execute(query, ['%' + term + '%']).fetchall())


@core.api_util.need_db_context
def list_projects(user_id=None, at=None, offset=0, limit=None, order=None, filter=None, status=None, storage=None):
    query_cond = []
    query_args = []
    table = "projects_history" if at else "projects"
    query = """SELECT p.*, u.login, u.email, T1.creation_date """
    if offset or limit:
        query += "     , count(*) OVER() AS pagination_full_count "
    query += """FROM """+table+""" AS p
                LEFT JOIN users AS u ON u.id = p.user_id
                LEFT JOIN (
                  SELECT MIN(start_time) AS creation_date, uid 
                    FROM projects_history
                   GROUP BY uid                      
                 ) AS T1 ON T1.uid = p.uid"""
    if at:
        query_cond.extend(["start_time <= %s", "(end_time > %s OR end_time IS NULL)"])
        query_args.extend([at, at])
    if user_id:
        query_cond.append("p.user_id = %s")
        query_args.append(user_id)
    if filter:
        query_cond.append("p.uid LIKE %s")
        query_args.append("%"+filter+"%")
    if user_id:
        query_cond.append("p.user_id = %s")
        query_args.append(user_id)
    if status:
        query_cond.append("p.status = %s")
        query_args.append(status)
    if storage:
        query_cond.append("p.storage = %s")
        query_args.append(storage)

    if query_cond:
        query += " WHERE "+" AND ".join(query_cond)+" "

    if order:
        order_mapping = {"id": "p.id", "project_uid": "p.uid", "storage": "p.storage", "status": "p.status",
                         "email": "u.email", "creation_date": "T1.creation_date"}
        query += " "+order.to_sql(order_mapping)
    if limit:
        query += " LIMIT "+str(int(limit))
    if offset:
        query += " OFFSET "+str(int(offset))
    count_key = "pagination_full_count" if offset or limit else None
    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.PgList.from_result(g_db.execute(query, query_args).fetchall(), count_key)


@core.api_util.need_db_context
def get_project(user_id, project_codename, include_deleted=False):
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute("""SELECT p.*, T1.creation_date FROM projects AS p
                               LEFT JOIN (
                                  SELECT MIN(start_time) AS creation_date, uid 
                                    FROM projects_history
                                   GROUP BY uid                      
                                 ) AS T1 ON T1.uid = p.uid
                              WHERE p.user_id = %s
                                AND p.uid = %s""", [user_id, project_codename]).fetchone()
    if result is None and include_deleted:
        result = g_db.execute("""SELECT p.*, T1.creation_date FROM projects_history AS p
                                    LEFT JOIN (
                                      SELECT MIN(start_time) AS creation_date, uid 
                                        FROM projects_history
                                       GROUP BY uid                      
                                     ) AS T1 ON T1.uid = p.uid
                                  WHERE p.user_id = %s
                                    AND P.uid = %s
                                  ORDER BY end_time DESC
                                  LIMIT 1""", [user_id, project_codename]).fetchone()
    return pg_util.row_to_dict(result)


@core.api_util.need_db_context
def create_project(user_id, project_codename, storage_name):
    """
    Create a new project

    :param user_id:
    :type user_id:
    :param project_codename:
    :type project_codename:
    :param storage_name:
    :type storage_name:
    :return:
    :rtype:
    """

    try:
        g_db = core.api_util.DatabaseContext.get_conn()
        result = pg_util.hist_insert(g_db, "projects", values={
                                                 "uid": project_codename,
                                                 "user_id": user_id,
                                                 "status": PROJECT_STATUS_RAW,
                                                 "data": '{}',
                                                 'storage': storage_name,
                                           })
        return result
    except pg_util.IntegrityError:
        return None


@core.api_util.need_db_context
def save_project_file(user_id, project_codename, filename, file_size, key=None):
    """
    Add a file to project file list

    :param user_id:             The project owner id
    :type user_id:              int
    :param project_codename:    The project uid
    :type project_codename:     str
    :param filename:            The saved file name
    :type filename:             str
    :param file_size:           The size of the file
    :type file_size:            int
    :param key:                 The key of the file
    :type key:                  int|None
    :return:                    The file information
    :rtype:                     dict[str, any]
    """
    project = get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("No project "+project_codename)
    g_db = core.api_util.DatabaseContext.get_conn()
    row_id = g_db.execute("""INSERT INTO project_files (project_uid, filename, key, size)
                                                VALUES (%s, %s, %s, %s)
                             RETURNING id""", [project_codename, filename, key, file_size]).fetchval()
    result = g_db.execute("SELECT * FROM project_files WHERE id = %s", [row_id]).fetchone()
    return pg_util.row_to_dict(result)


@core.api_util.need_db_context
def append_file_to_project(user_id, project_codename, file_path, filename=None, key=None, overwrite=False):
    """
    Add a file to project file list and save it into distant storage
    """
    project = get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("No project "+project_codename)
    storage = core.api_util.get_storage(project['storage'])
    if filename is None:
        _, file_extension = os.path.splitext(file_path)
        if not file_extension:
            file_extension = ""
        if file_extension:
            file_extension = "."+file_extension.lstrip(".")
        filename = project_codename+"-"+str(uuid.uuid4())+file_extension
    old_file = None
    g_db = core.api_util.DatabaseContext.get_conn()
    with storage.uploading_file(file_path, filename):
        file_size = os.path.getsize(file_path)
        if key and overwrite:
            with pg_util.Transaction(g_db):
                old_file = g_db.execute("""SELECT * 
                                             FROM project_files 
                                            WHERE project_uid = %s
                                              AND key = %s""", [project_codename, key]).fetchone()
                if old_file:
                    g_db.execute("DELETE FROM project_files WHERE id = %s", [old_file['id']])
                row_id = g_db.execute("""INSERT INTO project_files (project_uid, filename, key, size)
                                                            VALUES (%s, %s, %s, %s)
                                         RETURNING id""", [project_codename, filename, key, file_size]).fetchval()
        else:
            row_id = g_db.execute("""INSERT INTO project_files (project_uid, filename, key, size)
                                                        VALUES (%s, %s, %s, %s)
                                     RETURNING id""",
                                  [project_codename, filename, key, file_size]).fetchval()
    if old_file:
        storage = core.api_util.get_storage(project['storage'])
        storage.delete_file(old_file["filename"])
    result = g_db.execute("SELECT * FROM project_files WHERE id = %s", [row_id]).fetchone()
    return pg_util.row_to_dict(result)


@core.api_util.need_db_context
def charge_all(last_charge_limit):
    query = """INSERT INTO user_accounts (user_id, amount, description, job_id, price_snapshot)
                SELECT p.user_id AS user_id, j.fixed_cost * -1 AS amount, %s AS description, j.id AS job_id, 
                       ua.price_snapshot AS price_snapshot
                  FROM projects AS p 
                  RIGHT JOIN (
                        SELECT j.id, j.project_uid, o.fixed_cost
                          FROM jobs AS j
                          RIGHT JOIN (
                                  SELECT j.project_uid, MAX(j.start_time) as start_time
                                    FROM jobs AS j
                                    LEFT JOIN operations_history AS o ON j.operation_id = o.id
                                   WHERE j.status = %s
                                     AND j.operation_id IS NOT NULL
                                     AND o.operation_name = %s
                                   GROUP BY project_uid
                          ) AS j2 ON j2.project_uid = j.project_uid AND j2.start_time = j.start_time
                          LEFT JOIN operations_history AS o ON j.operation_id = o.id
                  ) AS j ON p.uid = j.project_uid 
                  RIGHT JOIN (
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
                 WHERE p.status = %s
                   AND ua.date < %s
                   AND ua.date < now() - INTERVAL '7 DAYS'
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    with g_db.cursor() as cur:
        cur.execute(query, ["Project storage cost", jobs.JOB_STATUS_FINISHED, 'anal', PROJECT_STATUS_ANALYSED,
                            last_charge_limit])


@contextlib.contextmanager
def try_append_file_to_project(user_id, project_codename, file_path, filename=None, key=None):
    generated = append_file_to_project(user_id, project_codename, file_path, filename, key)
    try:
        yield generated
    except error_util.all_errors:
        with error_util.before_raising():
            try:
                remove_file_from_project(user_id, project_codename, generated['id'])
            except error_util.all_errors as e:
                log.error("Unable to remove file "+repr(generated))
                error_util.log_error(log, e)


@core.api_util.need_db_context
def remove_file_from_project(user_id, project_codename, file_id):
    project = get_project(user_id, project_codename)
    if not project:
        return
    g_db = core.api_util.DatabaseContext.get_conn()
    project_file = g_db.execute("""SELECT * 
                                     FROM project_files 
                                    WHERE id = %s 
                                      AND project_uid = %s 
                                      AND delete_date IS NULL""", [file_id, project_codename]).fetchone()
    if not project_file:
        return
    storage = core.api_util.get_storage(project['storage'])
    if storage.file_exists(project_file["filename"]):
        storage.delete_file(project_file["filename"])
    pg_util.delete_with_date(g_db, "project_files", file_id)


@core.api_util.need_db_context
def get_file_by_key(user_id, project_codename, key, include_deleted=False):
    project = get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("No project "+project_codename)
    query = """SELECT * FROM project_files WHERE project_uid = %s AND key = %s"""
    if not include_deleted:
        query += " AND delete_date IS NULL"
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, [project_codename, key]).fetchone()


@core.api_util.need_db_context
def get_file_by_id(user_id, project_codename, file_id, include_deleted=False):
    project = get_project(user_id, project_codename)
    if not project:
        raise RuntimeError("No project "+project_codename)
    query = """SELECT * FROM project_files WHERE project_uid = %s AND id = %s"""
    if not include_deleted:
        query += " AND delete_date IS NULL"
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute(query, [project_codename, file_id]).fetchone()


@core.api_util.need_db_context
def list_files(user_id, project_codename, include_deleted=False):
    if include_deleted:
        query = "SELECT * FROM project_files WHERE project_uid = %s"
    else:
        query = "SELECT * FROM project_files WHERE project_uid = %s AND delete_date IS NULL"
    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.all_to_dict(g_db.execute(query, [project_codename]).fetchall())


@core.api_util.need_db_context
def file_exists(filename, include_deleted=False):
    query = "SELECT id FROM project_files WHERE filename = %s"
    if not include_deleted:
        query += " AND delete_date IS NULL"
    query += " LIMIT 1"
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(query, [filename]).fetchall()
    return True if result else False


@core.api_util.need_db_context
def set_project_status(user_id, project_codename, status):
    g_db = core.api_util.DatabaseContext.get_conn()
    pg_util.hist_update(g_db, "projects", values={
        "status": status
    }, where=[
        ("uid", "=", project_codename),
        ("user_id", "=", user_id)
    ])


@core.api_util.need_db_context
def get_already_spent(user_id, project_codename):
    """

    :param user_id:
    :param project_codename:
    :return:
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute("""SELECT COALESCE(SUM(amount), 0)
                               FROM user_accounts AS ua
                               LEFT JOIN jobs AS j ON ua.job_id = j.id
                              WHERE ua.user_id = %s
                                AND j.project_uid = %s""",
                          [user_id, project_codename]).fetchone()
    if not result:
        return 0
    return int(result[0])*-1


@core.api_util.need_db_context
def list_files_on_storage(storage_name):
    g_db = core.api_util.DatabaseContext.get_conn()
    query_result = g_db.execute("""SELECT pf.* 
                                     FROM project_files AS pf 
                                     LEFT JOIN projects AS p 
                                            ON p.uid = pf.project_uid 
                                     WHERE pf.delete_date IS NULL 
                                       AND ( 
                                          pf.storage = %s 
                                          OR ( 
                                              pf.storage IS NULL 
                                              AND p.storage = %s
                                          )
                                       )""", [storage_name, storage_name]).fetchall()
    results = []
    for line in query_result:
        results.append(line)
    return results


@core.api_util.need_db_context
def list_failed_and_dirty():
    """
    List all projects where link or analyse jobs failed but the project status is not failed

    :return:            A list of failed projects
    :rtype:             list[dict[str, any]]
    """
    project_status = [PROJECT_STATUS_PENDING, PROJECT_STATUS_ANALYSING, PROJECT_STATUS_ANALYSED]
    job_status = [jobs.JOB_STATUS_KILLED, jobs.JOB_STATUS_CANCELED, jobs.JOB_STATUS_CANCELING]
    query = """SELECT p.uid AS uid, p.user_id AS user_id
                 FROM projects AS p
                WHERE p.status IN ("""+", ".join(["%s"]*len(project_status))+""")
                  AND p.uid NOT IN (
                        SELECT p.uid AS project_uid
                          FROM projects AS p
                          LEFT JOIN jobs AS j
                                 ON j.project_uid = p.uid
                          LEFT JOIN operations_history AS o
                                 ON j.operation_id = o.id
                         WHERE j.status NOT IN ("""+", ".join(["%s"]*len(job_status))+""")
                           AND o.operation_name IN ('anal', 'link')
                      )"""
    query_args = project_status + job_status
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(query, query_args).fetchall()
    if not result:
        return []
    return result


@core.api_util.need_db_context
def delete_project(user_id, project_codename):
    project = get_project(user_id, project_codename, include_deleted=True)
    if not project:
        raise RuntimeError("Unknown project " + project_codename)

    # Canceling all running jobs
    running_status = [jobs.JOB_STATUS_PENDING, jobs.JOB_STATUS_LAUNCHING, jobs.JOB_STATUS_RUNNING]
    query = "SELECT id FROM jobs WHERE project_uid = %s AND status IN ("+", ".join(["%s"]*len(running_status))+")"
    g_db = core.api_util.DatabaseContext.get_conn()
    running_jobs = g_db.execute(query, [project_codename] + running_status).fetchall()
    running_job_ids = [job['id'] for job in running_jobs]
    if running_job_ids:
        log.info("killing jobs " + repr(running_job_ids) + " from deleting project " + project_codename)
        jobs.cancel_jobs(running_job_ids)

    # Cleaning calculations
    calculations = g_db.execute("""SELECT * 
                                     FROM calculations 
                                    WHERE project_uid = %s 
                                      AND delete_date IS NULL""", [project_codename]).fetchall()
    for calc in calculations:
        status_file_id = calc['status_file_id']
        result_file_id = calc['result_file_id']
        iterations_file_id = calc['iterations_file_id']
        reduce_file_id = calc['reduce_file_id']
        internal_file_id = calc['internal_file_id']
        if status_file_id is not None:
            remove_file_from_project(user_id, project_codename, status_file_id)
        if result_file_id is not None:
            remove_file_from_project(user_id, project_codename, result_file_id)
        if iterations_file_id is not None:
            remove_file_from_project(user_id, project_codename, iterations_file_id)
        if reduce_file_id is not None:
            remove_file_from_project(user_id, project_codename, reduce_file_id)
        if internal_file_id is not None:
            remove_file_from_project(user_id, project_codename, internal_file_id)
        pg_util.delete_with_date(g_db, "calculations", calc['id'])

    # Cleaning meshes
    meshes = g_db.execute("SELECT * FROM meshes WHERE project_uid = %s AND delete_date IS NULL",
                          [project_codename]).fetchall()
    for mesh in meshes:
        file_id = mesh['result_file_id']
        if file_id is not None:
            remove_file_from_project(user_id, project_codename, file_id)
        pg_util.delete_with_date(g_db, "meshes", mesh['id'])

    # Cleaning project itself
    anal_file = get_file_by_key(user_id, project_codename, PROJECT_FILE_ANALYSED)
    if anal_file:
        remove_file_from_project(user_id, project_codename, anal_file['id'])
    project_file = get_file_by_key(user_id, project_codename, PROJECT_FILE_RAW)
    if project_file:
        remove_file_from_project(user_id, project_codename, project_file['id'])
    pg_util.hist_remove(g_db, "projects", [('uid', "=", project_codename)])
