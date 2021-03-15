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
import models.calc
import models.meshes
from core import api_util
from core import cmd_util
from core import storages

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMMAND_NAME = "recalc"
STATUS_FETCHING_DELAY = 120
DO_NOT_KILL_INSTANCES = False
IS_TOOLCHAIN_SECURED = True
REMOVE_RESULTS_ON_ERROR = True


log = logging.getLogger("aziugo")


def run(api_name, server_name, job_id, project_codename, calc_id, calc_param_file, provider_name, machine, nbr_machines,
        nbr_iterations, split_results, client_login, client_ip, api_version):
    """
    Run a calculation that has already be partially computed

    :param api_name:                The name of the api
    :type api_name:                 str
    :param server_name:             The name of the server (ex: apidev.zephycloud.com)
    :type server_name:              str
    :param job_id:                  the id of the job to run
    :type job_id:                   int
    :param project_codename:        The uid of the project
    :type project_codename:         str
    :param calc_id:                 The id of the calculation
    :type calc_id:                  int
    :param calc_param_file:         The name of the param file
    :type calc_param_file:          str
    :param provider_name:           The name of the provider
    :type provider_name:            str
    :param machine:                 The type of machine to launch
    :type machine:                  str
    :param nbr_machines:            The number of machines to run
    :type nbr_machines:             int
    :param nbr_iterations:          The number of iteration the calculation should run
    :type nbr_iterations:           int
    :param split_results:           Do you want to split the results?
    :type split_results:            bool
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
            raise api_util.ToolchainError("Unknown project " + str(job['project_uid']))
        user_id = project["user_id"]

        calculation = models.calc.get_calc(user_id, project['uid'], calc_id)
        if not calculation:
            raise api_util.ToolchainError("Unknown calculation " + str(calc_id))
        calc_name = calculation['name']
        old_status = calculation['status']
        try:
            models.calc.set_job(user_id, project_codename, calc_name, job_id)
            models.calc.set_calc_status(user_id, project_codename, calc_name, models.calc.STATUS_RUNNING)
            recalculate(api_name, server_name, job, project, calculation, calc_param_file, provider_name, machine,
                        nbr_machines, nbr_iterations, split_results, client_login, client_ip, api_version)
            calculation = models.calc.get_calc(user_id, project['uid'], calc_id)
            if calculation['status'] != models.calc.STATUS_STOPPED:
                models.calc.set_calc_status(user_id, project_codename, calc_name, models.calc.STATUS_COMPUTED)
        except error_util.all_errors:
            with error_util.before_raising():
                models.calc.set_calc_status(user_id, project_codename, calc_name, old_status)
    finally:
        if os.path.exists(calc_param_file):
            os.remove(calc_param_file)


def fetch_progress(conn, user_id, project_codename, calc_name, calc_id, storage, tmp_folder):
    """
    Check if a progress file has been created on the main worker and save it if it exists

    :param conn:                    The ssh connection to the main worker
    :type conn:                     ssh.SshConnection
    :param user_id:                 The id of the job owner
    :type user_id:                  int
    :param project_codename:        The project uuid
    :type project_codename:         str
    :param calc_name:               The name of the calculation
    :type calc_name:                str
    :param calc_id:                 The id of the calculation
    :type calc_id:                  int
    :param storage:                 The storage of the project
    :type storage:                  core.ssh.Storage
    :param tmp_folder:              A temporary folder to use
    :type tmp_folder:               str
    :return:                        True if success, False if no file is found or a failure happens
    :rtype:                         bool
    """
    status_file_name = project_codename + "_calc_" + calc_name + "_status.zip"
    status_file = cmd_util.ResultFile(project_codename, status_file_name)
    old_status_file = None
    try:
        calc_dir = util.path_join(api_util.WORKER_WORK_PATH, "ZephyTOOLS", "PROJECTS_CFD", project_codename, "CALC")
        if not conn.folder_exists(calc_dir):
            log.debug("calc folder " + calc_dir + " doesn't exists yet, skipping...")
            return True
        _, out, _ = conn.run(["find", calc_dir, "-mindepth", "1", "-maxdepth", "1", "-type", "d"])
        out = out.strip()
        if not out or "\n" in out:  # No results or more than one result
            log.warning("Unable to get the calculation output folder")
            return
        calc_dir = out.rstrip("/")
        zipper_command = util.path_join(api_util.WORKER_WORK_PATH, "ZephyTOOLS", "APPLI", "TMP",
                                        "CFD_CALC_ZIP_STATUS.py")
        old_status_file = models.calc.get_calc_status_file(user_id, project_codename, calc_id)
        status_file_path = util.path_join(api_util.WORKER_OUTPUT_PATH, status_file_name)
        conn.run(["python", zipper_command, "-i", calc_dir, "-o", status_file_path])
        worker_out_storage = storages.SshStorage(conn, api_util.WORKER_OUTPUT_PATH, IS_TOOLCHAIN_SECURED)
        if not status_file.exists(worker_out_storage):
            log.warning("Unable to get calculation status file: file not found")
            return False
        status_file.save_on_storage(worker_out_storage, storage, tmp_folder)
        file_id = status_file.save_in_database(user_id)
        models.calc.save_status_file(user_id, project_codename, calc_id, file_id)
    except error_util.all_errors as e:
        with error_util.saved_stack() as error_stack:
            status_file.delete_from_distant(storage)
            if error_util.is_abort(e):
                error_stack.reraise()
            else:
                error_util.log_error(log, e)
                return False
    if old_status_file:
        models.projects.remove_file_from_project(user_id, project_codename, old_status_file['id'])
    return True


def stop_calc(conn, project_codename):
    """
    Tell the calculation to stop, running a specific script on the worker

    :param conn:                    The ssh connection to the main worker
    :type conn:                     ssh.SshConnection
    :param project_codename:        The uuid of the project
    :type project_codename:         str
    """
    calc_dir = util.path_join(api_util.WORKER_WORK_PATH, "ZephyTOOLS", "PROJECTS_CFD", project_codename, "CALC")
    if not conn.folder_exists(calc_dir):
        log.debug("calc folder " + calc_dir + " doesn't exists yet, skipping...")
        return True
    _, out, _ = conn.run(["find", calc_dir, "-mindepth", "1", "-maxdepth", "1", "-type", "d"])
    out = out.strip()
    if not out or "\n" in out:  # No results or more than one result
        log.warning("Unable to get the calculation output folder")
        return
    calc_dir = out.rstrip("/")
    stopper_command = util.path_join(api_util.WORKER_WORK_PATH, "ZephyTOOLS", "APPLI", "TMP", "CFD_CALC_STOP.py")
    conn.run(["python", stopper_command, calc_dir])


def recalculate(api_name, server_name, job, project, calculation, calc_param_file, provider_name, machine, nbr_machines,
                nbr_iterations, split_results, client_login, client_ip, api_version):
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
    :param calculation:             The calculation to launch
    :type calculation:              dict[str, any]
    :param calc_param_file:         The main job parameter file
    :type calc_param_file:          str
    :param provider_name:           The name of the provider
    :type provider_name:            str
    :param machine:                 The type of machine to launch
    :type machine:                  str
    :param nbr_machines:            The number of machines to run
    :type nbr_machines:             int
    :param nbr_iterations:          The number of iteration the new calculation should run
    :type nbr_iterations:           int
    :param split_results:           Do you want to split results ?
    :type split_results:            bool
    :param client_login:            The login of the job owner
    :type client_login:             str
    :param client_ip:               The client ip address of the http request string this job
    :type client_ip:                str
    :param api_version:             The version of the http api where the user ask to launch this job
    :type api_version:              str
    """
    job_id = int(job['id'])
    nbr_machines = int(nbr_machines)
    models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_RUNNING)
    project_codename = project['uid']
    user_id = project["user_id"]
    calc_id = calculation['id']
    tmp_folder = api_util.get_conf().get("general", "tmp_folder")
    provider = api_util.get_provider(provider_name)
    storage = api_util.get_storage(project['storage'])
    tags = {
        'operation': "calc",
        'job_id': str(job_id),
        'server': server_name,
        'api': api_name,
        'api_version': api_version,
        'client': client_login,
        'client_ip': client_ip,
        'debug': DO_NOT_KILL_INSTANCES,
        'trusted': IS_TOOLCHAIN_SECURED
    }

    models.users.charge_user_fix_price(user_id, job_id, "Calculation storage cost")
    result_name = project_codename + "-calc-" + str(job_id)
    result_file = cmd_util.ResultFile(project_codename, result_name + ".zip")
    internal_file = cmd_util.ResultFile(project_codename, result_name + "_workfiles.zip")
    if split_results:
        iterations_file = cmd_util.ResultFile(project_codename, result_name + "_iterations.zip")
        reduce_file = cmd_util.ResultFile(project_codename, result_name + "_reduce.zip")

    try:
        # Creating worker
        with cmd_util.using_workers(api_name, provider, job_id, machine, nbr_machines, tags,
                                    debug_keep_instances_alive=DO_NOT_KILL_INSTANCES) as workers:
            # Launch main script
            with cmd_util.TaskProcess(job_id, project_codename, "restart_calc", workers,
                                      [nbr_iterations, split_results]) as task_proc:
                conn = workers.ssh_connection
                # Charge user
                end_time = models.users.charge_user_computing(user_id, job_id, "Cloud computation cost")
                if models.users.get_credit(user_id) <= 0:
                    raise api_util.NoMoreCredits()

                log.info("Sending project files on worker")
                worker_in_storage = storages.SshStorage(conn, api_util.WORKER_INPUT_PATH, IS_TOOLCHAIN_SECURED)

                cmd_util.copy_project_file(user_id, project_codename, storage, worker_in_storage, "internal.zip",
                                           tmp_folder, file_id=calculation['internal_file_id'])
                worker_in_storage.upload_file(calc_param_file, "calc_params.zip")
                os.remove(calc_param_file)
                log.info("Project files sent to the worker")

                # Tell the script to start
                log.info("Starting the computation")
                task_proc.start()
                last_fetched_progress_time = datetime.datetime.utcfromtimestamp(0)
                is_stopped = False
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
                    if (datetime.datetime.utcnow() - last_fetched_progress_time).seconds > STATUS_FETCHING_DELAY:
                        fetch_progress(conn, user_id, project_codename, calculation['name'], calculation['id'], storage,
                                       tmp_folder)
                        last_fetched_progress_time = datetime.datetime.utcnow()

                    if not is_stopped:
                        calculation = models.calc.get_calc(user_id, project['uid'], calculation['id'])
                        if not calculation:
                            raise api_util.ToolchainError("Calculation " + str(calc_id) + " disappeared")
                        if calculation['status'] == models.calc.STATUS_STOPPED:
                            log.info("Stopping computation")
                            stop_calc(conn, project_codename)
                            is_stopped = True
                    time.sleep(1)

                # Checking if the machine is still here
                if not conn.ping():
                    models.jobs.save_job_text(job_id, "Worker instance disappeared")
                    raise api_util.ToolchainError("Worker instance disappeared")

                # Fetching computed data
                log.info("Saving results")
                worker_out_storage = storages.SshStorage(conn, api_util.WORKER_OUTPUT_PATH, IS_TOOLCHAIN_SECURED)
                log_file = util.path_join(api_util.WORKER_OUTPUT_PATH, "worker.log")
                if conn.file_exists(log_file):
                    with file_util.temp_filename(dir=tmp_folder) as tmp:
                        conn.get_file(log_file, tmp)
                        models.jobs.save_job_log(job_id, tmp)
                else:
                    log.warning("No worker log file")

                if not result_file.exists(worker_out_storage):
                    log.error("Unable to find file " + str(result_file) + " on worker")
                    raise api_util.ToolchainError("Task failed, no result file")
                result_file.save_on_storage(worker_out_storage, storage, tmp_folder)

                if split_results:
                    if not iterations_file.exists(worker_out_storage):
                        log.error("Unable to find file " + str(iterations_file) + " on worker")
                        raise api_util.ToolchainError("Task failed, no result file")
                    iterations_file.save_on_storage(worker_out_storage, storage, tmp_folder)

                    if not reduce_file.exists(worker_out_storage):
                        log.error("Unable to find file " + str(reduce_file) + " on worker")
                        raise api_util.ToolchainError("Task failed, no result file")
                    reduce_file.save_on_storage(worker_out_storage, storage, tmp_folder)

                if internal_file.exists(worker_out_storage):
                    internal_file.save_on_storage(worker_out_storage, storage, tmp_folder)
                else:
                    log.warning("No internal files found on server")

                fetch_progress(conn, user_id, project_codename, calculation['name'], calculation['id'], storage,
                               tmp_folder)
                log.info("Computation result fetched")

                # Signaling all output was fetched
                task_proc.stop_and_wait()

        # Charge again if required
        if datetime.datetime.utcnow() > end_time:
            models.users.charge_user_computing(project["user_id"], job_id, "Cloud computation cost")

        # Uploading file on cloud storage
        result_file.save_in_database(user_id)
        internal_file_id = internal_file.save_in_database(user_id) if internal_file.saved else None
        if split_results:
            iterations_file.save_in_database(user_id)
            reduce_file.save_in_database(user_id)
            models.calc.save_result_files(user_id, project_codename, calculation['name'], result_file.file_id,
                                          iterations_file.file_id, reduce_file.file_id, internal_file_id)
        else:
            models.calc.save_result_files(user_id, project_codename, calculation['name'], result_file.file_id,
                                          None, None, internal_file_id)
    except error_util.all_errors:
        with error_util.before_raising():
            if REMOVE_RESULTS_ON_ERROR:
                internal_file.delete_from_distant(storage)
                result_file.delete_from_distant(storage)
                if split_results:
                    iterations_file.delete_from_distant(storage)
                    reduce_file.delete_from_distant(storage)
    log.info("Results saved")
