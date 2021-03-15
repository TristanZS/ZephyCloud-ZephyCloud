# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core api
import logging

# Project specific libs
from lib import pg_util
import core.api_util


log = logging.getLogger("aziugo")

TASK_UPLOAD_AND_ANALYSE = "upload_and_analyse"
TASK_UPLOAD_AND_LINK = "upload_and_link"
TASK_MESH = "mesh"
TASK_CALC = "calc"
TASK_RESTART_CALC = "restart_calc"
TASK_CANCEL = "cancel"

JOB_STATUS_PENDING = 1
JOB_STATUS_LAUNCHING = 2
JOB_STATUS_RUNNING = 3
JOB_STATUS_CANCELED = 4
JOB_STATUS_KILLED = 5
JOB_STATUS_FINISHED = 6
JOB_STATUS_CANCELING = 4


def job_status_to_str(job_status):
    """
    Get the printable representation of a job status

    :param job_status:      The job status
    :type job_status:       int
    :return:                The string version of the job status
    :rtype:                 str
    """
    if job_status == JOB_STATUS_PENDING:
        return "pending"
    elif job_status == JOB_STATUS_LAUNCHING:
        return "launching"
    elif job_status == JOB_STATUS_RUNNING:
        return "running"
    elif job_status in (JOB_STATUS_CANCELED, JOB_STATUS_CANCELING):
        return "canceled"
    elif job_status == JOB_STATUS_KILLED:
        return "killed"
    elif job_status == JOB_STATUS_FINISHED:
        return "finished"
    else:
        raise RuntimeError("Unknown job status "+str(job_status))


def job_status_from_str(status_str):
    """
    Get a job status form it's string

    :param status_str:      The job status
    :type status_str:       str
    :return:                The string version of the job status
    :rtype:                 list[int]
    """
    if status_str == "pending":
        return [JOB_STATUS_PENDING]
    elif status_str == "launching":
        return [JOB_STATUS_LAUNCHING]
    elif status_str == "running":
        return [JOB_STATUS_RUNNING]
    elif status_str == "canceled":
        return [JOB_STATUS_CANCELED, JOB_STATUS_CANCELING]
    elif status_str == "killed":
        return [JOB_STATUS_KILLED]
    elif status_str == "finished":
        return [JOB_STATUS_FINISHED]
    else:
        raise RuntimeError("Unknown job status "+str(status_str))


@core.api_util.need_db_context
def list_jobs(user_id=None, project_uid=None, join_user=False, possible_status=None, offset=0, limit=None, order=None):
    """
    Get all jobs

    :param user_id:             The id of the user of the jobs. Optional, default None
    :type user_id:              int|None
    :param project_uid:         The project codename of the jobs you wants. Optional, default None
    :type project_uid:          string|None
    :param join_user:           Do we retrieve user login. Optional, default False
    :type join_user:            bool
    :param possible_status:     List of accepted status. Optional, default False
    :type possible_status:      None|list[int]
    :return:                    The jobs information
    :rtype:                     pg_util.PgList
    """
    where_conditions = []
    query_args = []
    if user_id:
        where_conditions.append("j.user_id = %s")
        query_args.append(user_id)
    if project_uid:
        where_conditions.append("j.project_uid = %s")
        query_args.append(project_uid)
    if possible_status:
        where_conditions.append("j.status IN (" + ", ".join(["%s"]*len(possible_status)) + ")")
        query_args.extend(possible_status)

    count_key = None
    if join_user:
        query = "SELECT j.*, u.login, u.email "
        if offset or limit:
            query += ", count(*) OVER() AS pagination_full_count"
            count_key = "pagination_full_count"
        query += " FROM jobs AS j LEFT JOIN users AS u ON u.id = j.user_id"
    else:
        query = "SELECT j.* "
        if offset or limit:
            query += ", count(*) OVER() AS pagination_full_count"
            count_key = "pagination_full_count"
        query += " FROM jobs AS j"
    if where_conditions:
        query += " WHERE "+" AND ".join(where_conditions)
    if order:
        query += " "+order.to_sql({"job_id": "j.id", "project_uid": "j.project_uid", "start_time": "j.start_time",
                                   "end_time": "j.end_time", "status": "j.status", "email": "u.email",
                                   "login": "u.login", "user_id": "j.user_id"})
    if limit:
        query += " LIMIT " + str(int(limit))
    if offset:
        query += " OFFSET " + str(int(offset))
    g_db = core.api_util.DatabaseContext.get_conn()
    query_results = g_db.execute(query, query_args).fetchall()
    return pg_util.PgList.from_result(query_results, count_key)


@core.api_util.need_db_context
def list_unfinished_jobs():
    unfinished_statuses = [JOB_STATUS_CANCELED, JOB_STATUS_KILLED, JOB_STATUS_FINISHED, JOB_STATUS_CANCELING]
    query = "SELECT j.* FROM jobs AS j WHERE status NOT IN ("+", ".join(["%s"]*len(unfinished_statuses))+")"
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(query, unfinished_statuses).fetchall()
    return pg_util.all_to_dict(result)


@core.api_util.need_db_context
def get_job_consume(job_id):
    """
    Count how much zephycoins have been spent on a job
    Warning: the result should almost always be negative

    :param job_id:      The job id
    :type job_id:       int
    :return:            The number of zephycoins burnt on this job
    :rtype:             int
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("""SELECT COALESCE(sum(amount), 0) FROM user_accounts
                             WHERE job_id = %s""", [job_id]).fetchval()


@core.api_util.need_db_context
def dequeue_task(job_id):
    """
    Remove a task for the queue

    :param job_id:      The id of the job to remove from the queue
    :type job_id:       int
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("""DELETE FROM task_queue WHERE job_id = %s""", [job_id])


@core.api_util.need_db_context
def get_task_info(job_id):
    """
    Get the task from the task queue

    :param job_id:      The id of the queued job
    :type job_id:       int
    :return:            The task info
    :rtype:             dict[str, any]
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.row_to_dict(g_db.execute("SELECT * FROM task_queue WHERE job_id = %s", [job_id]).fetchone())


@core.api_util.need_db_context
def set_job_status(job_id, status):
    """
    Set the status of a job

    :param job_id:      The id of the job to update
    :type job_id:       int
    :param status:      The new status
    :type status:       int
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    if status == JOB_STATUS_RUNNING:
        g_db.execute("""UPDATE jobs 
                               SET status = %s,
                                   start_time = now(),
                                   progress = 0.0
                             WHERE id = %s """, [status, job_id])
    elif status == JOB_STATUS_FINISHED:
        g_db.execute("""UPDATE jobs 
                           SET status = %s ,
                               end_time = now(),
                               progress = 1.0
                         WHERE id = %s """, [status, job_id])
    elif status in (JOB_STATUS_CANCELED, JOB_STATUS_KILLED):
        g_db.execute("""UPDATE jobs 
                           SET status = %s ,
                               end_time = now()
                         WHERE id = %s """, [status, job_id])
    else:
        g_db.execute("UPDATE jobs SET status = %s WHERE id = %s ", [status, job_id])


def save_job_log(job_id, log_file):
    """
    Save the log of a job

    :param job_id:          The id of the job
    :type job_id:           int
    :param log_file:        The path of the file containing the log
    :type log_file:         str
    """
    with open(log_file, "r") as fh:
        log_content = fh.read()
    save_job_text(job_id, log_content)


@core.api_util.need_db_context
def save_job_text(job_id, text):
    """
    Save the log of a job

    :param job_id:          The id of the job
    :type job_id:           int
    :param text:            the text of the log
    :type text:             str
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("UPDATE jobs SET logs = %s WHERE id = %s ", [text, int(job_id)])


@core.api_util.need_db_context
def list_tasks():
    """
    List all pending tasks

    :return:        All the tasks in the queue
    :rtype:         list[dict[str, any]]
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    return pg_util.all_to_dict(g_db.execute("SELECT * FROM task_queue").fetchall())


@core.api_util.need_db_context
def cancel_job(job_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        log.debug("adding cancellation in task queue")
        g_db.execute("""INSERT INTO task_queue 
                               VALUES (%s, %s, %s)
                        ON CONFLICT(job_id) DO UPDATE SET task = EXCLUDED.task""", [job_id, TASK_CANCEL, {}])
        g_db.execute("""UPDATE jobs 
                           SET status = %s,
                               end_time = now(),
                               progress = 0.0
                         WHERE id = %s """, [JOB_STATUS_CANCELING, job_id])
    with core.api_util.RedisContext.using_pubsub_conn() as r:
        try:
            channel = core.api_util.RedisContext.get_channel("launcher")
            r.publish(channel, str(TASK_CANCEL) + "_" + str(job_id))
            log.debug("redis cancellation publish")
        except StandardError as e:
            log.warning("Unable to connect to redis server: " + str(e))


@core.api_util.need_db_context
def cancel_jobs(job_id_list):
    if not job_id_list:
        return
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        g_db.execute("DELETE FROM task_queue WHERE job_id IN ("+", ".join(["%s"]*len(job_id_list))+")", job_id_list)
        g_db.execute("""UPDATE jobs 
                           SET status = %s ,
                               end_time = now(),
                               progress = 0.0
                         WHERE id IN ("""+", ".join(["%s"]*len(job_id_list))+")",
                     [JOB_STATUS_CANCELING]+job_id_list)

        g_db.executemany("""INSERT INTO task_queue
                                 VALUES (%s, %s, %s)
                            ON CONFLICT(job_id) DO UPDATE SET task = EXCLUDED.task""",
                         [[job_id, TASK_CANCEL, {}] for job_id in job_id_list])

    with core.api_util.RedisContext.using_pubsub_conn() as r:
        channel = core.api_util.RedisContext.get_channel("launcher")
        for job_id in job_id_list:
            try:
                r.publish(channel, str(TASK_CANCEL) + "_" + str(job_id))
                log.debug("redis cancellation publish")
            except StandardError as e:
                log.warning("Unable to connect to redis server: " + str(e))


@core.api_util.need_db_context
def push_task(job_id, task, **params):
    """
    Put an existing job into the task queue

    :param job_id:      The job id to queue
    :type job_id:       int
    :param task:        The kind of job to do (ex: CREATE_AND_ANALYSE)
    :type task:         str
    :param params:      All the tasks to run
    :type params:       any
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("INSERT INTO task_queue VALUES (%s, %s, %s)", [job_id, task, params])
    with core.api_util.RedisContext.using_pubsub_conn() as r:
        try:
            channel = core.api_util.RedisContext.get_channel("launcher")
            r.publish(channel, str(task)+"_"+str(job_id))
        except StandardError as e:
            log.warning("Unable to connect to redis server: "+str(e))


@core.api_util.need_db_context
def get_job(job_id, include_log=False):
    """
    Get the job information, and optionally the relative specific fields

    :param job_id:          The id of the job
    :type job_id:           int
    :return:                The job information, or None if the job is not found
    :rtype:                 dict[str, any]|None
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    if include_log:
        job = g_db.execute("""SELECT id, user_id, project_uid, status, progress, operation_id, provider_cost_id, 
                                     machine_price_id, nbr_machines, create_date, start_time, end_time, logs, debug,
                                     TRIM(COALESCE(logs, '')) <> '' AS has_logs
                                FROM jobs 
                               WHERE id = %s""", [job_id]).fetchone()
    else:
        job = g_db.execute("""SELECT id, user_id, project_uid, status, progress, operation_id, provider_cost_id, 
                                     machine_price_id, nbr_machines, create_date, start_time, end_time, debug,
                                     TRIM(COALESCE(logs, '')) <> '' AS has_logs
                                FROM jobs 
                               WHERE id = %s""", [job_id]).fetchone()
    return pg_util.row_to_dict(job)


@core.api_util.need_db_context
def create_job(user_id, project_codename, operation_id, provider_cost_id=None, machine_price_id=None,
               nbr_machines=1, status=JOB_STATUS_PENDING):
    """
    Create a new job

    :param user_id:                 The job owner
    :type user_id:                  int
    :param project_codename:        The project unique identifier
    :type project_codename:         str
    :param operation_id:            The identifier of a specific operation.
    :type operation_id:             int
    :param provider_cost_id:        The cost associated with the task. Optional, default None
    :type provider_cost_id:         int|None
    :param machine_price_id:        The price of the worker to launch. Optional, default None
    :type machine_price_id:         int|None
    :param nbr_machines:            The number of workers to launch. Optional, default 1
    :type nbr_machines:             int
    :param status:                  The initial status of the job. Optional, default JOB_STATUS_PENDING
    :type status:                   int
    :return:                        The created job
    :rtype:                         dict[str, any]
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        g_db.execute("""INSERT INTO jobs (user_id, project_uid, operation_id, provider_cost_id, machine_price_id, 
                                          status, nbr_machines)
                                  VALUES (%s, %s, %s, %s, %s, %s, %s)
                               RETURNING id""",
                     [user_id, project_codename, operation_id, provider_cost_id, machine_price_id, status,
                      nbr_machines])
        job_id = g_db.fetchval()
        return get_job(job_id)


@core.api_util.need_db_context
def set_job_progress(job_id, progress):
    """
    Set job progress

    :param job_id:      The id of the job to update
    :type job_id:       int
    :param progress:    THe progression of the job. Between 0 and 1
    :type progress:     float
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("UPDATE jobs SET progress = %s WHERE id = %s ", [max(0.0, min(1.0, progress)), job_id])


@core.api_util.need_db_context
def set_job_specific_cost(job_id, provider_code, machine_code, cost, currency, sec_granularity, min_sec_granularity):
    """
    Save specific cost from spot instance

    :param job_id:                  The job id of the task used for
    :type job_id:                   int
    :param provider_code:           The code of the provider (ex: "aws_eu_spot")
    :type provider_code:            str
    :param machine_code:            The code of the instance to run (ex: "c4.2x")
    :type machine_code:             str
    :param cost:                    The cost of the second multiplied by the precision
    :type cost:                     int
    :param currency:                The currency of the cost
    :type currency:                 str
    """
    g_db = core.api_util.DatabaseContext.get_conn()
    with pg_util.Transaction(g_db):
        machine_uid = g_db.execute("""SELECT uid 
                                              FROM machines         
                                             WHERE machine_code = %s 
                                               AND provider_code = %s 
                                             LIMIT 1""", [machine_code, provider_code]).fetchval()
        now = pg_util.get_now(g_db)
        query_args = [machine_uid, cost, currency, sec_granularity, min_sec_granularity, now, now]
        g_db.execute("""INSERT INTO provider_costs_history (machine_uid, cost_per_sec, currency, sec_granularity, 
                                                            min_sec_granularity, start_time, end_time)
                                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                                 RETURNING id""", query_args)
        row_id = g_db.fetchval()
        cost_id = g_db.execute("SELECT id FROM provider_costs_history WHERE id = %s", [row_id]).fetchval()
        g_db.execute("UPDATE jobs SET provider_cost_id = %s WHERE id = %s ", [cost_id, job_id])


@core.api_util.need_db_context
def get_running_machines(provider_code, machine_code):
    running_statuses = [JOB_STATUS_PENDING, JOB_STATUS_LAUNCHING, JOB_STATUS_RUNNING]
    query = """SELECT SUM(j.nbr_machines) 
                 FROM machines AS m
                 LEFT JOIN machine_prices_history AS mp
                        ON mp.machine_uid = m.uid 
                 LEFT JOIN jobs AS j
                        ON j.machine_price_id = mp.id
                WHERE m.machine_code = %s
                  AND m.provider_code = %s
                  AND j.status IN ("""+", ".join(["%s"]*len(running_statuses))+""")
                GROUP BY m.machine_code, m.provider_code"""
    query_args = [machine_code, provider_code] + running_statuses
    g_db = core.api_util.DatabaseContext.get_conn()
    result = g_db.execute(query, query_args).fetchone()
    if result:
        return int(result[0])
    else:
        return 0


@core.api_util.need_db_context
def get_running_machines_list(provider_code):
    running_statuses = [JOB_STATUS_PENDING, JOB_STATUS_LAUNCHING, JOB_STATUS_RUNNING]
    query = """SELECT m.machine_code, COALESCE(SUM(j.nbr_machines), 0)
                 FROM machines AS m
                 LEFT JOIN machine_prices_history AS mp
                        ON mp.machine_uid = m.uid 
                 LEFT JOIN jobs AS j
                        ON j.machine_price_id = mp.id
                  AND m.provider_code = %s
                  AND j.status IN ("""+", ".join(["%s"]*len(running_statuses))+""")
                 GROUP BY m.machine_code"""
    query_args = [provider_code] + running_statuses
    results = {}
    g_db = core.api_util.DatabaseContext.get_conn()
    for line in g_db.execute(query, query_args).fetchall():
        results[line[0]] = int(line[1])
    return results


@core.api_util.need_db_context
def disable_shutdown(job_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    g_db.execute("UPDATE jobs SET debug = %s WHERE id = %s", [True, job_id])


@core.api_util.need_db_context
def is_shutdown_disabled(job_id):
    g_db = core.api_util.DatabaseContext.get_conn()
    return g_db.execute("SELECT debug FROM jobs WHERE id = %s", [job_id]).fetchval()
