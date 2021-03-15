# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import datetime
import os

# Project Specific libs

from lib import type_util
from lib import ssh
from worker import Worker
from lifetime_rules import Motive, Penalty

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class WorkerObserver(object):
    def __init__(self, worker, provider, api_name, server_name, launcher_name):
        """
        :param worker:              The base worker
        :type worker:               core.worker.Worker
        :param provider:            The provider of this worker
        :type provider:             core.provider.Provider
        :param api_name:            The name of current API
        :type api_name:             str
        :param server_name:         The name of current server
        :type server_name:          str
        :param launcher_name:       The name of the process that should be running of the worker
        :type launcher_name:        str
        """
        super(WorkerObserver, self).__init__()
        self._conn = None                   # an ssh connection to the instance, type: SshConnection|None
        self._killed = False                # do we have killed the instance? type: bool
        self._probations = []               # list of actual issues detected (warning only), type: list[int]
        self._last_contact_date = None      # when do we have done the last successful ssh connection to this instance? type: datetime.datetime|None
        self._last_job_working_date = None  # when do we have seen the last processus working? type: datetime.datetime|None
        self._killing_date = None           # when the instance have been killed
        self._provider_name = provider.name
        self._api_name = api_name
        self._worker = worker
        self._launcher_name = launcher_name
        self._server_name = server_name
        self._job_id = None
        self._startup_time = provider.get_startup_time()
        self._shutdown_time = provider.get_shutdown_time()
        self._provider_key_path = provider.get_key_path()

    def update(self, worker):
        """
        Fetch all the information of this instance worker object and then try to connect using ssh

        :param worker:       The related worker
        :type worker:        Worker
        """
        self._worker = worker
        if self._killing_date is None and worker.status == Worker.Status.SHUTTING_DOWN:
            self._killing_date = datetime.datetime.utcnow()
        if self.has_immunity():
            return
        job_id = worker.get_tag("job_id")
        if job_id and type_util.ll_int(job_id) and int(job_id) > 0:
            self._job_id = int(job_id)
        if self._killing_date is None and worker.private_ip and not self.is_cluster_slave():
            if self._conn is None:
                ip = worker.public_ip if worker.public_ip else worker.private_ip
                self._conn = ssh.SshConnection(ip, "aziugo", self._provider_key_path)

            found_proc = False
            joinable = self._conn.ping()
            if joinable:
                cmd = "ps aux | grep -v defunct | grep -v grep"
                code, out, err = self._conn.run(cmd, shell=True, can_fail=True, max_retry=0)
            else:
                code = 256
            if code == 0:
                found_proc = self._launcher_name in out
            if code == 0 or joinable:
                self._last_contact_date = datetime.datetime.utcnow()
                self.drop_probation(Motive.NOT_JOINABLE)
            if found_proc:
                self._last_job_working_date = datetime.datetime.utcnow()
                self.drop_probation(Motive.NOT_WORKING)

    @property
    def worker_id(self):
        return self._worker.worker_id

    @property
    def working_date(self):
        """ last time the instance was working, :rtype Optional[datetime.datetime] """
        return self._last_job_working_date

    @property
    def killing_date(self):
        """ when we killed the instance, :rtype Optional[datetime.datetime] """
        return self._killing_date

    @property
    def last_contact_date(self):
        """ last time we connect to the instance, :rtype Optional[datetime.datetime] """
        return self._last_contact_date

    @property
    def status(self):
        return self._worker.status

    @property
    def creation_date(self):
        return self._worker.creation_date

    @property
    def jobid(self):
        return self._job_id

    def get_startup_time(self):
        return self._startup_time

    def get_shutdown_time(self):
        return self._shutdown_time

    def is_cluster_master(self):
        return self._worker.get_tag("type") == "cluster master"

    def is_cluster_slave(self):
        return self._worker.get_tag("type") == "cluster slave"

    def add_probation(self, sentence):
        """
        Add probation sentence motive in order to not send email twice for the same motive and instance

        :param sentence:    The sentence
        :type sentence:     Sentence
        """
        if sentence.penalty != Penalty.PROBATION or self.has_probation(sentence):
            return
        self._probations.append(sentence)

    def has_probation(self, sentence):
        """
        Check if an instance has already suffer the same sentence

        :param sentence:    The sentence
        :type sentence:     Sentence
        :return:            True if the instance has already another sentence for the same motive
        :rtype:             bool
        """
        return sentence in self._probations

    def drop_probation(self, probation):
        """
        Remove a probation from list of current sentences the instance suffer

        :param probation:   The probation type
        :type probation:    int
        """
        self._probations = [x for x in self._probations if x.motive != probation]

    def has_immunity(self):
        """
        Check whenever we should watch this instance or not

        :return:    True if we should watch for this instance
        :rtype:     bool
        """
        return self._killed or self._worker.get_tag("debug") == "true"

    def mark_as_killed(self):
        """
        Fake the worker as killed (usefull for debug purpose)
        """
        self._killed = True

    def __str__(self):
        result = "<"+self._api_name + " Worker " + str(self._worker.worker_id)+" ("+self._provider_name
        if self._worker.tags and "Name" in self._worker.tags.keys():
            result += ": " + self._worker.tags['Name']
        result += ")>"
        return result

    @property
    def description(self):
        result = "id: " + self.worker_id + "\n"
        result += "provider: " + self._provider_name + "\n"
        result += "job_id: " + (str(self._job_id) if self._job_id else "unknown") + "\n"
        result += "ip: " + str(self._worker.public_ip if self._worker.public_ip else self._worker.private_ip) + "\n"
        if not self._worker.tags:
            result += "tags: no"
        else:
            result += "tags:"
            tags = self._worker.tags
            for tag in sorted(tags.keys()):
                result += "\n  "+str(tag)+": "+str(tags[tag])
        return result
