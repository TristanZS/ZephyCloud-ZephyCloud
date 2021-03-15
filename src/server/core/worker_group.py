# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import os
import abc
import time
import uuid
import subprocess
import logging
import re
import datetime

# Project specific libs
from lib import error_util


API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
log = logging.getLogger("aziugo")


class WorkerGroup(object):
    """
    Create a WorkerGroup if you want all the worker to be created in the same place (usage example: clusters)
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, job_id):
        super(WorkerGroup, self).__init__()
        self._job_id = job_id

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean()
        return False

    @property
    def job_id(self):
        return self._job_id

    @abc.abstractmethod
    def init(self):
        pass

    @abc.abstractmethod
    def get_name(self):
        """
        :return:        The unique name of this worker group
        :rtype:         String
        """
        pass

    @abc.abstractmethod
    def clean(self):
        """
        Kill all the instances and do all cleanup
        """
        pass

    @property
    def description(self):
        result = "name: " + self.get_name() + "\n"
        result += "job_id: " + (str(self._job_id) if self._job_id else "unknown") + "\n"
        return result


class AwsWorkerGroup(WorkerGroup):
    """
    Represent a special place to put created instances> For Ec2 it used a placement group and
    a special tuned security group
    """
    CLEAN_TIMEOUT = 300  # in seconds (5 min)

    def __init__(self, job_id, aws_cloud, name):
        """
        :param aws_cloud:   The cloud of the worker group
        :type aws_cloud:    AwsProvider
        :param name:        The name of the group
        :type name:         str
        """
        super(AwsWorkerGroup, self).__init__(job_id)
        self._name = name
        self._cloud = aws_cloud
        self._placement_group = None
        self._security_group = None

    def init(self):
        try:
            self._placement_group = self._cloud.create_placement_group(self.get_name())
            self._security_group = self._cloud.create_security_group_for_cluster(self.get_name())
        except error_util.all_errors:
            with error_util.before_raising():
                self.clean()

    def clean(self):
        """
        Release cloud instances and remove security group and placement group on aws
        """
        timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=AwsWorkerGroup.CLEAN_TIMEOUT)
        if self._security_group:
            try:
                self._cloud.delete_security_group(self._security_group, timeout)
                self._security_group = None
            except Exception as e:
                log.exception(e)

        if self._placement_group:
            if timeout < datetime.datetime.utcnow() + datetime.timedelta(seconds=10):
                timeout = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
            try:
                self._cloud.delete_placement_group(self._placement_group, timeout)
                self._placement_group = None
            except Exception as e:
                log.exception(e)

    def get_name(self):
        return self._name

    def get_location(self):
        return self._cloud.location

    def get_security_groups(self):
        return [self._security_group]

    def set_sec_group(self, sec_group):
        self._security_group = sec_group

    def set_placement_group(self, placement_group):
        self._placement_group = placement_group

    @property
    def description(self):
        result = "name: " + self.get_name() + "\n"
        result += "job_id: " + (str(self._job_id) if self._job_id else "unknown") + "\n"
        result += "type: Aws\n"
        result += "provider: " + self._cloud.name + "\n"
        result += "location: " + self.get_location() + "\n"
        if self._security_group:
            result += "security group: " + self._security_group.name +" (" + str(self._security_group.id) + ")\n"
        else:
            result += "security groups: not defined\n"
        if self._placement_group:
            result += "placement group: " + str(self._placement_group) + "\n"
        else:
            result += "placement group: not defined\n"
        return result


class DockerWorkerGroup(WorkerGroup):
    def __init__(self, job_id, name):
        """
        :param name:        The name of the work group
        :type name:         str
        """
        super(DockerWorkerGroup, self).__init__(job_id)
        self._name = name
        self._shared_volume = None

    def init(self):
        try:
            self._shared_volume = re.sub("_+", "_", re.sub("[^a-z0-9_]+", "_", self._name.lower()))
            cmd = ['docker', 'volume', 'create', self._shared_volume]
            subprocess.check_output(cmd, cwd=API_PATH, stderr=subprocess.PIPE)
        except error_util.all_errors:
            with error_util.before_raising():
                self.clean()

    def clean(self):
        if not self._shared_volume:
            return
        cmd = ['docker', 'volume', 'rm', self._shared_volume]
        try:
            subprocess.check_output(cmd, cwd=API_PATH, stderr=subprocess.PIPE)
        except error_util.all_errors as e:
            error_util.log_error(log, e)

    def get_name(self):
        """
        :return:        The unique name of this worker group
        :rtype:         String
        """
        return self._name

    def get_volume_name(self):
        return self._shared_volume

    def set_volume_name(self, sharded_volume_name):
        self._shared_volume = sharded_volume_name

    @property
    def description(self):
        result = "name: " + self.get_name() + "\n"
        result += "job_id: " + (str(self._job_id) if self._job_id else "unknown") + "\n"
        result += "type: Docker\n"
        if self._shared_volume:
            result += "shared volume: " + self._shared_volume + "\n"
        else:
            result += "shared volume: not defined\n"
        return result
