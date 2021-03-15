# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import json
import logging
import contextlib
import datetime
import os
import uuid
import copy
import subprocess

# Third party libs
from flask import g, url_for

# Project specific libs
from lib import util
from lib import error_util
from lib import proc_util
from lib import type_util
from lib import file_util
from lib import ssh
from lib import async_util
import api_util
import core.cluster
import models.jobs
import models.provider_config
import models.projects


API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
log = logging.getLogger("aziugo")


class TaskProcess(object):
    def __init__(self, job_id, project_codename, command, running_workers, params=None):
        self._job_id = int(job_id)
        self._project_uid = project_codename
        self._command = str(command)
        self._running_worker = running_workers
        self._proc = None
        self._status = models.jobs.JOB_STATUS_LAUNCHING
        self._creation_time = datetime.datetime.utcnow()
        self._params = params if params else []
        conf = api_util.get_conf()
        self._api_name = conf.get("general", "api_name")
        self._server_name = conf.get("general", "server")

    @property
    def status(self):
        return self._status

    @property
    def exit_code(self):
        return self._proc.poll()

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def conn(self):
        return self._running_worker.ssh_connection

    def start(self):
        self.conn.run(["rm", "-f", util.path_join(api_util.WORKER_OUTPUT_PATH, "task_end.txt")])
        self.conn.run("echo '1' > '" + util.path_join(api_util.WORKER_INPUT_PATH, "start_task")+"'", shell=True)
        self._status = models.jobs.JOB_STATUS_RUNNING

    def stop_and_wait(self):
        self.conn.run("echo '1' > '" + util.path_join(api_util.WORKER_INPUT_PATH, "output_fetched")+"'", shell=True)
        try:
            proc_util.wait_for_proc_and_streams(self._proc, 2)
        except util.TimeoutError:
            pass  # Machine stopped
        self._proc = None

    def check_status(self):
        if not self._running_worker.is_debug:
            if models.jobs.is_shutdown_disabled(self._job_id):
                self._running_worker.disable_shutdown()
        if self.is_canceled():
            self._status = models.jobs.JOB_STATUS_CANCELED
            raise api_util.ToolchainCanceled()

        status_file = util.path_join(api_util.WORKER_OUTPUT_PATH, "task_end.txt")
        code, out, err = self.conn.run(["cat", status_file], can_fail=True)
        if code == 0:
            task_status = out.strip()
            if task_status == "success":
                self._status = models.jobs.JOB_STATUS_FINISHED
            elif task_status == "cancel":
                self._status = models.jobs.JOB_STATUS_CANCELED
            elif task_status == "error":
                self._status = models.jobs.JOB_STATUS_KILLED
            else:
                raise RuntimeError("Unknown worker task result: " + repr(task_status))
            return self._status

        # Ensure the proc is still running
        if not self._proc.is_running():
            self._status = models.jobs.JOB_STATUS_KILLED

        # Load progress
        exit_code, out, _ = self.conn.run(["cat", api_util.WORKER_WORK_PATH + "/progress.txt"], can_fail=True)
        if exit_code == 0 and type_util.ll_float(out.strip()):
            models.jobs.set_job_progress(self._job_id, max(0.0, min(1.0, float(out))))
        return self._status

    def is_canceled(self):
        job = models.jobs.get_job(self._job_id)
        return not job or job['status'] not in (models.jobs.JOB_STATUS_RUNNING, models.jobs.JOB_STATUS_LAUNCHING)

    def __enter__(self):
        proc = None
        try:
            log_info_file = util.path_join(api_util.WORKER_INPUT_PATH, "log_info.json")
            log_info = {
                "jobid": self._job_id,
                "job_type": self._command,
                "api_name": self._api_name,
                "server_name": self._server_name,
                "instance": self._running_worker.worker_ids[0],
                "provider": self._running_worker.provider_name
            }
            with file_util.temp_file(json.dumps(log_info)) as tmp_filepath:
                self.conn.send_file(tmp_filepath, api_util.WORKER_INPUT_PATH + "/log_info.json")
            self.conn.run(["chmod", "a+r", log_info_file])
            proc = self.conn.run_async(["python", api_util.WORKER_RUNNER_PATH])

            # Send the task parameter to the worker
            task_params_file = os.path.join(api_util.WORKER_INPUT_PATH, "task_params.json")
            task_params = {
                "jobid": self._job_id,
                "project_uid": self._project_uid,
                "toolchain": self._command,
                "params": json.dumps(self._params),
                "shutdown": "0" if self._running_worker.is_debug else "1"
            }
            with file_util.temp_file(json.dumps(task_params)) as tmp_filepath:
                self.conn.send_file(tmp_filepath, task_params_file)
            self.conn.run(["chmod", "a+r", task_params_file])
            self._proc = proc
        except error_util.abort_errors:
            with error_util.before_raising():
                log.info("Signal received, stopping process")
                if proc:
                    proc_util.ensure_stop_proc(proc, 2)
        except error_util.all_errors:
            with error_util.before_raising():
                try:
                    if proc:
                        proc_util.ensure_kill_proc(proc)
                except error_util.abort_errors:
                    pass
                except error_util.all_errors as e:
                    logging.getLogger("aziugo").exception(e)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._proc:
            proc_util.ensure_kill_proc(self._proc)
        return False


def config_cmd_log(command_name, job_id):
    """
    Reconfigure the logger to get more explicit log messages

    :param command_name:    The name of the current command. ex: upload_and_analyse
    :type command_name:     str
    :param job_id:          The id of the job
    :type job_id:           int
    """
    log.name = command_name
    try:
        job_id = int(job_id)
    except ValueError:
        raise api_util.ToolchainError("Invalid job id:" + repr(job_id)+", cancelling "+__name__)
    log.name = "Job" + str(job_id).rjust(6) + ":" + command_name


class RunningWorkers(object):
    def __init__(self, provider, workers, conn, debug=False):
        """
        :param provider:        The provider
        :type provider:         provider.Provider
        :param workers:         The created workers
        :type workers:          list[worker.Worker]
        :param conn:            The ssh connection to the main worker
        :type conn:             lib.ssh.SshConnection
        :param debug:           Should we forget to shutdown the workers at the end. Optional, default False
        :type debug:            bool
        """
        super(RunningWorkers, self).__init__()
        self._conn = conn
        self._debug = debug
        self._provider = provider
        self._workers = workers

    @property
    def ssh_connection(self):
        return self._conn

    @property
    def is_debug(self):
        return self._debug

    @property
    def provider_name(self):
        return self._provider.name

    @property
    def worker_ids(self):
        return [w.worker_id for w in self._workers]

    def disable_shutdown(self):
        self._debug = True
        self._provider.tag_workers(self._workers, {'debug': True})
        flag_file = util.path_join(api_util.WORKER_INPUT_PATH, "disable_shutdown")
        self._conn.run("echo '1' > '" + flag_file + "'", shell=True)

    def say_hello(self):
        """ Tell the worker(s) we are still listening to him/them """


class KeepAliveWorkerThread(async_util.RecurringThread):
    """ Ping a specific file on the worker, allowing the worker to notice it is still monitored """
    def __init__(self, ssh_conn, *args, **kwargs):
        """
        :param ssh_conn:        An ssh connection to the worker
        :type ssh_conn:         lib.ssh.SshConnection
        """
        super(KeepAliveWorkerThread, self).__init__(*args, **kwargs)
        self._conn = ssh_conn

    @property
    def delay(self):
        return datetime.timedelta(seconds=60)

    def work(self, *args, **kwargs):
        if self.should_stop():
            return
        self._conn.run(["touch", api_util.WORKER_INPUT_PATH.rstrip("/")+"/worker_ping"])


class KeepAliveClusterThread(async_util.RecurringThread):
    """ Ping a specific file on each worker of a cluster, allowing them to notice they are still monitored """
    def __init__(self, cluster, *args, **kwargs):
        """
        :param cluster:         The cluster we want to monitor
        :type cluster:          core.cluster.Cluster
        """
        super(KeepAliveClusterThread, self).__init__(*args, **kwargs)
        self._cluster = cluster

    @property
    def delay(self):
        return datetime.timedelta(seconds=60)

    def work(self, *args, **kwargs):
        if self.should_stop():
            return
        connections = self._cluster.get_connections()
        for conn in connections:
            if self.should_stop():
                return
            conn.run(["touch", api_util.WORKER_INPUT_PATH.rstrip("/")+"/worker_ping"])


@contextlib.contextmanager
def using_workers(api_name, provider, job_id, machine, nbr_machines, tags, debug_keep_instances_alive=False):
    machine_cost = models.provider_config.get_machine_provider_cost(provider.name, machine)
    if not machine_cost:
        raise RuntimeError("Unable to get the cost for provider " + str(provider.name))
    instance_price = api_util.price_to_float(machine_cost["cost_per_sec"]) * 3600  # In $/h, for aws spots
    nbr_machines = int(nbr_machines)
    alive_thread = None
    if nbr_machines == 1:
        workers = []
        try:
            log.info("Launching worker on provider " + str(provider.name))
            workers = provider.create_workers(int(nbr_machines), machine=machine, spot_price=instance_price)
            log.info("worker created")
            main_worker = workers[0]
            if main_worker.specific_cost:
                models.jobs.set_job_specific_cost(job_id, provider.name, machine, main_worker.specific_cost,
                                                  machine_cost["currency"], machine_cost["sec_granularity"],
                                                  machine_cost["min_sec_granularity"])

            # Tag instance
            provider.tag_workers(workers, {'Name': api_name + "_worker/job_" + str(job_id), "type": "worker"})
            if not debug_keep_instances_alive:
                debug_keep_instances_alive = models.jobs.is_shutdown_disabled(job_id)
            tags = copy.copy(tags)
            tags['debug'] = "true" if debug_keep_instances_alive else "false"
            provider.tag_workers(workers, tags)

            # Connect to the worker
            ip = main_worker.public_ip if main_worker.public_ip else main_worker.private_ip
            log.info("Waiting for worker ssh connection to " + str(ip) + " ...")
            conn = ssh.SshConnection(ip, "aziugo", provider.get_key_path())
            conn.wait_for_connection()
            log.info("Connection with worker established")
            alive_thread = KeepAliveWorkerThread(conn)
            alive_thread.start()

            yield RunningWorkers(provider, workers, conn, debug_keep_instances_alive)
        finally:
            if alive_thread:
                alive_thread.stop()
                alive_thread.join()

            if workers and provider:
                if not debug_keep_instances_alive:
                    try:
                        debug_keep_instances_alive = models.jobs.is_shutdown_disabled(job_id)
                    except error_util.all_errors as e:
                        log.warning(str(e))
                if debug_keep_instances_alive:
                    log.debug("Worker cleaning is disabled for debug purpose")
                else:
                    log.info("Stopping workers...")
                    cleanup_failed = False
                    try:
                        provider.terminate_workers(workers)
                    except error_util.abort_errors:
                        with error_util.before_raising():
                            try:
                                provider.terminate_workers(workers)
                                log.info("Workers stopped")
                            except error_util.abort_errors:
                                log.warning("Worker cleaned aborted.")
                                msg = "Workers of job "+str(job_id)+" are not killed. Please kill them manually"
                                log.error(msg)
                                api_util.send_admin_email("Worker cleaned aborted.", msg)
                    except error_util.all_errors as e:
                        cleanup_failed = True
                        msg = "Workers of job " + str(job_id) + " are not killed. Please kill them manually"
                        log.error(msg)
                        error_util.log_error(log, e)
                        api_util.send_admin_email("Worker cleaned aborted.", msg)
                    if not cleanup_failed:
                        log.info("Workers stopped")

    else:
        machine_info = models.provider_config.get_machine(provider.name, machine)
        if not machine_info:
            raise RuntimeError("Unable to get the description of machine " + str(machine))
        nbr_cores = int(machine_info['nbr_cores'])
        cluster_tags = copy.copy(tags)
        if not debug_keep_instances_alive:
            debug_keep_instances_alive = models.jobs.is_shutdown_disabled(job_id)
        cluster_tags.update({
            "debug": "true" if debug_keep_instances_alive else "false",
            '%master%_Name': api_name + "_worker/job_" + str(job_id),
            '%master%_type': "cluster master",
            '%slave%_Name': api_name + "_worker/job_" + str(job_id) + " slave %slave_index%",
            '%slave%_type': "cluster slave",
        })
        log.info("Launching worker on provider " + str(provider.name))
        with core.cluster.Cluster(provider, "aziugo", nbr_cores, str(job_id), machine=machine,
                                  spot_price=instance_price, tags=cluster_tags,
                                  debug_no_terminate=debug_keep_instances_alive) as cluster:
            try:
                log.info("Main worker launched, with id " + str(cluster.master_id))

                log.info("Launching " + str(nbr_machines - 1) + " slave workers...")
                cluster.add_slaves(nbr_machines - 1)
                log.info("Slave workers launched")

                # Connect to the worker
                log.info("Waiting for worker ssh connection to "+str(cluster.ip)+" ...")
                conn = ssh.SshConnection(cluster.ip, "aziugo", provider.get_key_path())
                conn.wait_for_connection()
                log.info("Connection with worker established")
                alive_thread = KeepAliveClusterThread(cluster)
                alive_thread.start()
                yield RunningWorkers(provider, cluster.workers, conn, debug_keep_instances_alive)
            finally:
                if alive_thread:
                    alive_thread.stop()
                    alive_thread.join()

                if not debug_keep_instances_alive:
                    try:
                        debug_keep_instances_alive = models.jobs.is_shutdown_disabled(job_id)
                    except error_util.all_errors as e:
                        log.warning(str(e))
                    if debug_keep_instances_alive:
                        cluster.disable_clean()
                if not debug_keep_instances_alive:
                    log.info("Stopping workers...")
        if not debug_keep_instances_alive:
            log.info("Workers stopped")


def get_file_url(user_id, project_uid, storage_name, file_key=None, file_id=None):
    if storage_name not in g.storages.keys():
        log.error("Project storage " + repr(storage_name) + " is not part of known storages")
        raise RuntimeError("Storage issue")
    if file_key:
        file_info = models.projects.get_file_by_key(user_id, project_uid, file_key)
    elif file_id:
        file_info = models.projects.get_file_by_id(user_id, project_uid, file_id)
    else:
        raise RuntimeError("You should define a file key or a file id")
    if not file_info:
        log.error("Not analysed data in project file list")
        raise RuntimeError("Storage issue")
    filename = file_info['filename']
    storage = g.storages[storage_name]
    if storage.type == "local_filesystem":
        return url_for('public.local_file', storage_name=storage_name, subpath=filename,
                       _external=True, _scheme='https')
    else:
        return storage.get_file_url(filename)


def copy_project_file(user_id, project_codename, src_storage, dest_storage, dest_name, tmp_folder, filename=None,
                      key=None, file_id=None):
    if filename:
        saved_file = filename
    elif key:
        saved_file = models.projects.get_file_by_key(user_id, project_codename, key=key)
        if not saved_file:
            raise RuntimeError("File is not found in this project")
        saved_file = saved_file['filename']
    elif file_id:
        saved_file = models.projects.get_file_by_id(user_id, project_codename, file_id)
        if not saved_file:
            raise RuntimeError("File is not found in this project")
        saved_file = saved_file['filename']
    else:
        raise RuntimeError("Neither filename, key nor file_id is defined")
    dest_storage.copy_from_storage(src_storage, saved_file, dest_name, tmp_folder)


class ResultFile(object):
    def __init__(self, project_codename, worker_filename):
        self._saved = False
        self._project_codename = project_codename
        self._worker_filename = worker_filename
        _, file_extension = os.path.splitext(self._worker_filename)
        if not file_extension:
            file_extension = ""
        else:
            file_extension = "." + file_extension.lstrip(".")
        self._dest_filename = project_codename+"-"+str(uuid.uuid4())+file_extension
        self._file_size = -1
        self._file_id = None

    def exists(self, worker_out_storage):
        """
        Check if file exists on worker

        :param worker_out_storage:      The worker internal storage
        :type worker_out_storage:       core.storage.SshStorage
        :return:                        True if the file exists on worker, false otherwise
        :rtype:                         bool
        """
        return worker_out_storage.file_exists(self._worker_filename)

    def save_on_storage(self, worker_out_storage, dest_storage, tmp_folder):
        """
        Save file on an external storage

        :param worker_out_storage:      The worker internal storage
        :type worker_out_storage:       core.storage.SshStorage
        :param dest_storage:            The external destination storage
        :type dest_storage:             core.storage.Storage
        :param tmp_folder:              A temporary folder, required if local swapping is needed
        :type tmp_folder:               tmp
        """
        self._file_size = worker_out_storage.get_file_size(self._worker_filename)
        worker_out_storage.copy_to_storage(dest_storage, self._worker_filename, self._dest_filename, tmp_folder)
        self._saved = True

    def save_in_database(self, user_id, key=None):
        if not self.saved:
            raise RuntimeError("The file is not saved on distant storage")
        if key:
            old_file = models.projects.get_file_by_key(user_id, self._project_codename, key)
            if old_file is not None:
                models.projects.remove_file_from_project(user_id, self._project_codename, old_file['id'])
            result = models.projects.save_project_file(user_id, self._project_codename, self._dest_filename,
                                                       file_size=self._file_size, key=key)
        else:
            result = models.projects.save_project_file(user_id, self._project_codename, self._dest_filename,
                                                       file_size=self._file_size)
        self._file_id = int(result['id'])
        return self._file_id

    @property
    def saved(self):
        return self._saved

    @property
    def file_id(self):
        if self._file_id is None:
            raise RuntimeError("File is not saved in database")
        return self._file_id

    def delete_from_distant(self, storage):
        if not self._saved:
            return
        storage.delete_file(self._dest_filename)

    def __str__(self):
        return self._worker_filename
