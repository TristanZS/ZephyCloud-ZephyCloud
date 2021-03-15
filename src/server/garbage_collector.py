#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import sys
import logging
import logging.handlers
import os
import argparse
import datetime
import time
import json
import signal
import copy
import shutil
import threading

# Third party libs
import colorlog

# Project specific libs
from lib import util
from lib import error_util
from lib import type_util
from lib import async_util
from lib import debug_util
import models.meshes
import models.projects
import models.calc
import models.jobs
from core import api_util
import core.provider
import core.storages
from core.worker_observer import WorkerObserver
from core.worker import Worker
from core.lifetime_rules import Sentence, Penalty, Motive, LifetimeRules


log = logging.getLogger("aziugo")
API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKER_PROCESS_LAUNCHER = "aziugo_start.py"
GC_DEBUG_MODE = True
GC_DEBUG_EMAIL = "sysadmin@aziugo.com"
IGNORE_SIGNAL_DELAY = datetime.timedelta(milliseconds=500)


def gc_debug(message):
    log.debug("GC DEBUG: "+message)
    core.api_util.send_admin_email("Gc debug", message, GC_DEBUG_EMAIL)


class RunningJobs(object):
    """ Manage collector shared list of jobs """
    def __init__(self):
        super(RunningJobs, self).__init__()
        self._job_list = []
        self._update_date = datetime.datetime.utcfromtimestamp(0)

    def set_list(self, job_list, date):
        if date <= self._update_date:
            return
        self._update_date = date
        self._job_list = job_list

    def get_list(self):
        return copy.deepcopy(self._job_list)

    def get_update_date(self):
        return self._update_date


class RunningWorkers(object):
    """ Manage collector shared list of workers """
    def __init__(self):
        super(RunningWorkers, self).__init__()
        self._worker_list = []
        self._update_date = datetime.datetime.utcfromtimestamp(0)

    def set_list(self, worker_list, date):
        if date <= self._update_date:
            return
        self._update_date = date
        self._worker_list = worker_list

    def get_list(self):
        return copy.deepcopy(self._worker_list)

    def get_update_date(self):
        return self._update_date



class ClusterList(object):
    def __init__(self):
        super(ClusterList, self).__init__()
        self._cluster_by_master = {}
        self._cluster_by_job_id = {}        # :type: dict[int, list[core.worker_observer.WorkerObserver]]

    def append_master(self, observer):
        """
        Save a cluster master observer to this list

        :param observer:    an observer to append to this list
        :type observer:     core.worker_observer.WorkerObserver
        """
        if not observer.jobid:
            return
        if observer.jobid not in self._cluster_by_job_id.keys():
            self._cluster_by_job_id[observer.jobid] = []
        worker_list = self._cluster_by_job_id[observer.jobid]
        worker_list.append(observer)
        self._cluster_by_job_id[observer.jobid] = worker_list
        self._cluster_by_master[observer.worker_id] = worker_list

    def append_slave(self, observer):
        """
        Save a cluster slave observer to this list

        :param observer:    an observer to append to this list
        :type observer:     core.worker_observer.WorkerObserver
        """
        if not observer.jobid:
            return
        if observer.jobid not in self._cluster_by_job_id.keys():
            self._cluster_by_job_id[observer.jobid] = []
        worker_list = self._cluster_by_job_id[observer.jobid]
        worker_list.append(observer)
        self._cluster_by_job_id[observer.jobid] = worker_list

    def has_master(self, observer):
        """
        Check if a cluster slave has a running cluster master  running

        :param observer:        The slave worker observer
        :type observer:         core.worker_observer.WorkerObserver
        :return:                True if we have found the corresponding master in running state
        :rtype:                 bool
        """
        if not observer.jobid or observer.jobid not in self._cluster_by_job_id.keys():
            raise RuntimeError("Corrupted cluster list, can't check master of instance "+str(observer))
        cluster = self._cluster_by_job_id[observer.jobid]
        for coworker in cluster:
            if coworker.worker_id == observer.worker_id or coworker.is_cluster_slave():
                pass
            return coworker.status not in (Worker.Status.SHUTTING_DOWN, Worker.Status.TERMINATED)
        return False

    def has_slaves(self, observer):
        """
        Check if a cluster slave has a running cluster master  running

        :param observer:        The slave worker observer
        :type observer:         core.worker_observer.WorkerObserver
        :return:                True if we have found the corresponding master in running state
        :rtype:                 bool
        """
        if not observer.jobid or observer.jobid not in self._cluster_by_job_id.keys():
            raise RuntimeError("Corrupted cluster list, can't check master of instance "+str(observer))
        cluster = self._cluster_by_job_id[observer.jobid]
        for coworker in cluster:
            if coworker.worker_id == observer.worker_id or coworker.is_cluster_master():
                pass
            return coworker.status not in (Worker.Status.SHUTTING_DOWN, Worker.Status.TERMINATED)
        return False


def judge_worker(observer, lifetime_rules, cluster_list, now=None):
    """
    Judge what to do with the instance

    :param observer:        The information about a worker
    :type observer:         core.worker_observer.WorkerObserver
    :param lifetime_rules:  The rules used to judge the worker
    :type lifetime_rules:   lib.lifetime_rules.LifetimeRules
    :param cluster_list:    The list of running cluster workers
    :type cluster_list:     ClusterList
    :param now:             The instant we could use to check
    :type now:              datetime.datetime|None
    :return:                The sentence for current instance, or None
    :rtype:                 Sentence|None
    """

    if now is None:
        now = datetime.datetime.utcnow()

    # The instance is stopped, so we check if it's stuck terminating, but no further checks
    rules = lifetime_rules.get_rules(Penalty.PROBATION)
    if observer.status in (Worker.Status.SHUTTING_DOWN, Worker.Status.TERMINATED):
        if (rules[Motive.STUCK_STOPPING] and
                observer.killing_date is not None and
                now - observer.killing_date > rules[Motive.STUCK_STOPPING]):
            sentence = Sentence(Penalty.PROBATION, Motive.STUCK_STOPPING, observer.killing_date)
            if not observer.has_probation(sentence):
                observer.add_probation(sentence)
                return sentence
        return None

    if observer.has_immunity():
        return None

    # We start to check fatal limits
    rules = lifetime_rules.get_rules(Penalty.DEATH)
    if rules[Motive.TOO_LONG] and now - observer.creation_date > rules[Motive.TOO_LONG]:
        return Sentence(Penalty.DEATH, Motive.TOO_LONG, observer.creation_date)
    if not observer.is_cluster_slave():
        not_working_rule = rules[Motive.NOT_WORKING] if rules[Motive.NOT_WORKING] else None
        if not_working_rule:
            if observer.working_date is None:
                if observer.is_cluster_master():
                    not_working_rule += observer.get_startup_time()*2
                if now - observer.creation_date > not_working_rule:
                    return Sentence(Penalty.DEATH, Motive.NOT_WORKING, observer.working_date)
            else:
                if now - observer.working_date > not_working_rule + observer.get_shutdown_time()*2:
                    return Sentence(Penalty.DEATH, Motive.NOT_WORKING, observer.working_date)
    if rules[Motive.NO_JOBID] and observer.jobid is None and now - observer.creation_date > rules[Motive.NO_JOBID]:
        return Sentence(Penalty.DEATH, Motive.NO_JOBID, observer.creation_date)

    if observer.is_cluster_slave() and not cluster_list.has_master(observer):
        return Sentence(Penalty.DEATH, Motive.NO_MASTER, observer.creation_date)

    # Nothing fatal, so we check warnings
    rules = lifetime_rules.get_rules(Penalty.PROBATION)
    if rules[Motive.TOO_LONG] and now - observer.creation_date > rules[Motive.TOO_LONG]:
        sentence = Sentence(Penalty.PROBATION, Motive.TOO_LONG, observer.creation_date)
        if not observer.has_probation(sentence):
            observer.add_probation(sentence)
            return sentence
    if not observer.is_cluster_slave():
        not_working_rule = rules[Motive.NOT_WORKING] if rules[Motive.NOT_WORKING] else None
        if not_working_rule:
            if observer.working_date is None:
                if observer.is_cluster_master():
                    not_working_rule += observer.get_startup_time()*2
                if now - observer.creation_date > not_working_rule:
                    sentence = Sentence(Penalty.PROBATION, Motive.NOT_WORKING, observer.working_date)
                    if not observer.has_probation(sentence):
                        observer.add_probation(sentence)
                        return sentence
            else:
                if now - observer.working_date > not_working_rule + observer.get_shutdown_time()*2:
                    sentence = Sentence(Penalty.PROBATION, Motive.NOT_WORKING, observer.working_date)
                    if not observer.has_probation(sentence):
                        observer.add_probation(sentence)
                        return sentence
    if rules[Motive.NO_JOBID] and observer.jobid is None and now - observer.creation_date > rules[Motive.NO_JOBID]:
        sentence = Sentence(Penalty.PROBATION, Motive.NO_JOBID, observer.creation_date)
        if not observer.has_probation(sentence):
            observer.add_probation(sentence)
            return sentence
    return None


class WorkerCollector(async_util.RecurringThread):
    """
    Kills worker stuck for various reasons
    """
    EMAIL_MSG = "Strange behaviour for instance %s: %s\n%s\nWorker description:\n%s\n"

    def __init__(self, provider, api_name, server_name, running_jobs, running_workers, *args, **kwargs):
        """
        :param provider:            The provider to clean
        :type provider:             core.providers.Provider
        :param api_name:            The name of the API
        :type api_name:             str
        :param server_name:         The name of the server
        :type server_name:          str
        :param running_jobs:        The list of active job manager
        :type running_jobs:         RunningJobs
        :param running_workers:     The list of active worker manager
        :type running_workers:      RunningWorkers

        """
        super(WorkerCollector, self).__init__(*args, **kwargs)
        self._provider = provider
        self._api_name = api_name
        self._server_name = server_name
        self._rules = LifetimeRules(os.path.join(API_PATH, 'config.conf'))
        self._observers = {}        # :type: dict[str, core.worker_observer.WorkerObserver]
        self._running_jobs = running_jobs
        self._running_workers = running_workers
        if GC_DEBUG_MODE:
            self._dirty_kill_workers = set([])
            self._dirty_warning_workers = set([])

    @property
    def delay(self):
        return datetime.timedelta(seconds=120)

    def work(self, *args, **kwargs):
        try:
            now = datetime.datetime.utcnow()

            # fetching data about running workers
            thread_list = []
            workers = async_util.run_proc(WorkerCollector._list_workers, self._provider.name)
            self._running_workers.set_list(workers, now)
            for worker in workers:
                if self.should_stop():
                    return
                if worker.worker_id not in self._observers.keys():
                    self._observers[worker.worker_id] = WorkerObserver(worker, self._provider, self._api_name,
                                                                       self._server_name, WORKER_PROCESS_LAUNCHER)
                thread = threading.Thread(target=WorkerCollector._update_worker,
                                          args=(self._observers[worker.worker_id], worker))
                thread.start()
                thread_list.append(thread)

            for thread in thread_list:
                if self.should_stop():
                    return
                thread.join()

            # Listing active jobs, and grouping cluster
            job_list = []
            cluster_list = ClusterList()
            for worker in workers:
                if self.should_stop():
                    return
                observer = self._observers[worker.worker_id]
                if observer.jobid and observer.status not in (Worker.Status.SHUTTING_DOWN, Worker.Status.TERMINATED):
                    job_list.append(observer.jobid)
                    if observer.is_cluster_master():
                        cluster_list.append_master(observer)
                    elif observer.is_cluster_slave():
                        cluster_list.append_slave(observer)
            self._running_jobs.set_list(job_list, now)

            for worker in workers:
                if self.should_stop():
                    return
                observer = self._observers[worker.worker_id]
                sentence = judge_worker(observer, self._rules, cluster_list, now)
                if sentence is None:
                    continue
                if sentence.penalty == Penalty.DEATH:
                    msg = WorkerCollector.EMAIL_MSG % (observer, sentence.description, "KILLING INSTANCE !!!",
                                                       observer.description)
                    if GC_DEBUG_MODE:
                        if worker.worker_id in self._dirty_kill_workers:
                            continue
                        self._dirty_kill_workers.add(worker.worker_id)
                        gc_debug(msg)
                    else:
                        log.warning("killing instance %s: %s" % (observer, sentence.description))
                        core.api_util.send_admin_email("Watchdog KILL", msg)
                        async_util.run_proc(WorkerCollector._kill_worker, self._provider.name, worker)
                    observer.mark_as_killed()
                elif sentence.penalty == Penalty.PROBATION:
                    msg = WorkerCollector.EMAIL_MSG % (observer, sentence.description, "", observer.description)
                    if not GC_DEBUG_MODE:
                        if worker.worker_id in self._dirty_warning_workers:
                            continue
                        self._dirty_warning_workers.add(worker.worker_id)
                        gc_debug(msg)
                    else:
                        log.warning("Strange behaviour for instance %s: %s" % (observer, sentence.description))
                        core.api_util.send_admin_email("Watchdog warning", msg)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)

    @staticmethod
    def _update_worker(observer, worker):
        """
        Make the observer observe a worker

        :param observer:    The observer
        :type observer:     WorkerObserver
        :param worker:      The worker information
        :type worker:       Worker
        """
        observer.update(worker)

    @staticmethod
    def _list_workers(provider_name):
        """
        List the workers of given provider

        :param provider_name:    The name of the provider we observe
        :type provider_name:     str
        :return:                The list of workers
        :rtype:                 list[worker.Worker]
        """
        provider = api_util.get_provider(provider_name)
        return provider.list_workers()

    @staticmethod
    def _kill_worker(provider_name, worker):
        """
        List the workers of given provider

        :param provider_name:    The name of the provider we observe
        :type provider_name:     str
        """
        provider = api_util.get_provider(provider_name)
        provider.terminate_workers([worker])


class JobCollector(async_util.RecurringThread):
    """
    Cancel jobs if no worker is running for it since two hours
    """
    def __init__(self, running_jobs, *args, **kwargs):
        """
        :param running_jobs:    The list of active job manager
        :type running_jobs:     RunningJobs
        """
        super(JobCollector, self).__init__(*args, **kwargs)
        self._running_jobs = running_jobs
        self._date_by_job_id = {}
        self._last_date = datetime.datetime.utcfromtimestamp(0)
        if GC_DEBUG_MODE:
            self._deleted_jobs = set([])

    @property
    def delay(self):
        return datetime.timedelta(seconds=60)

    def work(self, *args, **kwargs):
        try:
            if self._running_jobs.get_update_date() <= datetime.datetime.utcfromtimestamp(0):
                return

            running_jobs = []
            if self._last_date < self._running_jobs.get_update_date():
                self._last_date = self._running_jobs.get_update_date()
                running_jobs = self._running_jobs.get_list()
                for job_id in running_jobs:
                    if self.should_stop():
                        return
                    self._date_by_job_id[int(job_id)] = self._last_date

            if GC_DEBUG_MODE:
                if datetime.datetime.utcnow() - self._last_date > datetime.timedelta(hours=1):
                    log.warning("GC: Should not happen:\n"+
                        "\tlast_date: "+str(self._last_date)+"\n"+
                        "\tnow: "+str(datetime.datetime.utcnow()) + "\n"+
                        "\trunning jobs update date: "+str(self._running_jobs.get_update_date()))
                    return

            unfinished_jobs = models.jobs.list_unfinished_jobs()
            unfinished_job_ids = set([int(job['id']) for job in unfinished_jobs])
            for job_id in unfinished_job_ids:
                if self.should_stop():
                    return
                if job_id not in self._date_by_job_id.keys():
                    self._date_by_job_id[job_id] = datetime.datetime.utcnow()

            for job_id in unfinished_job_ids:
                if self.should_stop():
                    return
                date = self._date_by_job_id[job_id]
                if datetime.datetime.utcnow() - date > datetime.timedelta(hours=2):
                    if GC_DEBUG_MODE:
                        if job_id in self._deleted_jobs:
                            continue
                        self._deleted_jobs.add(job_id)
                        gc_debug("GC: Cleaning job " + str(job_id) + " because no worker is working on it.\n"+
                                 "Details: \n  date:"+str(date)+"\nlast_date:"+str(self._last_date)+
                                 "\nrunning_jobs: "+repr(running_jobs)+"\nnow: "+str(datetime.datetime.utcnow()))
                    else:
                        log.warning("GC: Cleaning job " + str(job_id) + " because no worker is working on it")
                        models.jobs.cancel_job(job_id)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)


class ModelCollector(async_util.RecurringThread):
    """
    Update Calc and mesh status if a job have failed
    """
    def __init__(self, *args, **kwargs):
        super(ModelCollector, self).__init__(*args, **kwargs)
        if GC_DEBUG_MODE:
            self._dirty_projects = set([])
            self._dirty_meshes = set([])
            self._dirty_calcs = set([])

    @property
    def delay(self):
        return datetime.timedelta(seconds=300)

    def work(self, *args, **kwargs):
        try:
            # Clean projects
            dirty_projects = models.projects.list_failed_and_dirty()
            if self.should_stop():
                return
            for project in dirty_projects:
                if self.should_stop():
                    return
                if GC_DEBUG_MODE:
                    if project['uid'] in self._dirty_projects:
                        continue
                    self._dirty_projects.add(project['uid'])
                    gc_debug("GC: Setting project as not analyzed " + str(project['uid']) +
                             " because no analysis succeeded")
                else:
                    log.warning("GC: Setting project as not analyzed " + str(project['uid']) +
                                " because no analysis succeeded")
                    models.projects.set_project_status(project['user_id'], project['uid'],
                                                       models.projects.PROJECT_STATUS_RAW)

            # Clean meshes
            if self.should_stop():
                return
            dirty_meshes = models.meshes.list_failed_and_dirty()
            if self.should_stop():
                return
            for mesh in dirty_meshes:
                if self.should_stop():
                    return
                if GC_DEBUG_MODE:
                    if mesh['id'] in self._dirty_meshes:
                        continue
                    self._dirty_meshes.add(mesh['id'])
                    gc_debug("GC: Setting mesh as failed " + str(mesh['id']) + " because mesh job failed")
                else:
                    log.warning("GC: Setting mesh as failed " + str(mesh['id']) + " because mesh job failed")
                    models.meshes.set_mesh_status(mesh['user_id'], mesh['project_uid_id'], mesh['name'],
                                                  models.meshes.STATUS_KILLED)

            # Clean calculations
            if self.should_stop():
                return
            dirty_calculations = models.calc.list_failed_and_dirty()
            if self.should_stop():
                return
            for calc in dirty_calculations:
                if self.should_stop():
                    return
                if GC_DEBUG_MODE:
                    if calc['id'] in self._dirty_calcs:
                        continue
                    self._dirty_calcs.add(calc['id'])
                    gc_debug("GC: Setting calc as failed " + str(calc['id']) + " because calc job failed")
                else:
                    log.warning("GC: Setting calc as failed " + str(calc['id']) + " because calc job failed")
                    models.calc.set_calc_status(calc['user_id'], calc['project_uid_id'], calc['name'],
                                                models.calc.STATUS_KILLED)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)


class FileCollector(async_util.RecurringThread):
    """
    Remove old uploaded files which haven't been removed for one day
    """
    def __init__(self, api_name, *args, **kwargs):
        super(FileCollector, self).__init__(*args, **kwargs)
        conf = api_util.get_conf()
        app_tmp_folder = conf.get("general", "tmp_folder")
        self._uploaded_file_dir = os.path.join(app_tmp_folder, "uploaded_files")
        if not os.path.exists(self._uploaded_file_dir):
            os.makedirs(self._uploaded_file_dir)
        if GC_DEBUG_MODE:
            self._dirty_files = set([])

    @property
    def delay(self):
        return datetime.timedelta(days=1)

    def work(self, *args, **kwargs):
        try:
            yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
            to_delete = []
            for filename in os.listdir(self._uploaded_file_dir):
                if self.should_stop():
                    return
                if filename in ("/", "", ".", ".."):
                    continue
                file_path = os.path.abspath(os.path.join(self._uploaded_file_dir, filename))
                creation_date = datetime.datetime.utcfromtimestamp(os.path.getmtime(file_path))
                if creation_date < yesterday:
                    to_delete.append(file_path)

            for file_path in to_delete:
                if self.should_stop():
                    return
                if GC_DEBUG_MODE:
                    try:
                        if file_path in self._dirty_files:
                            continue
                        self._dirty_files.add(file_path)
                        gc_debug("GC: Removing old temp file: "+str(file_path))
                    except error_util.abort_errors: raise
                    except error_util.all_errors as e:
                        log.error("Unable to remove old uploaded dir " + repr(file_path))
                        error_util.log_error(log, e)
                else:
                    if os.path.isdir(file_path):
                        try:
                            log.warning("GC: Removing old temp folder: " + str(file_path))
                            shutil.rmtree(file_path)
                        except error_util.abort_errors: raise
                        except error_util.all_errors as e:
                            log.error("Unable to remove old uploaded dir " + repr(file_path))
                            error_util.log_error(log, e)
                    else:
                        try:
                            log.warning("GC: Removing old temp file: "+str(file_path))
                            os.remove(file_path)
                        except error_util.abort_errors: raise
                        except error_util.all_errors as e:
                            log.error("Unable to remove old uploaded file " + repr(file_path))
                            error_util.log_error(log, e)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)


class StorageCollector(async_util.RecurringThread):
    """
    Remove old uploaded files which haven't been removed for one day

    """
    def __init__(self, storage, *args, **kwargs):
        """
        :param storage:     The storage to clean
        :type storage:      core.storages.Storage
        """
        super(StorageCollector, self).__init__(*args, **kwargs)
        self._storage = storage
        if GC_DEBUG_MODE:
            self._dirty_files = set([])
            self._missing_files = set([])

    @property
    def delay(self):
        return datetime.timedelta(days=1)

    def work(self, *args, **kwargs):
        # Check if all files in a storage should exists
        try:
            a_week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            files = async_util.run_proc(StorageCollector._list_files, self._storage.name)
            for filename in files:
                if self.should_stop():
                    return
                if models.projects.file_exists(filename):
                    continue
                try:
                    creation_date = async_util.run_proc(StorageCollector._get_file_creation_date,
                                                        self._storage.name, filename)
                except core.storages.FileMissingError:
                    continue  # The file has been already deleted
                if creation_date > a_week_ago:
                    continue
                if GC_DEBUG_MODE:
                    if filename in self._dirty_files:
                        continue
                    self._dirty_files.add(filename)
                    gc_debug("Removing old file " + filename + " on storage " + self._storage.name)
                else:
                    log.warning("GC: Removing old file " + filename + " on storage " + self._storage.name)
                    async_util.run_proc(StorageCollector._delete_file, self._storage.name, filename)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)

        # Check if there is a missing file
        try:
            files = models.projects.list_files_on_storage(self._storage.name)
            for file_info in files:
                filename = file_info['filename']
                if async_util.run_proc(StorageCollector._file_exists, self._storage.name, filename):
                    continue
                if GC_DEBUG_MODE:
                    if filename in self._missing_files:
                        continue
                    self._missing_files.add(filename)
                    gc_debug("Missing file " + filename + " on storage " + self._storage.name)
                else:
                    log.error("GC: Missing file " + filename + " on storage " + self._storage.name)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)

    @staticmethod
    def _list_files(storage_name):
        storage = api_util.get_storage(storage_name)
        return storage.list_files()

    @staticmethod
    def _get_file_creation_date(storage_name, filename):
        storage = api_util.get_storage(storage_name)
        return storage.get_file_creation_date(filename)

    @staticmethod
    def _delete_file(storage_name, filename):
        storage = api_util.get_storage(storage_name)
        storage.delete_file(filename)

    @staticmethod
    def _file_exists(storage_name, filename):
        storage = api_util.get_storage(storage_name)
        return storage.file_exists(filename)


class ProviderArtefactCollector(async_util.RecurringThread):
    """
    Kills worker stuck for various reasons
    """
    def __init__(self, provider, running_jobs, running_workers, *args, **kwargs):
        """
        :param provider:            The provider to clean
        :type provider:             core.providers.Provider
        :param running_jobs:        The list of active job manager
        :type running_jobs:         RunningJobs
        :param running_workers:     The list of active workers manager
        :type running_workers:      RunningWorkers
        """
        super(ProviderArtefactCollector, self).__init__(*args, **kwargs)
        self._provider = provider
        self._running_jobs = running_jobs
        self._running_workers = running_workers
        self._artefact_list_queue = []
        if GC_DEBUG_MODE:
            self._dirty_artefacts = set([])

    @property
    def delay(self):
        # FIXME SAM DEV: change this after checked this is ok
        return datetime.timedelta(seconds=120)

    def work(self, *args, **kwargs):
        if self._running_jobs.get_update_date() <= datetime.datetime.utcfromtimestamp(0):
            return
        if self._running_workers.get_update_date() <= datetime.datetime.utcfromtimestamp(0):
            return
        try:
            artefacts = self._fetch_artefacts()
            if self.should_stop():
                return
            job_ids = [int(job_id) for job_id in self._running_jobs.get_list()]
            worker_ids = [w.worker_id for w in self._running_workers.get_list()]
            for artefact in artefacts:
                if self.should_stop():
                    return
                try:
                    if artefact.job_id is not None:
                        if artefact.job_id in job_ids:
                            continue
                    elif artefact.worker_id is not None:
                        if artefact.worker_id in worker_ids:
                            continue
                    else:
                        log.warning("Bad artefact: no job or worker specified: "+str(artefact))
                        continue

                    if GC_DEBUG_MODE:
                        if artefact in self._dirty_artefacts:
                            continue
                        self._dirty_artefacts.add(artefact)
                        gc_debug("GC: Cleaning " + str(artefact) + " because not worker use it anymore")
                    else:
                        log.warning("GC: Cleaning " + str(artefact) + " because not worker use it anymore")
                        self._provider.delete_artefact(artefact)
                except StandardError as e:
                    error_util.log_error(log, e)
        except error_util.abort_errors: raise
        except error_util.all_errors as e:
            error_util.log_error(log, e)

    def _fetch_artefacts(self):
        """
        Fetch new artefacts, store only new in the list to act like 10 minute buffering

        :return:    The artefacts that are 10 minutes old (5 * self.delay)
        :rtype:     list[core.provider.ProviderArtefact]
        """
        max_length = 5
        current_artefacts = async_util.run_proc(ProviderArtefactCollector._list_artefacts, self._provider.name)
        if self.should_stop():
            return
        new_artefacts = []
        for artefact in current_artefacts:
            for artefact_list in self._artefact_list_queue:
                if self.should_stop():
                    return
                if artefact not in artefact_list:
                    new_artefacts.append(artefact)
        self._artefact_list_queue.append(new_artefacts)
        if len(self._artefact_list_queue) < max_length:
            return []
        else:
            return self._artefact_list_queue.pop(0)

    @staticmethod
    def _list_artefacts(provider_name):
        provider = api_util.get_provider(provider_name)
        return provider.list_artefacts()


class SignalMemory(object):
    """ Class used to store global memory of the datetime of the last abort message received """
    last_signal_received = datetime.datetime.utcfromtimestamp(0)


def raise_keyboard_interrupt(*_):
    """ Callback called when SIGINT or SIGTERM are received """
    received = datetime.datetime.utcnow()
    if (received - SignalMemory.last_signal_received) > IGNORE_SIGNAL_DELAY:
        SignalMemory.last_signal_received = received
        raise KeyboardInterrupt()


def stop_and_join(thread_list):
    for thread in thread_list:
        thread.stop()
    for thread in thread_list:
        thread.join()


def run_garbage_collector(api_name, server_name, redis_host="localhost", redis_port=6379, data_db=0, pubsub_db=1):
    signal.signal(signal.SIGTERM, raise_keyboard_interrupt)
    signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    core.api_util.DatabaseContext.load_conf()
    core.api_util.RedisContext.set_params(api_name, server_name, redis_host, redis_port, data_db, pubsub_db)

    # Loading providers and storages
    conf = api_util.get_conf()
    conf.read(os.path.join(API_PATH, 'config.conf'))
    allowed_providers = json.loads(conf.get("general", "allowed_providers"))
    providers = []
    for provider_name in allowed_providers:
        providers.append(api_util.get_provider(provider_name))
    allowed_storages = json.loads(conf.get("general", "allowed_storages"))
    storages = []
    for storage_name in allowed_storages:
        storages.append(api_util.get_storage(storage_name))

    running_jobs = RunningJobs()

    thread_list = []
    for provider in providers:
        running_workers = RunningWorkers()
        worker_collector = WorkerCollector(provider, api_name, server_name, running_jobs, running_workers)
        worker_collector.start()
        thread_list.append(worker_collector)
        provider_artefact_collector = ProviderArtefactCollector(provider, running_jobs, running_workers)
        provider_artefact_collector.start()
        thread_list.append(provider_artefact_collector)

    job_collector = JobCollector(running_jobs)
    job_collector.start()
    thread_list.append(job_collector)

    model_collector = ModelCollector()
    model_collector.start()
    thread_list.append(model_collector)

    # FIXME: Disable for now
    # file_collector = FileCollector(api_name)
    # file_collector.start()
    # thread_list.append(file_collector)
    #
    # for storage in storages:
    #     storage_collector = StorageCollector(storage)
    #     storage_collector.start()
    #     thread_list.append(storage_collector)

    try:
        while True:
            time.sleep(0.1)
            for proc in thread_list:
                if not proc.is_alive():
                    proc.reraise()
    except error_util.all_errors as e:
        with error_util.before_raising():
            if error_util.is_abort(e):
                log.info("Signal received, exiting...")
            else:
                error_util.log_error(log, e)
            log.info("Garbage collection cleaning...")
            stop_and_join(thread_list)
            log.info("Garbage collection is cleaned")

    log.info("Garbage collection cleaning...")
    stop_and_join(thread_list)
    log.info("Garbage collection is cleaned")


def main():
    """
    Parse command arguments, initialize log and start launch `run_server`

    :return:        0 in case of success, between 1 and 127 in case of failure
    :rtype:         int
    """

    # Initialise and parse command arguments
    parser = argparse.ArgumentParser(description="Api service")
    parser.add_argument('--log-level', '-l', help="log level (ex: info)")
    parser.add_argument('--log-output', help="log out, file path, 'syslog', 'stderr' or 'stdout'")
    parser.add_argument('--redis-host', '-H', help="Redis-server host")
    parser.add_argument('--redis-port', '-P', help='Redis-server connection port')
    parser.add_argument('--redis-data-db', '-i', help="Redis-server database index for data")
    parser.add_argument('--redis-pubsub-db', '-j', help="Redis-server database index for events")
    parser.add_argument('--debug', '-d', action="store_true", help="Enable debug mode")

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
        sys.stderr.write("Error: Invalid logging level " + repr(log_level) + "\n")
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
        redis_data_db = int(args.redis_data_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "data_db"):
        redis_data_db = int(conf.get("redis", "data_db").strip())
    else:
        redis_data_db = 0
    if args.redis_pubsub_db:
        redis_pubsub_db = int(args.redis_pubsub_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "pubsub_db"):
        redis_pubsub_db = int(conf.get("redis", "pubsub_db").strip())
    else:
        redis_pubsub_db = 1

    if args.debug:
        debug_util.register_for_debug()
    else:
        def ignore_signal(*args):
            log.info("Garbage collector not in debug mode, ignoring signal...")
        signal.signal(signal.SIGUSR2, ignore_signal)

    try:
        run_garbage_collector(api_name, server_name, redis_host, redis_port, redis_data_db, redis_pubsub_db)
    except error_util.abort_errors: return 0
    except error_util.all_errors as e:
        logging.getLogger("aziugo").exception(str(e))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
