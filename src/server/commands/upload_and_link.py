# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python libs
import logging
import os

# Project Specific libs
from lib import error_util
import models.jobs
import models.projects
import models.users
import models.provider_config
from core import api_util
from core import cmd_util

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMMAND_NAME = "upload_and_link"


log = logging.getLogger("aziugo")


def run(api_name, server_name, job_id, project_file, anal_file, storage, client_login, client_ip, api_version):
    """
    Upload project file, analyse them and save analysis

    :param api_name:                The name of the api
    :type api_name:                 str
    :param server_name:             The name of the server (ex: apidev.zephycloud.com)
    :type server_name:              str
    :param job_id:                  the id of the job to run
    :type job_id:                   int
    :param project_file:            The raw project file to save
    :type project_file:             str
    :param anal_file:               The analysed project file
    :type anal_file:                str
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
            raise api_util.ToolchainError("Unknown project " + str(job['project_uid']))

        try:
            models.projects.set_project_status(project["user_id"], job["project_uid"],
                                               models.projects.PROJECT_STATUS_ANALYSING)

            link(job, project, project_file, anal_file)
            models.projects.set_project_status(project["user_id"], job["project_uid"],
                                               models.projects.PROJECT_STATUS_ANALYSED)
        except error_util.all_errors:
            with error_util.before_raising():
                models.projects.set_project_status(project["user_id"], job["project_uid"],
                                                   models.projects.PROJECT_STATUS_RAW)
    finally:
        if os.path.exists(project_file):
            os.remove(project_file)
        if os.path.exists(anal_file):
            os.remove(anal_file)


def link(job, project, project_file, anal_file):
    """
    Upload files in the cloud

    :param job:                     The job information
    :type job:                      dict[str, any]
    :param project:                 The main project
    :type project:                  dict[str, any]
    :param project_file:            The raw project file to analyse
    :type project_file:             str
    :param anal_file:               The analysed project file
    :type anal_file:                str
    """
    job_id = int(job['id'])
    user_id = project["user_id"]

    # Uploading file on cloud storage
    log.info("Uploading project files to storage")
    models.projects.append_file_to_project(user_id, job["project_uid"], project_file,
                                           "project_" + job["project_uid"] + ".zip",
                                           key=models.projects.PROJECT_FILE_RAW)
    os.remove(project_file)
    anal_filename = job["project_uid"] + "-anal-" + str(job_id) + ".zip"
    models.projects.append_file_to_project(user_id, job["project_uid"], anal_file, anal_filename,
                                           key=models.projects.PROJECT_FILE_ANALYSED)
    os.remove(anal_file)
    models.users.charge_user_fix_price(user_id, job_id, "Project storage cost")
    log.info("Project file uploaded")
