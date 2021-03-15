# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python libs
import time
import logging
import os
import datetime

# Project Specific libs
from lib import util
from lib import file_util
from lib import error_util
import models.jobs
import models.projects
import models.users
import models.provider_config
from core import api_util
from core import cmd_util
from core import storages

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMMAND_NAME = "upload_and_analyze"
DO_NOT_KILL_INSTANCES = False
IS_TOOLCHAIN_SECURED = True
REMOVE_RESULTS_ON_ERROR = True


log = logging.getLogger("aziugo")


def run(api_name, server_name, job_id, project_file, provider, machine, nbr_machines, storage, client_login, client_ip,
        api_version):
    """
    Upload project file, analyse them and save analysis

    :param api_name:                The name of the api
    :type api_name:                 str
    :param server_name:             The name of the server (ex: apidev.zephycloud.com)
    :type server_name:              str
    :param job_id:                  the id of the job to run
    :type job_id:                   int
    :param project_file:            The raw project file to analyse
    :type project_file:             str
    :param provider:                The name of the provider
    :type provider:                 str
    :param machine:                 The type of machine to launch
    :type machine:                  str
    :param nbr_machines:            The number of machines to run
    :type nbr_machines:             int
    :param storage:                 The name of the storage where the project will be located
    :type storage:                  str
    :param client_login:            The login of the job owner
    :type client_login:             str
    :param client_ip:               The client ip address of the http request string this job
    :type client_ip:                str
    :param api_version:             The version of the http api where the user ask to launch this job
    :type api_version:              str
    """
    try:
        # Configure better logging name
        cmd_util.config_cmd_log(COMMAND_NAME, job_id)

        # Loading required information from database
        job = models.jobs.get_job(job_id)
        if not job:
            raise api_util.ToolchainError("Unknown job " + str(job_id))
        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_RUNNING)
        project = models.projects.get_project(job['user_id'], job['project_uid'])
        if not project:
            raise api_util.ToolchainError("Unknown project " + str(job['project_uid']) + " for user " + str(job['user_id']))

        try:
            models.projects.set_project_status(project["user_id"], job["project_uid"],
                                               models.projects.PROJECT_STATUS_ANALYSING)
            analyse(api_name, server_name, job, project, storage, project_file, provider, machine, nbr_machines,
                    client_login, client_ip, api_version)
            models.projects.set_project_status(project["user_id"], job["project_uid"],
                                               models.projects.PROJECT_STATUS_ANALYSED)
        except error_util.all_errors:
            with error_util.before_raising():
                models.projects.set_project_status(project["user_id"], job["project_uid"],
                                                   models.projects.PROJECT_STATUS_RAW)
    finally:
        if os.path.exists(project_file):
            os.remove(project_file)


def analyse(api_name, server_name, job, project, storage_name, project_file, provider_name, machine, nbr_machines,
            client_login, client_ip, api_version):
    """
    Launch the machine(s), send the files, start the worker script, wait for progress and results and saving results

    :param api_name:                The name of the api
    :type api_name:                 str
    :param server_name:             The name of the server (ex: apidev.zephycloud.com)
    :type server_name:              str
    :param job:                     The job information
    :type job:                      dict[str, any]
    :param project:                 The main project
    :type project:                  dict[str, any]
    :param storage_name:            The name of the storage where the project will be located
    :type storage_name:             str
    :param project_file:            The raw project file to analyse
    :type project_file:             str
    :param provider_name:           The name of the provider
    :type provider_name:            str
    :param machine:                 The type of machine to launch
    :type machine:                  str
    :param nbr_machines:            The number of machines to run
    :type nbr_machines:             int
    :param client_login:            The login of the job owner
    :type client_login:             str
    :param client_ip:               The client ip address of the http request string this job
    :type client_ip:                str
    :param api_version:             The version of the http api where the user ask to launch this job
    :type api_version:              str
    """
    job_id = int(job['id'])
    project_codename = job["project_uid"]
    analyzed_filename = job["project_uid"] + "-anal-" + str(job_id) + ".zip"
    user_id = project["user_id"]
    provider = api_util.get_provider(provider_name)
    storage = api_util.get_storage(storage_name)
    tmp_folder = api_util.get_conf().get("general", "tmp_folder")

    tags = {
        'operation': "anal",
        'job_id': str(job_id),
        'server': server_name,
        'api': api_name,
        'api_version': api_version,
        'client': client_login,
        'client_ip': client_ip,
        'trusted': IS_TOOLCHAIN_SECURED
    }

    # Uploading file on cloud storage
    log.info("Uploading project file to storage")
    models.projects.append_file_to_project(user_id, job["project_uid"], project_file,
                                           "project_"+job["project_uid"]+".zip",
                                           key=models.projects.PROJECT_FILE_RAW, overwrite=True)
    log.info("Project file uploaded")

    models.users.charge_user_fix_price(user_id, job_id, "Project storage cost")
    analyzed_file = cmd_util.ResultFile(project_codename, analyzed_filename)
    try:
        # Creating worker
        with cmd_util.using_workers(api_name, provider, job_id, machine, nbr_machines, tags,
                                    debug_keep_instances_alive=DO_NOT_KILL_INSTANCES) as workers:
            with cmd_util.TaskProcess(job_id, job["project_uid"], "anal", workers) as task_proc:
                conn = workers.ssh_connection
                # Charge user
                end_time = models.users.charge_user_computing(user_id, job_id, "Cloud computation cost")
                if models.users.get_credit(user_id) <= 0:
                    raise api_util.NoMoreCredits()

                log.info("Sending project files on worker")
                conn.send_file(project_file, util.path_join(api_util.WORKER_INPUT_PATH, "project_file.zip"))
                os.remove(project_file)
                log.info("Project files sent to the worker")

                # Tell the script to start
                log.info("Starting the computation")
                task_proc.start()
                while True:
                    task_status = task_proc.check_status()

                    # Charge if we need
                    if datetime.datetime.utcnow() > end_time:
                        end_time = models.users.charge_user_computing(user_id, job_id, "Cloud computation cost")
                        if models.users.get_credit(user_id) <= 0:
                            models.jobs.save_job_text(job_id, "No more credit")
                            raise api_util.NoMoreCredits()

                    if task_status != models.jobs.JOB_STATUS_RUNNING:
                        log.info("Computation finished with status: " + models.jobs.job_status_to_str(task_status))
                        break
                    time.sleep(5)

                # Checking if the machine is still here
                if not conn.ping():
                    models.jobs.save_job_text(job_id, "Worker instance disappeared")
                    raise api_util.ToolchainError("Worker instance disappeared")

                # Fetching computed data
                log.info("Fetching results")
                worker_out_storage = storages.SshStorage(conn, api_util.WORKER_OUTPUT_PATH, IS_TOOLCHAIN_SECURED)
                log_file = util.path_join(api_util.WORKER_OUTPUT_PATH, "worker.log")
                if conn.file_exists(log_file):
                    with file_util.temp_filename(dir=tmp_folder) as tmp:
                        conn.get_file(log_file, tmp)
                        models.jobs.save_job_log(job_id, tmp)
                else:
                    log.warning("No worker log file")

                if not analyzed_file.exists(worker_out_storage):
                    log.error("Unable to find file " + str(analyzed_file) + " on worker")
                    raise api_util.ToolchainError("Task failed, no result file")
                analyzed_file.save_on_storage(worker_out_storage, storage, tmp_folder)
                log.info("Computation result fetched")

                # Signaling all output was fetched
                task_proc.stop_and_wait()

        # Charge again if required
        if datetime.datetime.utcnow() > end_time:
            models.users.charge_user_computing(project["user_id"], job_id, "Cloud computation cost")

        # Uploading file on cloud storage
        analyzed_file.save_in_database(user_id, key=models.projects.PROJECT_FILE_ANALYSED)
    except error_util.all_errors:
        with error_util.before_raising():
            if REMOVE_RESULTS_ON_ERROR:
                analyzed_file.delete_from_distant(storage)
    log.info("Result saved")
