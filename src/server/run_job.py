#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120


# Python core api
import sys
import logging
import logging.handlers
import os
import time
import datetime
import argparse
import exceptions
import signal
import subprocess

# Third party libraries
import colorlog
import setproctitle

# Project specific libs
from lib import util
from lib import type_util
from lib import proc_util
from lib import error_util
import commands.upload_and_analyze
import commands.upload_and_link
import commands.mesh
import commands.calc
import commands.restart_calc
import core.api_util
import models.jobs

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

log = logging.getLogger("aziugo")

IGNORE_SIGNAL_DELAY = datetime.timedelta(milliseconds=500)
# CANCEL_JOB_TIMEOUT = 300


class SignalMemory(object):
    """ Class used to store global memory of the datetime of the last abort message received """
    last_signal_received = datetime.datetime.utcfromtimestamp(0)


def raise_keyboard_interrupt(signal_code, *_):
    """ Callback called when SIGINT or SIGTERM are received """
    received = datetime.datetime.utcnow()
    if (received - SignalMemory.last_signal_received) > IGNORE_SIGNAL_DELAY:
        SignalMemory.last_signal_received = received
        log.warning("Signal received ("+str(signal_code)+"), exiting...")
        raise KeyboardInterrupt()
    else:
        log.warning("Signal received twice ("+str(signal_code)+"). Ignoring it")


def init_data_sources(api_name, server_name, redis_host, redis_port, data_db, pubsub_db):
    core.api_util.DatabaseContext.load_conf()
    core.api_util.RedisContext.set_params(api_name, server_name, redis_host, redis_port, data_db, pubsub_db)


def init_process(fork, api_name, job_id, toolchain):
    if fork:
        try:
            in_child, parent_pid, child_pid = proc_util.double_fork()
        except exceptions.OSError as e:
            log.error("Unable to run command, fork failed, cause:")
            error_util.log_error(log, e)
            return False

        if not in_child:
            return False # Nothing to do in parent, we continue the main loop

    signal.signal(signal.SIGTERM, raise_keyboard_interrupt)
    signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    try:
        setproctitle.setproctitle(api_name + " " + toolchain + " job " + str(job_id))
    except StandardError as e:
        log.warning(str(e))
    return True


def run_toolchain(api_name, server_name, job_id, toolchain):
    """
    Execute a task, which could be to cancel a running toolchain or to launch a specific toolchain.
    It will launch a separated subprocess and return before task is completed

    :param api_name:            The name of current API
    :type api_name:             str
    :param server_name:         The fqdn of current server
    :type server_name:          str
    :param job_id:              The is of the job the task is related to
    :type job_id:               int
    :param toolchain:           The task to launch
    :type toolchain:            str
    """
    # FIXME: Disable because it lock the database: with core.api_util.DatabaseContext.using_conn():
    try:
        task = models.jobs.get_task_info(job_id)
        if not task:
            log.info("Job " + str(job_id) + " is already running, skipping")
            return
        models.jobs.dequeue_task(job_id)
        job = models.jobs.get_job(job_id)
        if not job:
            log.error("Unknown job " + str(job_id))
        time.sleep(0.2)
        if int(job['status']) != models.jobs.JOB_STATUS_PENDING:
            log.info("Job " + str(job_id) + " already launched, skipping")
            return

        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_LAUNCHING)
        with core.api_util.RedisContext.using_data_conn() as r:
            r.set(api_name + ":" + server_name + ":job-" + str(job_id) + "-pid", int(os.getpid()))
        if toolchain != task['task']:
            log.error("Bad task toolchain")
            return
        if toolchain == models.jobs.TASK_UPLOAD_AND_ANALYSE:
            commands.upload_and_analyze.run(api_name, server_name, job_id, **task["params"])
        elif toolchain == models.jobs.TASK_UPLOAD_AND_LINK:
            commands.upload_and_link.run(api_name, server_name, job_id, **task["params"])
        elif toolchain == models.jobs.TASK_MESH:
            commands.mesh.run(api_name, server_name, job_id, **task["params"])
        elif toolchain == models.jobs.TASK_CALC:
            commands.calc.run(api_name, server_name, job_id, **task["params"])
        elif toolchain == models.jobs.TASK_RESTART_CALC:
            commands.restart_calc.run(api_name, server_name, job_id, **task["params"])
        else:
            log.error("Task not implemented: " + str(toolchain))
            return
        log.info("Command successfully finished")
    except core.api_util.abort_errors:
        log.warning("Operation canceled")
        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_CANCELED)
    except core.api_util.ToolchainError as e:
        log.error(str(e))
        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_KILLED)
    except error_util.all_errors as e:
        error_util.log_error(log, e)
        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_KILLED)
    else:
        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_FINISHED)
    finally:
        with core.api_util.RedisContext.using_data_conn() as redis_conn:
            redis_conn.delete(api_name + ":" + server_name + ":job-" + str(job_id) + "-pid")
    sys.exit(0)


def main():
    """
    Parse command arguments, initialize log and start the job

    :return:        0 in case of success, between 1 and 127 in case of failure
    :rtype:         int
    """

    # Initialise and parse command arguments
    parser = argparse.ArgumentParser(description="Run a specific job")
    parser.add_argument('--fork', "-f", action="store_true", help="Run double fork to daemonize the process")
    parser.add_argument('--redis-host', '-H', help="Redis-server host")
    parser.add_argument('--redis-port', '-P', help='Redis-server connection port')
    parser.add_argument('--redis-data-db', '-i', help="Redis-server database index for data")
    parser.add_argument('--redis-pubsub-db', '-j', help="Redis-server database index for events")
    parser.add_argument('--log-level', '-l', help="log level (ex: info)")
    parser.add_argument('--log-output', help="log out, file path, 'syslog', 'stderr' or 'stdout'")
    parser.add_argument('job_id', type=int, help="The id of the job to run")
    parser.add_argument('toolchain', help="The toolchain to launch")

    args = parser.parse_args()

    # Load config
    conf = core.api_util.get_conf()
    api_name = conf.get('general', 'api_name')
    server_name = conf.get('general', "server")

    # Initialise logging
    if args.log_level:
        log_level = args.log_level.strip().upper()
    elif conf.has_section("log") and conf.has_option("log", "server_level"):
        log_level = conf.get("log", "server_level").strip().upper()
    else:
        log_level = "WARNING"
    log_level_int = logging.getLevelName(log_level)
    if not type_util.is_int(log_level_int):
        sys.stderr.write("Error: Invalid logging level "+repr(log_level)+"\n")
        sys.stderr.flush()
        return 1
    logging.getLogger().setLevel(logging.INFO if log_level_int < logging.INFO else log_level_int)
    log.setLevel(log_level_int)

    if args.log_output:
        log_output = args.log_output.strip().lower()
    elif conf.has_section("log") and conf.has_option("log", "server_output"):
        log_output = conf.get("log", "server_output").strip().lower()
    else:
        log_output = "stderr"
    if log_output in ("stderr", "stdout"):
        log_file = sys.stderr if log_output == "stderr" else sys.stdout
        if log_file.isatty():
            use_color = not util.env_is_off("LOG_COLOR")
        else:
            use_color = util.env_is_on("LOG_COLOR")
        if use_color:
            log_format = "%(log_color)s%(levelname)-8s%(blue)s%(name)-16s%(reset)s %(white)s%(message)s"
            log_handler = colorlog.StreamHandler(stream=log_file)
            log_handler.setFormatter(colorlog.ColoredFormatter(log_format))
        else:
            log_handler = logging.StreamHandler(stream=log_file)
            log_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    elif log_output == "syslog":
        log_handler = logging.handlers.SysLogHandler(address='/dev/log')
        log_handler.setFormatter(logging.Formatter('%(levelname)s %(module)s P%(process)d T%(thread)d %(message)s'))
    else:
        log_handler = logging.FileHandler(log_output)
        log_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-7s: %(name)s - %(message)s'))
    logging.getLogger().addHandler(log_handler)
    log.addHandler(log_handler)
    log.propagate = False

    # Get Redis config
    if args.redis_host:
        redis_host = args.redis_host.strip()
    elif conf.has_section("redis") and conf.has_option("redis", "host"):
        redis_host = conf.get("redis", "host").strip()
    else:
        redis_host = "localhost"
    if args.redis_port:
        redis_port = int(args.redis_port.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "port"):
        redis_port = int(conf.get("redis", "port").strip())
    else:
        redis_port = 6379
    if args.redis_data_db:
        data_db = int(args.redis_data_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "data_db"):
        data_db = int(conf.get("redis", "data_db").strip())
    else:
        data_db = 0
    if args.redis_pubsub_db:
        pubsub_db = int(args.redis_pubsub_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "pubsub_db"):
        pubsub_db = int(conf.get("redis", "pubsub_db").strip())
    else:
        pubsub_db = 1

    # Launch the main function
    try:
        if init_process(args.fork, api_name, int(args.job_id), args.toolchain):
            init_data_sources(api_name, server_name, redis_host, redis_port, data_db, pubsub_db)
            run_toolchain(api_name, server_name, int(args.job_id), args.toolchain)
    except KeyboardInterrupt:
        logging.getLogger("aziugo").info("Signal received, exiting")
        return 0
    except (StandardError, subprocess.CalledProcessError) as e:
        logging.getLogger("aziugo").exception(str(e))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
