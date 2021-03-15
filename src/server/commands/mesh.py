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
import models.meshes
from core import api_util
from core import cmd_util
from core import storages

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMMAND_NAME = "mesh"
DO_NOT_KILL_INSTANCES = False
IS_TOOLCHAIN_SECURED = True
REMOVE_RESULTS_ON_ERROR = True


log = logging.getLogger("aziugo")


def run(api_name, server_name, job_id, project_codename, mesh_param_file, mesh_name, provider_name, machine,
        nbr_machines, client_login, client_ip, api_version):
    """
    Run the given mesh job

    :param api_name:                The name of the api
    :type api_name:                 str
    :param server_name:             The name of the server (ex: apidev.zephycloud.com)
    :type server_name:              str
    :param job_id:                  the id of the job to run
    :type job_id:                   int
    :param project_codename:        The uid of the project
    :type project_codename:         str
    :param mesh_param_file:         The param file used to configure the mesh
    :type mesh_param_file:          str
    :param mesh_name:               The name of the mesh to generate
    :type mesh_name:                str
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

    try:
        # Configure better logging name
        cmd_util.config_cmd_log(COMMAND_NAME, job_id)

        # Loading required information from database
        job = models.jobs.get_job(job_id)
        if not job:
            raise api_util.ToolchainError("Unknown job " + str(job_id))
        models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_RUNNING)
        project = models.projects.get_project(job['user_id'], project_codename)
        if not project:
            raise api_util.ToolchainError("Unknown project " + str(job["project_uid"]) + " for user " + str(job['user_id']))
        user_id = project["user_id"]

        try:
            models.meshes.set_job(user_id, project_codename, mesh_name, job_id)
            models.meshes.set_mesh_status(user_id, project_codename, mesh_name, models.meshes.STATUS_RUNNING)
            compute_mesh(api_name, server_name, job, project, mesh_param_file, mesh_name, provider_name, machine,
                         nbr_machines, client_login, client_ip, api_version)
            models.meshes.set_mesh_status(user_id, project_codename, mesh_name, models.meshes.STATUS_COMPUTED)
        except api_util.abort_errors:
            with error_util.before_raising():
                models.meshes.set_mesh_status(user_id, project_codename, mesh_name, models.meshes.STATUS_CANCELED)
        except error_util.all_errors:
            with error_util.before_raising():
                models.meshes.set_mesh_status(user_id, project_codename, mesh_name, models.meshes.STATUS_KILLED)
    finally:
        if os.path.exists(mesh_param_file):
            os.remove(mesh_param_file)


def compute_mesh(api_name, server_name, job, project, mesh_param_file, mesh_name, provider_name, machine, nbr_machines,
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
    :param mesh_param_file:         The param file used to configure the mesh
    :type mesh_param_file:          str
    :param mesh_name:               The name of the mesh to generate
    :type mesh_name:                str
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
    user_id = project["user_id"]
    project_codename = project['uid']
    mesh_filename = job["project_uid"] + "-mesh-" + str(job_id) + ".zip"
    provider = api_util.get_provider(provider_name)
    storage = api_util.get_storage(project['storage'])
    tmp_folder = api_util.get_conf().get("general", "tmp_folder")
    mesh_file = cmd_util.ResultFile(project_codename, mesh_filename)
    preview_file = cmd_util.ResultFile(project_codename, "preview.zip")
    tags = {
        'operation': "mesh",
        'job_id': str(job_id),
        'server': server_name,
        'api': api_name,
        'api_version': api_version,
        'client': client_login,
        'client_ip': client_ip,
        'trusted': IS_TOOLCHAIN_SECURED
    }

    models.users.charge_user_fix_price(user_id, job_id, "Mesh storage cost")
    try:
        with cmd_util.using_workers(api_name, provider, job_id, machine, nbr_machines, tags,
                                    debug_keep_instances_alive=DO_NOT_KILL_INSTANCES) as workers:
            # Launching aziugo process launcher
            with cmd_util.TaskProcess(job_id, job["project_uid"], "mesh", workers) as task_proc:
                conn = workers.ssh_connection
                # Charge user
                end_time = models.users.charge_user_computing(user_id, job_id, "Cloud computation cost")
                if models.users.get_credit(user_id) <= 0:
                    raise api_util.NoMoreCredits()

                log.info("Sending project files on worker")
                worker_in_storage = storages.SshStorage(conn, api_util.WORKER_INPUT_PATH, IS_TOOLCHAIN_SECURED)
                cmd_util.copy_project_file(user_id, project_codename, storage, worker_in_storage, "project_file.zip",
                                           tmp_folder, key=models.projects.PROJECT_FILE_RAW)
                cmd_util.copy_project_file(user_id, project_codename, storage, worker_in_storage, "anal.zip",
                                           tmp_folder, key=models.projects.PROJECT_FILE_ANALYSED)
                worker_in_storage.upload_file(mesh_param_file, "mesh_params.zip")
                os.remove(mesh_param_file)
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
                log_file = util.path_join(api_util.WORKER_OUTPUT_PATH, "worker.log")
                if conn.file_exists(log_file):
                    with file_util.temp_filename(dir=tmp_folder) as tmp:
                        conn.get_file(log_file, tmp)
                        models.jobs.save_job_log(job_id, tmp)
                else:
                    log.warning("No worker log file")

                worker_out_storage = storages.SshStorage(conn, api_util.WORKER_OUTPUT_PATH, IS_TOOLCHAIN_SECURED)
                if not mesh_file.exists(worker_out_storage):
                    log.error("Unable to find file " + str(mesh_file) + " on worker")
                    raise api_util.ToolchainError("Task failed, no result file")
                mesh_file.save_on_storage(worker_out_storage, storage, tmp_folder)
                if preview_file.exists(worker_out_storage):
                    preview_file.save_on_storage(worker_out_storage, storage, tmp_folder)
                else:
                    log.warning("No preview found on server")

                # Signaling all output was fetched
                task_proc.stop_and_wait()

        # Charge again if required
        if datetime.datetime.utcnow() > end_time:
            models.users.charge_user_computing(user_id, job_id, "Cloud computation cost")

        # Uploading file on cloud storage
        mesh_file.save_in_database(user_id)
        preview_file_id = preview_file.save_in_database(user_id) if preview_file.saved else None
        models.meshes.save_mesh_files(user_id, project_codename, mesh_name, mesh_file.file_id, preview_file_id)
    except error_util.all_errors:
        with error_util.before_raising():
            if REMOVE_RESULTS_ON_ERROR:
                mesh_file.delete_from_distant(storage)
                preview_file.delete_from_distant(storage)
    log.info("Results saved")
