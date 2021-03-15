# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import abc
import json
import time
import logging
import os
import datetime
import subprocess
import re
import math

# Third party libs
import boto3
import botocore.exceptions

# Project Specific libs
from lib import util
from lib import error_util
from lib import proc_util
from lib import type_util
import worker
import api_util
from worker_group import AwsWorkerGroup, DockerWorkerGroup, WorkerGroup


API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
log = logging.getLogger("aziugo")
USE_ALARM=0


class Provider(object):
    LOCATION_EUROPE = "eu"
    LOCATION_CHINA = "cn"
    LOCATION_USA = "us"
    LOCATION_CANADA = "ca"
    LOCATION_INDIA = "in"
    LOCATION_KOREA = "ko"
    LOCATION_JAPAN = "ja"
    LOCATION_SINGAPORE = "sg"
    LOCATION_AUSTRALIA = "au"
    LOCATION_BRAZIL = "br"

    """
    A Cloud instance is an abstraction of a cloud service (for example AWS)
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, location):
        """
        :param location:    The location of the cloud, for example, 'eu' or 'cn'
        :type location:     str
        """
        super(Provider, self).__init__()
        self._name = name
        self._location = location

    @abc.abstractmethod
    def get_default_storage_name(self):
        """
        Get the name of the default storage associated with this cloud provider (if any)
        :return:    A storage name or None
        :rtype:     str|None
        """
        return None

    @abc.abstractmethod
    def list_workers(self):
        """
        Get the list of all running workers
        :return:                The list of workers
        :rtype:                 list[worker.Worker]
        """
        pass

    @abc.abstractmethod
    def create_workers(self, nb_workers=1, worker_group=None, **creation_options):
        """
        Create one or more worker machine instances
        :param nb_workers:          The number of workers to create. Optional, default 1
        :type nb_workers:           Int
        :param worker_group:        A specific WorkerGroup if you want all the worker to be
                                    created in the same place (usage example: clusters). Optional, default None
        :type worker_group:         WorkerGroup|None
        :param creation_options:    A list of creation argument specific to the cloud we want.
                                         For example, you should provide 'm4.large' as the 'machine' argument for
                                         AwsCloud instances. Please refer to the specific cloud documentation
        :type creation_options:     dict
        :return:                    The created instances
        :rtype:                     list[worker.Worker]
        """
        return []

    @abc.abstractmethod
    def generate_worker_group(self, job_id):
        """
        Create a WorkerGroup if you want all the worker to be created in the same place (usage example: clusters)
        :param job_id:      The id of the job
        :type job_id:       int
        :return:            A new Worker group
        :rtype:             WorkerGroup
        """
        return None

    @abc.abstractmethod
    def terminate_workers(self, workers):
        """
        Stop worker machine instances
        :param workers:         The worker you want to stop
        :type workers:          list[worker.Worker]|list[str]
        """
        pass

    @abc.abstractmethod
    def get_startup_time(self):
        """
        Get the time needed to create an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        pass

    @abc.abstractmethod
    def get_shutdown_time(self):
        """
        Get the time needed to stop an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        pass

    def tag_workers(self, workers, tags):
        """
        Add some tag to the worker instances if the could have tag capability, otherwise, do nothing
        :param workers:         The workers to tag
        :type workers:          list[worker.Worker]|list[str]
        :param tags:            values to tag
        :type tags:             dict[str:str]
        """
        return

    @property
    def location(self):
        """
        :return:                The location of the cloud, for example, 'eu' or 'cn'
        :rtype:                 str
        """
        return self._location

    @property
    def name(self):
        """
        :return:                The name of the cloud provider
        :rtype:                 str
        """
        return self._name

    @abc.abstractmethod
    def get_key_path(self, root=False):
        """
        Get the path of path of the ssh key to access to the workers

        :param root:    Do you want the ssh key of the root user. Optional, default False
        :type root:     bool
        :return:        The path of the ssh key to get access to the worker
        :rtype:         str|None
        """
        return None

    @property
    def type(self):
        return "unknown"

    def list_artefacts(self):
        """
        List all artefacts created for worker groups

        :return:        The provider artefacts
        :rtype:         list[ProviderArtefact]
        """
        return []

    def delete_artefact(self, artefact):
        """

        :param artefact:
        :type artefact:     ProviderArtefact
        """
        pass


class ProviderArtefact(object):
    """
    This class represent anything that given provider create and could need to be cleaned
    """
    def __init__(self, provider, type, data, job_id=None, worker_id=None):
        """
        :param provider:
        :type provider:         Provider
        :param type:
        :type type:             str
        :param data:
        :type data:             str|any
        :param job_id:
        :type job_id:           int|None
        :param worker_id:
        :type worker_id:        str|None
        """
        super(ProviderArtefact, self).__init__()
        self._provider_name = str(provider.name)
        self.type = type
        self.data = data
        self.job_id = job_id
        self.worker_id = worker_id

    def __str__(self):
        return str(self.type) + " " + str(self.data) + " on " + self._provider_name

    def __eq__(self, other):
        if not isinstance(other, ProviderArtefact):
            return False
        if self._provider_name != other._provider_name:
            return False
        if self.type != other.type or self.data != other.data:
            return False
        return self.job_id == other.job_id and self.worker_id == other.worker_id

    def __hash__(self):
        return hash((self._provider_name, self.type, str(self.data), self.job_id, self.worker_id))


class AwsProvider(Provider):
    """
    Represent a specific AWS API.
    Note: Each location (china, europe) should be represented by a different cloud service
    """

    class StatusFlags(object):  # AWS status flags
        UNDEFINED = -1
        PENDING = 0
        RUNNING = 16
        SHUTTING_DOWN = 32
        TERMINATED = 48
        STOPPING = 64
        STOPPED = 80

    @staticmethod
    def tags_to_dict(tags):
        if not tags:
            return {}
        result = {}
        for tag_info in tags:
            result[tag_info['Key']] = tag_info["Value"]
        return result

    @staticmethod
    def dict_to_tags(tags_dict):
        result = []
        for key, val in tags_dict.items():
            result.append({"Key": key, "Value": str(val)})
        return result

    def __init__(self, conf, name):
        """
        :param conf:        A description of the storage
        :type conf:         ConfigParser.ConfigParser
        :param name:        The name of the storage
        :type name:         str
        """
        section_name = "provider_"+name
        location = self._get_config(conf, section_name, 'location')
        super(AwsProvider, self).__init__(name, location)

        self._ec2_conn = None
        self._cw_conn = None
        self._sns_conn = None

        # Init fields from config
        self._api_name = conf.get("general", "api_name")
        self._server_name = conf.get("general", "server")

        self._api_group = self._api_name+":"+self._server_name
        self._default_storage = self._get_config(conf, section_name, 'default_storage')

        key_name = conf.get("provider_"+name, 'key_name')
        self._key_path = os.path.join(API_PATH, "cloud_ssh_keys", key_name)
        key_name = conf.get("provider_"+name, 'root_key_name')
        self._root_key_path = os.path.join(API_PATH, "cloud_ssh_keys", key_name)

        self._region = self._get_config(conf, section_name, 'aws_region')
        self._access_key_id = self._get_config(conf, section_name, 'aws_access_key_id')
        self._access_key_secret = self._get_config(conf, section_name, 'aws_access_key_secret')

        self._ami = self._get_config(conf, section_name, 'ami')
        # FIXME ZOPEN: TO GET FROM DB INSTEAD
        self._ebs_size = int(self._get_config(conf, section_name, 'ebs_block_size'))
        self._security_groups = json.loads(self._get_config(conf, section_name, 'security_groups'))
        self._security_groups.extend([self._api_group, self._name])

        self._cluster_ami = self._get_config(conf, section_name, 'cluster_ami')
        # FIXME ZOPEN: TO GET FROM DB INSTEAD
        self._cluster_ebs_size = int(self._get_config(conf, section_name, 'cluster_ebs_block_size'))

        # Disable boto logging
        logging.getLogger('boto').propagate = False

    @property
    def type(self):
        return "aws"

    def list_workers(self):
        """
        Get the list of all running workers

        :return:                The list of workers
        :rtype:                 list[worker.Worker]
        """
        worker_list = []
        instance_list = self.conn.instances.filter(Filters=[{"Name": "instance.group-name",
                                                             "Values": [self._name]},
                                                            {"Name": "instance.group-name",
                                                             "Values": [self._api_group]}])
        if not instance_list:
            return worker_list

        for instance in instance_list:
            new_worker = worker.Worker(instance.id, instance.public_ip_address, instance.private_ip_address)

            new_worker.set_tags(AwsProvider.tags_to_dict(instance.tags))
            creation_date = instance.launch_time
            new_worker.set_creation_date(creation_date)
            aws_status = instance.state['Code']
            if aws_status == AwsProvider.StatusFlags.UNDEFINED:
                new_worker.set_status(worker.Worker.Status.UNDEFINED)
            elif aws_status == AwsProvider.StatusFlags.PENDING:
                new_worker.set_status(worker.Worker.Status.PENDING)
            elif util.has_flag(aws_status, AwsProvider.StatusFlags.TERMINATED):
                new_worker.set_status(worker.Worker.Status.TERMINATED)
            elif util.has_flag(aws_status, AwsProvider.StatusFlags.STOPPING):
                new_worker.set_status(worker.Worker.Status.SHUTTING_DOWN)
            elif util.has_flag(aws_status, AwsProvider.StatusFlags.SHUTTING_DOWN):
                new_worker.set_status(worker.Worker.Status.SHUTTING_DOWN)
            else:  # stopped instances are still considered as running, because they still cost (really few) money
                new_worker.set_status(worker.Worker.Status.RUNNING)
            worker_list.append(new_worker)
        return worker_list

    def get_key_path(self, root=False):
        """
        Get the path of path of the ssh key to access to the workers

        :param root:    Do you want the ssh key of the root user. Optional, default False
        :type root:     bool
        :return:        The path of the ssh key to get access to the worker
        :rtype:         str|None
        """
        return self._root_key_path if root else self._key_path

    def get_default_storage_name(self):
        """
        Get the name of the default storage associated with this cloud provider (if any)
        :return:    A storage name or None
        :rtype:     str|None
        """
        return self._default_storage

    def generate_worker_group(self, job_id):
        """
        Create a WorkerGroup if you want all the worker to be created in the same place (usage example: clusters)
        The worker group is an Ec2 placement group and a specific security group

        :param job_id:      The id of the job used for this group
        :type job_id:       int
        :return:            A new Worker group
        :rtype:             AwsWorkerGroup
        """
        worker_group_name = self._api_name + "/" + self._server_name + "/" + self.name + "/cluster_" + str(job_id)
        return AwsWorkerGroup(job_id, self, worker_group_name)

    def create_workers(self, nb_workers=1, worker_group=None, **creation_options):
        """
        Create one or more Ec2 worker machine instances

        :param nb_workers:          The number of workers to create. Optional, default 1
        :type nb_workers:           int
        :param worker_group:        A specific WorkerGroup if you want all the worker to be
                                    created in the same place (usage example: clusters). Optional, default None
        :type worker_group:         AwsWorkerGroup|None
        :param creation_options:    For Aws the specif arguments are:
                                        'machine'        str, REQUIRED, The machine type you want (ex: 'm4.large')
        :type creation_options:     any
        :return:                    The created instances
        :rtype:                     list[worker.Worker]
        """
        if 'machine' not in creation_options or creation_options['machine'] is None:
            raise RuntimeError("AwsCloud.create_worker need a 'machine' argument")
        machine_type = creation_options['machine']
        sec_groups = self._security_groups
        if worker_group is None:
            ami_to_launch = self._ami
            ebs_size = self._ebs_size
            placement_group = None
        else:
            ami_to_launch = self._cluster_ami
            ebs_size = self._cluster_ebs_size
            placement_group = worker_group.get_name()
            sec_groups.extend(worker_group.get_security_groups())

        workers, cpu_per_machine = self._create_instances(nb_workers, machine_type, ami_to_launch, ebs_size, sec_groups,
                                                          placement_group)
        if USE_ALARM:
            threshold = self._compute_alert_threshold(cpu_per_machine)
            try:
                for new_worker in workers:
                    self._create_alert(new_worker, threshold)
            except:
                with error_util.before_raising():
                    self.terminate_workers(workers)
        return workers

    def terminate_workers(self, workers):
        """
        Stop worker machine instances

        :param workers:         The worker you want to stop
        :type workers:          list[str]|list[worker.Worker]
        """
        instance_ids = [w.worker_id if isinstance(w, worker.Worker) else w for w in workers]
        instance_ids = [str(i) for i in instance_ids if i is not None and i != ""]
        if not instance_ids:
            return
        log.info("Killing instances "+", ".join(instance_ids))
        try:
            filters = [{"Name": "instance-id", "Values": instance_ids},
                       {"Name": "instance-state-name", "Values": ["pending", "running"]}]
            instance_list = list(self.conn.instances.filter(Filters=filters))
            while len(instance_list) > 0:
                self.conn.meta.client.terminate_instances(InstanceIds=[str(instance.id) for instance in instance_list])
                time.sleep(1)
                instance_list = list(self.conn.instances.filter(Filters=filters))
        finally:
            if USE_ALARM:
                for instance_id in instance_ids:
                    self._del_alert(instance_id)

    def tag_workers(self, workers, tags):
        """
        Add some tag to the worker instances

        :param workers:         The workers to tag
        :type workers:          list[str]|list[worker.Worker]
        :param tags:            Values of the tags
        :type tags:             dict[str, str]
        """
        instance_ids = [w.worker_id if isinstance(w, worker.Worker) else w for w in workers]
        self.conn.meta.client.create_tags(Resources=instance_ids, Tags=AwsProvider.dict_to_tags(tags))

    def list_artefacts(self):
        """
        List all artefacts created for worker groups

        :return:        The provider artefacts
        :rtype:         list[ProviderArtefact]
        """
        results = []

        # List security groups
        group_prefix = self._api_name + "/" + self._server_name + "/" + self.name + "/cluster_"
        groups = self.conn.security_groups.all()
        for group in groups:
            if not group.group_name.startswith(group_prefix):
                continue
            job_id_str = group.group_name[len(group_prefix):]
            if not type_util.ll_int(job_id_str):
                log.warning("Invalid group name: " + repr(group.group_name))
                continue
            results.append(ProviderArtefact(self, "security_group", group.group_name, job_id=int(job_id_str)))

        # List placement groups
        place_groups = self.conn.placement_groups.all()
        for group in place_groups:
            if not group.name.startswith(group_prefix):
                continue
            job_id_str = group.name[len(group_prefix):]
            if not type_util.ll_int(job_id_str):
                log.warning("Invalid group name: " + repr(group.name))
                continue
            results.append(ProviderArtefact(self, "placement_group", group.name, job_id=int(job_id_str)))

        # List cloudwatch alerts
        prefix = self._api_name + "/" + self._server_name + "/" + self.name + ":"
        cw_rsc = boto3.resource("cloudwatch", region_name=self._region, aws_access_key_id=self._access_key_id,
                                aws_secret_access_key=self._access_key_secret)
        alarms = cw_rsc.alarms.all()
        for alarm in alarms:
            if not str(alarm.name).startswith(prefix):
                continue
            instance_name = str(alarm.name)[len(prefix):]
            results.append(ProviderArtefact(self, "alert", alarm.name, worker_id=instance_name))
        return results

    def delete_artefact(self, artefact):
        """

        :param artefact:
        :type artefact:     ProviderArtefact
        """
        try:
            if artefact.type == "alert":
                self.cw_conn.Alarm(artefact.data).delete()
            elif artefact.type == "security_group":
                self.conn.SecurityGroup(artefact.data).delete()
            elif artefact.type == "placement_group":
                self.conn.PlacementGroup(artefact.data).delete()
            else:
                raise RuntimeError("Unknown artefact type " + str(artefact.type))
        except StandardError as e:
            log.warning("Unable to delete " + str(artefact) + ": " + str(e))

    def create_placement_group(self, group_name):
        """
        Create a placement group. Usefull for clusters

        :param group_name:      The name of the group
        :type group_name:       str
        :return:                The real final name of the placement group
        :rtype:                 str
        """
        safe_group_name = group_name[0:255]
        self.conn.create_placement_group(GroupName=safe_group_name, Strategy="cluster")
        return safe_group_name

    def delete_placement_group(self, group_name, timeout=300):
        """
        Remove a placement group, waiting for it to not contains instances anymore
        If timeout is None of 0, never fails

        :param group_name:          The name of the group
        :type group_name:           str
        :param timeout:             The number of seconds we wait before raising error
        :type timeout:              int|float|datetime.timedelta|datetime.datetime|None
        """
        if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
            time_limit = None
        elif isinstance(timeout, datetime.datetime):
            time_limit = timeout
        else:
            if not isinstance(timeout, datetime.timedelta):
                timeout = datetime.timedelta(milliseconds=int(float(timeout) * 1000))
            time_limit = datetime.datetime.utcnow() + timeout
        log.info("Deleting aws placement group "+group_name+"...")
        group = self.conn.PlacementGroup(group_name)
        filters=[{"Name": "instance-state-name",
                  "Values": ["pending", "running", "shutting-down", "stopping", "stopped"]}]
        while time_limit is None or datetime.datetime.utcnow() < time_limit:
            instances = group.instances.filter(Filters=filters).limit(1)
            if len(list(instances)) > 0:
                time.sleep(2)
            else:
                group.delete()
                log.info("Aws placement group " + group_name + " deleted")
                return
        raise RuntimeError("Timeout exceded to delete aws placement group "+group_name)

    def create_security_group_for_cluster(self, group_name):
        """
        Create an EC2 security group for cluster and configure it

        :param group_name:      The name of the security group
        :type group_name:       str
        :return:                The real name of the security group
        :rtype:                 str
        """
        safe_group_name = group_name[0:255]
        tags = {"Name": group_name, "api": self._api_name, "server": self._server_name}
        resp = self.conn.meta.client.create_security_group(GroupName=safe_group_name,
                                                           Description=group_name + " security group")
        try:
            sec_group = self.conn.SecurityGroup(resp['GroupId'])
            sec_group.create_tags(Tags=AwsProvider.dict_to_tags(tags))
            sec_group.authorize_ingress(CidrIp="0.0.0.0/0", FromPort=22, ToPort=22, IpProtocol="tcp")
            sec_group.authorize_ingress(SourceSecurityGroupName=safe_group_name)
            return safe_group_name
        except:
            self.conn.meta.client.delete_security_group(GroupName=safe_group_name)
            raise

    def delete_security_group(self, group_name, timeout=300):
        """
        Remove a security group, waiting for it to not contains instances anymore
        If timeout is None of 0, never fails

        :param group_name:          The name of the group
        :type group_name:           str
        :param timeout:             The number of seconds we wait before raising error. Optional, default 5 min
        :type timeout:              int|float|datetime.timedelta|datetime.datetime|None
        """

        if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
            time_limit = None
        elif isinstance(timeout, datetime.datetime):
            time_limit = timeout
        else:
            if not isinstance(timeout, datetime.timedelta):
                timeout = datetime.timedelta(milliseconds=int(float(timeout) * 1000))
            time_limit = datetime.datetime.utcnow() + timeout

        log.info("Deleting aws security group " + group_name + "...")
        group_id = self._get_sec_goup_id(group_name)
        filters = [{"Name": "instance.group-name", "Values": [group_name]}]
        # {"Name": "instance-state-name", "Values": ["pending", "running", "shutting-down", "stopping", "stopped"]}
        while time_limit is None or datetime.datetime.utcnow() < time_limit:
            instances = self.conn.instances.limit(1).filter(Filters=filters)
            for instance in instances:
                sec_groups_to_keep = [sg['GroupId'] for sg in instance.security_groups if sg['GroupId'] != group_id]
                instance.modify_attribute(Groups=sec_groups_to_keep)

            if len(list(self.conn.instances.limit(1).filter(Filters=filters))) > 0:
                time.sleep(2)
            else:
                self.conn.meta.client.delete_security_group(GroupName=group_name)
                log.info("Aws security group " + group_name + " deleted")
                return
        raise RuntimeError("Timeout exceded to delete security group " + group_name)

    def get_startup_time(self):
        """
        Get the time needed to create an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        return datetime.timedelta(seconds=120)

    def get_shutdown_time(self):
        """
        Get the time needed to stop an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        return datetime.timedelta(seconds=90)

    @property
    def region(self):
        """
        :return:        The AWS cloud region ( for example 'cn-north-1' )
        :rtype:         str
        """
        return self._region

    @property
    def conn(self):
        """
        :return:        The boto connection instance
        :rtype:         boto3.resources.factory.ec2.ServiceResource
        """
        if self._ec2_conn is None:
            self._ec2_conn = boto3.resource("ec2", region_name=self._region, aws_access_key_id=self._access_key_id,
                                            aws_secret_access_key=self._access_key_secret)
        return self._ec2_conn

    @property
    def cw_conn(self):
        """
        :return:        The boto connection instance
        :rtype:         boto3.resources.factory.cloudwatch.ServiceResource
        """
        if self._cw_conn is None:
            self._cw_conn = boto3.resource("cloudwatch", region_name=self._region,
                                           aws_access_key_id=self._access_key_id,
                                           aws_secret_access_key=self._access_key_secret)
        return self._cw_conn

    @property
    def sns_conn(self):
        """
        :return:        The boto connection instance
        :rtype:         boto3.resources.factory.sns.ServiceResource
        """
        if self._sns_conn is None:
            self._sns_conn = boto3.resource("sns", region_name=self._region,
                                            aws_access_key_id=self._access_key_id,
                                            aws_secret_access_key=self._access_key_secret)
        return self._sns_conn

    def _get_sec_goup_id(self, group_name):
        filters=[{"Name": 'group-name', "Values": [group_name]}]
        response = self.conn.meta.client.describe_security_groups(Filters=filters)
        return response['SecurityGroups'][0]['GroupId']

    def _compute_alert_threshold(self, cpu_count):
        """
        Set under which percent of CPU use we should send an alert

        :param cpu_count:       The number of cores per machine
        :type cpu_count:        int
        :return:                The CPU usage percentage at which the machine should be considered as idle
        :rtype:                 int
        """
        return max(1, math.ceil(11 - (2 * math.log(cpu_count))))

    def _get_config(self, conf, section_name, key):
        """
        Return an aws config value. It will look for location specific data if any, otherwise, it will return the
        default one

        :param key:         The config key
        :type key:          str
        :return:            The value in the config
        :rtype:             str
        """
        if conf.has_section(section_name) and conf.has_option(section_name, key):
            return conf.get(section_name, key)
        return conf.get('aws_default', key)

    def _on_clean_error(self, title, msg, instance_list):
        """
        Send email and log error when we failed to clean instances

        :param title:               The email subject we will send to the sysadmins
        :type title:                str
        :param msg:                 The content of the log and the email we will send to the sysadmin
        :type msg:                  str
        :param instance_list:       The failed instances
        :type instance_list:        list[boto3.resources.factory.ec2.Instance]
        """
        log.error("Provider cleaning error: "+str(msg))
        instance_ids = []
        if instance_list:
            try:
                instance_ids = [i.id for i in instance_list]
            except error_util.all_errors as e:
                log.warning("Error while listing instances to clean manually: "+str(e))
        try:
            msg += "\n"
            if instance_ids:
                msg += "Instances:\n  - " + "\n  - ".join(instance_ids) + "\n"
            api_util.send_admin_email(title, msg)
        except error_util.all_errors as e:
            log.error("Unable to send alert: "+str(e))

    def _create_instances(self, nb_workers, machine_type, ami_to_launch, ebs_size, sec_groups,
                          placement_group):
        """
        Create some regular Ec2 instances

        :param nb_workers:              The number of workers
        :type nb_workers:               int
        :param machine_type:            The machine type you want (ex: 'm4.large')
        :type machine_type:             str
        :param ami_to_launch:           The ami id you want (ex: 'ami-cadetf')
        :type ami_to_launch:            str
        :param ebs_size:                The disk size on the machines
        :type ebs_size:                 int
        :param sec_groups:              A list of Ec2 security group ids
        :type sec_groups:               list[str]
        :param placement_group:         The name of the placement group (or None)
        :type placement_group:          str|None
        :return:                        The created instances and the number of cpu per machine
        :rtype:                         Tuple[list[worker.Worker], int]
        """
        risc = False
        instance_list = []
        instance_ids = []
        launch_args = { "ImageId": ami_to_launch,
                        "InstanceType": machine_type,
                        "MinCount": nb_workers,
                        "MaxCount": nb_workers,
                        "SecurityGroups": sec_groups,
                        "Monitoring": {'Enabled': True},
                        "DisableApiTermination": False,
                        "EbsOptimized": False,
                        "IamInstanceProfile" :{"Name": "ec2_instance_autostop"},
                        "InstanceInitiatedShutdownBehavior": "terminate",
                        "BlockDeviceMappings": [{
                           'DeviceName': '/dev/sda1',
                           'Ebs': {
                               'VolumeSize': ebs_size,
                               'DeleteOnTermination': True,
                           }
                       }]}
        if placement_group:
            launch_args["Placement"] = {"GroupName": placement_group}
        try:
            risc = True
            instance_list = self.conn.create_instances(**launch_args)
            instance_ids = [i.id for i in instance_list]
            risc = False
            instance_list = self._wait_for_instances_info(instance_ids, 300)
            cpu_info = instance_list[0].cpu_options
            cpu_per_machine = cpu_info['CoreCount'] * cpu_info['ThreadsPerCore']
            results = []
            for instance in instance_list:
                results.append(worker.Worker(instance.id, instance.public_ip_address, instance.private_ip_address))
            return results, cpu_per_machine
        except error_util.all_errors as e:
            with error_util.before_raising():
                if risc:
                    log.warning("Maybe some aws instance have beeing created and not cleaned")
                if instance_list:
                    if error_util.is_abort(e):
                        log.warning("Aws instance creation canceled, try to clean...")
                    else:
                        log.error("Error during aws instance creation, try to clean...")
                    try:
                        self.terminate_workers(instance_ids)
                        log.info("workers cleaned successfully")
                    except error_util.abort_errors:
                        self._on_clean_error("Worker cleaned aborted.",
                                             "Aws instances clean up canceled. Please do it MANUALLY !!!",
                                             instance_list)
                    except error_util.all_errors as e:
                        error_util.log_error(log, e)
                        self._on_clean_error("Worker cleaned aborted.",
                                             "Unable to clean aws instances. Please do it MANUALLY !!!",
                                             instance_list)

    def _wait_for_instances_info(self, instance_id_list, timeout=300):
        """
        Wait for instance to have been lanched and have ip defined
        Timeout is never reached is timeout is 0 or None

        :param instance_id_list:        List of instance Id to wait for initialisation
        :type instance_id_list:         list[str]
        :param timeout:                 How many time do we wait before raising an error in secons. Optional, 5min
        :type timeout:                  int|float|datetime.timedelta|datetime.datetime|None
        :return:                        The list of instance infob
        :rtype:                         list[boto3.resources.factory.ec2.Instance]
        """
        if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
            time_limit = None
        elif isinstance(timeout, datetime.datetime):
            time_limit = timeout
        else:
            if not isinstance(timeout, datetime.timedelta):
                timeout = datetime.timedelta(milliseconds=int(float(timeout) * 1000))
            time_limit = datetime.datetime.utcnow() + timeout

        filters = [{"Name": "instance-id", "Values": instance_id_list}]
        while time_limit is None or datetime.datetime.utcnow() < time_limit:
            new_instance_list = self.conn.instances.filter(Filters=filters)
            result = []
            for instance in new_instance_list:
                if not instance.public_ip_address or not instance.private_ip_address:
                    break
                result.append(instance)
            if len(result) == len(instance_id_list):
                return result
            time.sleep(2)
        raise RuntimeError("Unable to get instance public ip at creation after " + str(timeout))

    def _create_alert(self, worker_or_id, threshold):
        """
        Create a cloudwatch alarm

        :param worker_or_id:
        :type worker_or_id:       worker.Worker|str
        """
        instance_id = worker_or_id.worker_id if isinstance(worker_or_id, worker.Worker) else worker_or_id
        log.info("Creating AWS alarm for instance " +str(instance_id))
        topic_arn = None
        for topic in self.sns_conn.topics.all():
            if str(topic.arn).endswith(":"+self._api_name+"-alert"):
                topic_arn = topic.arn
        if topic_arn is None:
            raise RuntimeError("Unable to find topic "+self._api_name+"-alert")
        alarm_name = self._api_name + "/" + self._server_name + "/" + self.name + ":" + str(instance_id)
        description = "Zephycloud CPU utilisation alarm for instance " + str(instance_id)
        self.cw_conn.meta.client.put_metric_alarm(AlarmName=alarm_name,
                                                  AlarmDescription=description,
                                                  Namespace="AWS/EC2",
                                                  ActionsEnabled=False,
                                                  MetricName="CPUUtilization",
                                                  Unit="Seconds",
                                                  Threshold=threshold,
                                                  ComparisonOperator="LessThanOrEqualToThreshold",
                                                  Period=300,
                                                  EvaluationPeriods=1,
                                                  Statistic="Average",
                                                  TreatMissingData="notBreaching",
                                                  Dimensions=[{'Name': 'InstanceId',
                                                               'Value': 'INSTANCE_ID'}])

    def _del_alert(self, worker_or_id):
        """

        :param worker_or_id:
        :type worker_or_id:       worker.Worker|str
        """
        try:
            instance_id = worker_or_id.worker_id if isinstance(worker_or_id, worker.Worker) else worker_or_id
            log.info("Deleting AWS alarm for instance " + str(instance_id))
            al = self.cw_conn.Alarm(self._api_name + "/" + self._server_name + "/" + self.name + ":" + str(instance_id))
            if al:
                al.delete()
        except BaseException as e:
            log.exception(e)


class AwsSpotProvider(AwsProvider):
    """
    Represent a specific AWS API.
    Note: Each location (china, europe) should be represented by a different cloud service
    """

    def __init__(self, conf, name):
        """
        :param conf:    A description of the storage
        :type conf:     ConfigParser.ConfigParser
        :param name:    The name of the storage
        :type name:     str
        """
        super(AwsSpotProvider, self).__init__(conf, name)
        self._price_history_token = None
        self._last_history_date = datetime.datetime.utcfromtimestamp(0)
        self._price_history = None
        section_name = "provider_" + name
        self._startup_time = datetime.timedelta(seconds=int(self._get_config(conf, section_name, 'startup_time')))

    @property
    def type(self):
        return "aws_spot"

    def create_workers(self, nb_workers=1, worker_group=None, **creation_options):
        """
        Create one or more Ec2 worker machine spot instances

        :param nb_workers:          The number of workers to create. Optional, default 1
        :type nb_workers:           int
        :param worker_group:        A specific WorkerGroup if you want all the worker to be
                                    created in the same place (usage example: clusters). Optional, default None
        :type worker_group:         AwsWorkerGroup|None
        :param creation_options:    For Aws the specif arguments are:
                                        'machine'        str, REQUIRED, The machine type you want (ex: 'm4.large')
                                        'spot_price'     ???, Required, The spot price if you want spot workers
        :type creation_options:     any
        :return:                    The created instances
        :rtype:                     list[worker.Worker]
        """
        if 'machine' not in creation_options or creation_options['machine'] is None:
            raise RuntimeError("AwsCloud.create_worker need a 'machine' argument")
        machine_type = creation_options['machine']
        if 'spot_price' not in creation_options or creation_options['spot_price'] is None:
            raise RuntimeError("No spot price defined")
        spot_price = creation_options['spot_price']
        sec_groups = self._security_groups
        if worker_group is None:
            ami_to_launch = self._ami
            ebs_size = int(self._ebs_size)
            placement_group = None
        else:
            ami_to_launch = self._cluster_ami
            ebs_size = int(self._cluster_ebs_size)
            placement_group = worker_group.get_name()
            sec_groups.extend(worker_group.get_security_groups())

        workers, cpu_per_machine = self._create_spot_instances(nb_workers, spot_price, machine_type, ami_to_launch,
                                                               ebs_size, sec_groups, placement_group)
        if USE_ALARM:
            threshold = self._compute_alert_threshold(cpu_per_machine)
            try:
                for worker_object in workers:
                    self._create_alert(worker_object, threshold)
            except Exception:
                self.terminate_workers(workers)
                raise
        return workers

    def get_spot_price_history(self, machine_type, days=30):
        """
        Get the prices list for a specific machine

        :param machine_type:        The machine type (ex: "c5.2xlarge")
        :type machine_type:         str
        :param days:                The history length, in days. Optional, default 30
        :type days:                 int
        :return:                    The list of price in dollar per hour
        :rtype:                     list[float]
        """
        now = datetime.datetime.utcnow()
        result = self.conn.meta.client.describe_spot_price_history(InstanceTypes=[machine_type],
                                                                   StartTime=now-datetime.timedelta(days=days),
                                                                   EndTime=now,
                                                                   ProductDescriptions=['Linux/UNIX'],
                                                                   AvailabilityZone=self._region+"a",
                                                                   MaxResults=70)
        sorted_results = sorted(result['SpotPriceHistory'], key=lambda x: x['Timestamp'], reverse=True)
        return [float(r['SpotPrice']) for r in sorted_results]

    def get_startup_time(self):
        """
        Get the time needed to create an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        return super(AwsSpotProvider, self).get_startup_time() + self._startup_time

    def get_shutdown_time(self):
        """
        Get the time needed to stop an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        aws_shutdown = super(AwsSpotProvider, self).get_shutdown_time()
        return aws_shutdown + aws_shutdown  # We count it twice, one for the master, and on for the slaves

    def _create_spot_instances(self, nb_workers, spot_price, machine_type, ami_to_launch, ebs_size,
                               sec_groups, placement_group):
        """
        Create some Ec2 spot instances

        :param nb_workers:              The number of workers
        :type nb_workers:               int
        :param spot_price:              The max price of the instances
        :type spot_price:               str|float
        :param machine_type:            The machine type you want (ex: 'm4.large')
        :type machine_type:             str
        :param ami_to_launch:           The ami id you want (ex: 'ami-cadetf')
        :type ami_to_launch:            str
        :param ebs_size:                The disk size on the machines
        :type ebs_size:                 int
        :param sec_groups:              A list of Ec2 security group ids
        :type sec_groups:               list[str]
        :param placement_group:         The name of the placement group (or None)
        :type placement_group:          str|None
        :return:                        The created instances and the number ofcpu per machine
        :rtype:                         Tuple[list[worker.Worker], int]
        """

        request_ids = []
        instance_id_list = []
        risc = False
        max_spot_bid = float(spot_price)
        launch_info = {
            "ImageId": ami_to_launch,
            "InstanceType": machine_type,
            "IamInstanceProfile": {"Name": "ec2_instance_autostop"},
            "EbsOptimized": False,
            "SecurityGroups": sec_groups,
            "Monitoring": {'Enabled': True},
            "BlockDeviceMappings": [{
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "DeleteOnTermination": True,
                    "VolumeSize": ebs_size,
                }}]
        }
        if placement_group:
            launch_info['Placement'] = {"GroupName": placement_group}
        try:
            risc = True
            res_info = self.conn.meta.client.request_spot_instances(
                SpotPrice=str(max_spot_bid),
                Type="one-time",
                InstanceCount=nb_workers,
                InstanceInterruptionBehavior="terminate",
                ValidUntil=datetime.datetime.utcnow() + datetime.timedelta(seconds=3600),
                LaunchSpecification=launch_info)
            if "SpotInstanceRequests" not in res_info.keys() or not res_info["SpotInstanceRequests"]:
                raise RuntimeError("Invalid AWS response: "+repr(res_info))
            risc = False
            request_ids = [r['SpotInstanceRequestId'] for r in res_info['SpotInstanceRequests']]
            instance_id_list = self._wait_spot_request(request_ids, 3600)
            instance_list = self._wait_for_instances_info(instance_id_list, 300)
            cpu_info = instance_list[0].cpu_options
            cpu_per_machine = cpu_info['CoreCount'] * cpu_info['ThreadsPerCore']
            worker_list = []
            for instance in instance_list:
                new_worker = worker.Worker(instance.id, instance.public_ip_address, instance.private_ip_address)
                cost = float(spot_price) * api_util.PRICE_PRECISION / 3600.0
                new_worker.set_specific_cost(cost, "dollar")
                worker_list.append(new_worker)
            return worker_list, cpu_per_machine
        except error_util.all_errors as e:
            with error_util.before_raising():
                if risc:
                    log.warning("Maybe some aws spot instance have beeing created and not cleaned")
                if request_ids:
                    if error_util.is_abort(e):
                        log.warning("Aws spot instance creation canceled, try to clean...")
                    else:
                        log.error("Error during aws spot instance creation, try to clean...")
                    try:
                        self._cleanup_spot_request(request_ids, instance_id_list)
                        log.info("workers cleaned successfully")
                    except error_util.abort_errors:
                        self._on_clean_error("Worker cleaned aborted.",
                                             "Aws spot instances clean up canceled. Please do it MANUALLY !!!", [])
                    except error_util.all_errors as e:
                        error_util.log_error(log, e)
                        self._on_clean_error("Worker cleaned failed.",
                                             "Unable to clean aws spot instances. Please do it MANUALLY !!!", [])

    def _cleanup_spot_request(self, request_ids, instance_id_list):
        self.conn.meta.client.cancel_spot_instance_requests(SpotInstanceRequestIds=request_ids)
        if instance_id_list:
            try:
                self.terminate_workers(instance_id_list)
            except Exception as e:
                log.warning("Minor error while cleaning failed spot request (1): " + str(e))
                log.exception(e)
        try:
            res_info = self.conn.meta.client.describe_spot_instance_requests(SpotInstanceRequestIds=request_ids)
            if "SpotInstanceRequests" not in res_info.keys() or not res_info["SpotInstanceRequests"]:
                raise RuntimeError("Invalid AWS response: " + repr(res_info))
            instance_id_list = []
            for info in res_info["SpotInstanceRequests"]:
                if "InstanceId" in info.keys():
                    instance_id_list.append(info["InstanceId"])
            if instance_id_list:
                try:
                    self.terminate_workers(instance_id_list)
                except Exception as e:
                    log.warning("Minor error while cleaning failed spot request (2): " + str(e))
                    log.exception(e)

        except Exception as e:
            log.warning("Minor error while cleaning failed spot request (3): " + str(e))
            log.exception(e)

    def _wait_spot_request(self, request_ids, timeout=3600):
        """
        Wait for spot request ids to be fulfilled, raise an Error on timeout
        A None or 0 timeout means we will wait forever

        :param request_ids:     The list of spot instance reservation request identifiers
        :type request_ids:      list[str]
        :param timeout:         How many time do we wait before raising an Error, in second. Optional, default 1h
        :type timeout:          int|float|datetime.timedelta|datetime.datetime|None
        :return:                The list of created instance ids
        :rtype:                 list[str]
        """
        if not request_ids:
            raise RuntimeError("Not request id provided")

        if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
            full_limit_date = None
            init_limit_date = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)
        elif isinstance(timeout, datetime.datetime):
            full_limit_date = timeout
            init_limit_date = min(full_limit_date, datetime.datetime.utcnow() + datetime.timedelta(seconds=30))
        else:
            if not isinstance(timeout, datetime.timedelta):
                timeout = datetime.timedelta(milliseconds=int(float(timeout) * 1000))
            full_limit_date = datetime.datetime.utcnow() + timeout
            init_limit_date = datetime.datetime.utcnow() + min(timeout, datetime.timedelta(seconds=30))
        res_info = None
        while datetime.datetime.utcnow() < init_limit_date:
            try:
                res_info = self.conn.meta.client.describe_spot_instance_requests(SpotInstanceRequestIds=request_ids)
                break
            except botocore.exceptions.ClientError:
                # We accept error for a short amount of time
                # because AWS request don't known our request id just after creation
                time.sleep(2)
        if not res_info:
            res_info = self.conn.meta.client.describe_spot_instance_requests(SpotInstanceRequestIds=request_ids)

        while full_limit_date is None or datetime.datetime.utcnow() < full_limit_date:
            if "SpotInstanceRequests" not in res_info.keys() or not res_info["SpotInstanceRequests"]:
                raise RuntimeError("Invalid AWS response: " + repr(res_info))
            instance_id_list = []
            for info in res_info["SpotInstanceRequests"]:
                if info["State"] == "open":
                    break
                elif info["State"] == "active":
                    instance_id_list.append(info["InstanceId"])
                elif info["State"] == "failed":
                    raise RuntimeError("Spot request failed: "+repr(info["State"]))
                else:
                    raise RuntimeError("Spot request failed with unknown status: " + str(info["State"]) + ":" +
                                       repr(info["Status"]))
            if len(instance_id_list) == len(request_ids):
                return instance_id_list
            time.sleep(10)
            res_info = self.conn.meta.client.describe_spot_instance_requests(SpotInstanceRequestIds=request_ids)
        raise RuntimeError("Unable to launch spot instances after "+str(timeout))


class DockerProvider(Provider):
    """
    Local docker manager
    """

    def __init__(self, conf, name, tmp_folder):
        location = conf.get("provider_"+name, "location")
        self._tag_file = os.path.join(tmp_folder, name+".tags")
        if not os.path.exists(tmp_folder):
            os.makedirs(tmp_folder)
        if not os.path.exists(self._tag_file):
            with open(self._tag_file, "w") as fh:
                fh.write(json.dumps({}))

        self._api_name = conf.get('general', 'api_name')
        self._server_name = conf.get('general', 'server')
        self._default_storage = conf.get("provider_"+name, 'default_storage')

        super(DockerProvider, self).__init__(name, location)

        self._key_name = conf.get("provider_"+name, 'key_name')
        self._key_path = os.path.join(API_PATH, "cloud_ssh_keys", self._key_name)
        self._root_key_name = conf.get("provider_"+name, 'root_key_name')
        self._root_key_path = os.path.join(API_PATH, "cloud_ssh_keys", self._root_key_name)

        self._current_docker_image = None
        self._current_docker_image_fetched = False

        self._image_id = self._get_image_id()
        if self._image_id is None:
            self._image_id = self._build_image()
            if self._image_id is None:
                raise RuntimeError("Unable to build docker image")

    def get_key_path(self, root=False):
        """
        Get the path of path of the ssh key to access to the workers

        :param root:    Do you want the ssh key of the root user. Optional, default False
        :type root:     bool
        :return:        The path of the ssh key to get access to the worker
        :rtype:         str|None
        """
        return self._root_key_path if root else self._key_path

    @property
    def type(self):
        return "docker"

    def get_default_storage_name(self):
        """
        Get the name of the default storage associated with this cloud provider (if any)
        :return:    A storage name or None
        :rtype:     str|None
        """
        return self._default_storage

    def list_workers(self):
        """
        Get the list of all running workers
        :return:                The list of workers
        :rtype:                 list[worker.Worker]
        """
        all_tags = self._load_tags()

        results = []
        cmd = ["docker", "ps", "-q",
               "-f", "label=aziugo_project=" + self._api_name,
               "-f", "label=provider=" + self.name,
               "-f", "label=app=worker_" + self._api_name]
        code, out, err = proc_util.run_cmd(cmd, cwd=API_PATH)
        for line in out.strip().splitlines():
            container_id = line.strip()
            try:
                cmd = ["docker", "inspect", "-f", "'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'",
                       container_id]
                _, ip_address, _ = proc_util.run_cmd(cmd)
            except RuntimeError:
                continue
            worker_obj = worker.Worker(container_id, None, ip_address.strip())
            worker_obj.set_creation_date(datetime.datetime.utcnow())
            worker_obj.set_status(worker.Worker.Status.RUNNING)
            if container_id in all_tags.keys():
                worker_obj.set_tags(all_tags[container_id])
            results.append(worker_obj)
        return results

    def create_workers(self, nb_workers=1, worker_group=None, **creation_options):
        """
        Create one or more worker machine instances
        :param nb_workers:          The number of workers to create. Optional, default 1
        :type nb_workers:           Int
        :param worker_group:        A specific WorkerGroup if you want all the worker to be
                                    created in the same place (usage example: clusters). Optional, default None
        :type worker_group:         DockerWorkerGroup|None
        :param creation_options:    A list of creation argument specific to the cloud we want.
                                         For docker the specif arguments are:
                                        'machine'        str, REQUIRED, The machine type you want. Ignored for now
        :type creation_options:     dict
        :return:                    The created instances
        :rtype:                     list[worker.Worker]
        """
        network_name = None
        current_docker_image = self._get_current_docker_image()

        # Get the Network configuration if current app is in a docker
        if current_docker_image is not None:
            cmd = ["docker", "inspect", current_docker_image, '-f', "{{json .NetworkSettings.Networks }}"]
            output = subprocess.check_output(cmd)
            try:
                network_config = json.loads(output)
            except StandardError:
                raise RuntimeError("Unable to get the network of the current container: invalid json: "+repr(output))
            if not network_config:
                raise RuntimeError("Unable to get the network of the current container: No network detected")
            network_name = network_config.keys()[0]

        # FIXME LATER: better implementation can re-enable this ?
        # Toolchain folder is disable because of target compilation
        mount_folder = None
        # mount_folder = os.path.join(API_PATH, "worker_scripts", "toolchain")

        container_id_list = []
        results = []
        try:
            shared_folder = None
            if worker_group:
                shared_folder = worker_group.get_volume_name()
            for i in range(nb_workers):
                container_id_list.append(self._run_container(network_name, mount_folder, shared_mount=shared_folder))

            for container_id in container_id_list:
                try:
                    cmd = ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                           container_id]
                    _, ip_address, _ = proc_util.run_cmd(cmd, shell=False)
                except StandardError as e:
                    log.warning(str(e))
                    continue
                if not ip_address:
                    log.warning("Unable to read ip address")
                    continue
                worker_obj = worker.Worker(container_id, None, ip_address.strip())
                worker_obj.set_creation_date(datetime.datetime.utcnow())
                worker_obj.set_status(worker.Worker.Status.RUNNING)
                results.append(worker_obj)
        except error_util.all_errors as e:
            with error_util.before_raising():
                if container_id_list:
                    if error_util.is_abort(e):
                        log.warning("Docker instance creation canceled, try to clean...")
                    else:
                        log.error("Error during docker instance creation, try to clean...")
                    try:
                        self.terminate_workers(container_id_list)
                        log.info("workers cleaned successfully")
                    except error_util.abort_errors:
                        msg = "docker instances clean up canceled. Please do it MANUALLY !!!"
                        log.warning(msg)
                        api_util.send_admin_email("Worker cleaned aborted.", msg +
                                                  "\nInstances: " + repr(container_id_list))
                    except error_util.all_errors as e:
                        msg = "Unable to clean docker instances. Please do it MANUALLY !!!"
                        log.error(msg)
                        error_util.log_error(log, e)
                        api_util.send_admin_email("Worker cleaned failed.", msg +
                                                  "\nInstances: " + repr(container_id_list))
        return results

    def generate_worker_group(self, job_id):
        """
        Create a WorkerGroup if you want all the worker to be created in the same place (usage example: clusters)
        :param job_id:      The id of the job we create this group for
        :type job_id:       int
        :return:            A new Worker group
        :rtype:             WorkerGroup
        """
        name = self._api_name + "/" + self._server_name + "/" + self.name + "/cluster_" + str(job_id)
        return DockerWorkerGroup(job_id, name)

    def terminate_workers(self, workers):
        """
        Stop worker machine instances
        :param workers:         The worker you want to stop
        :type workers:          list[worker.Worker]|list[str]
        """
        all_tags = self._load_tags()
        worker_id_list = []
        for worker_param in workers:
            worker_id = worker_param if type_util.is_string(worker_param) else worker_param.worker_id
            if worker_id in all_tags.keys():
                del all_tags[worker_id]
            worker_id_list.append(str(worker_id))
        if worker_id_list:
            cmd = ["docker", "container", "stop"]+worker_id_list
            proc_util.run_cmd(cmd)
            for worker_id in worker_id_list:
                child_proc = subprocess.Popen(["docker", "container", "rm", worker_id])
                if child_proc.poll() is None:
                    child_proc.wait()
        self._save_tags(all_tags)

    def tag_workers(self, workers, tags):
        """
        Add some tag to the worker instances if the could have tag capability, otherwise, do nothing
        :param workers:         The workers to tag
        :type workers:          list[worker.Worker]|list[str]
        :param tags:            values to tag
        :type tags:             dict[str:str]
        """
        all_tags = self._load_tags()
        for worker_param in workers:
            worker_id = worker_param if type_util.is_string(worker_param) else worker_param.worker_id
            if worker_id not in all_tags.keys():
                all_tags[worker_id] = {}
            all_tags[worker_id].update(tags)
            if "Name" in tags.keys():
                container_name = re.sub(r"\.+", ".", re.sub(r"[^a-zA-Z0-9_.-]+", ".", tags['Name']))
                subprocess.check_output(['docker', 'rename', worker_id, container_name])
        self._save_tags(all_tags)

    def list_artefacts(self):
        """
        List all artefacts created for worker groups

        :return:        The provider artefacts
        :rtype:         list[ProviderArtefact]
        """
        # List volumes
        prefix = self._api_name + "/" + self._server_name + "/" + self.name + "/cluster_"
        formatted_prefix = re.sub("_+", "_", re.sub("[^a-z0-9_]+", "_", prefix.lower()))

        cmd = ['docker', 'volume', 'ls', "-q"]
        output = subprocess.check_output(cmd, cwd=API_PATH, stderr=subprocess.PIPE)

        results = []
        for volume_name in output.strip().splitlines():
            if not volume_name.startswith(formatted_prefix):
                continue
            job_id_str = volume_name[len(formatted_prefix):]
            if not type_util.ll_int(job_id_str):
                log.warning("Invalid volume name: " + repr(volume_name))
                continue
            results.append(ProviderArtefact(self, "volume", volume_name, job_id=int(job_id_str)))
        return results

    def delete_artefact(self, artefact):
        """

        :param artefact:
        :type artefact:     ProviderArtefact
        """
        try:
            if artefact.type == "volume":
                self._del_volume(artefact.data)
            else:
                raise RuntimeError("Unknown artifact type " + str(artefact.type))
        except StandardError as e:
            log.warning("Unable to delete "+str(artefact)+": "+str(e))

    def get_startup_time(self):
        """
        Get the time needed to create an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        return datetime.timedelta(seconds=60)

    def get_shutdown_time(self):
        """
        Get the time needed to stop an instance

        :return:         the time needed to create an instance
        :rtype:          datetime.timedelta
        """
        return datetime.timedelta(seconds=30)

    def _del_volume(self, volume_name):
        cmd = ['docker', 'volume', 'rm', volume_name]
        subprocess.check_output(cmd, cwd=API_PATH, stderr=subprocess.PIPE)

    def _load_tags(self):
        """
        Load tags from tag file

        :return:    The tags dictionary, by docker container id
        :rtype:     dict[str, dict[str, any]]
        """
        if not os.path.exists(self._tag_file):
            self._save_tags({})
        try:
            with open(self._tag_file, "r") as fh:
                return json.load(fh)
        except StandardError:
            log.error("Docker tag file have been corrupted. Generated a cleaned one.")
            self._save_tags({})
            return {}

    def _save_tags(self, all_tags):
        """
        Save tags

        :param all_tags:    The tags dictionary, by docker container id
        :type all_tags:     dict[str, dict[str, any]]
        """
        with open(self._tag_file, "w") as fh:
            json.dump(all_tags, fh)

    def _get_current_docker_image(self):
        """
        Get the current docker container id if any

        :return:        The current docker container id if any, None otherwise
        :rtype:         str|None
        """
        if not self._current_docker_image_fetched:
            cgroups = subprocess.check_output(["cat", "/proc/self/cgroup"]).splitlines()
            for line in cgroups:
                if "docker" not in line:
                    continue
                fields = line.split(":", 3)
                if len(fields) < 2:
                    continue
                if not fields[2].startswith("/docker/"):
                    continue
                self._current_docker_image = fields[2][len("/docker/"):]
                break
            self._current_docker_image_fetched = True
        return self._current_docker_image

    def _get_image_id(self):
        """
        Get docker container id to launch

        :return:    The docker container id if found, else None
        :rtype:     str|None
        """

        cmd = ["docker", "images", "-q", "-a",
               "-f", "label=aziugo_project="+str(self._api_name),
               "-f", "label=provider="+str(self.name),
               "-f", "label=app=worker_"+str(self._api_name),
               "-f", "dangling=false"]
        output = subprocess.check_output(cmd)
        images = output.strip().splitlines()
        if images:
            return images[0].strip()
        return None

    def _build_image(self):
        """
        Build new worker container

        :return:    The docker container id
        :rtype:     str
        """
        cmd = ['docker', 'build', '.', '-f', 'docker_worker/Dockerfile',
               '--build-arg', "BUILD_API_NAME=" + str(self._api_name),
               '--build-arg', "PUBKEY_PATH=" + str("cloud_ssh_keys/"+self._key_name+".pub"),
               '--build-arg', "ROOT_PUBKEY_PATH=" + str("cloud_ssh_keys/" + self._root_key_name + ".pub"),
               '--build-arg', "PROVIDER_NAME=" + str(self.name),
               '--build-arg', "INSTALL_DEPS_SH_PATH=docker_worker/install_deps.sh",
               '--build-arg', "REQUIREMENTS_PATH=docker_worker/requirements.txt",
               '--build-arg', "SCRIPTS_PATH=src/worker",
               '--target', 'api_worker',
               "-t", "aziugo."+self._api_name+".worker:"+self.name]
        subprocess.check_call(cmd, cwd=API_PATH)
        return self._get_image_id()

    def _run_container(self, network_name=None, src_mount=None, shared_mount=None):
        """
        Launch a docker container

        :param network_name:        The name of the specific docker network. Option, default None
        :type network_name:         str|None
        :return:                    The new container id
        :rtype:                     str
        """
        image_id = self._image_id
        cmd = ['docker', 'run',
               '-e', "DOCKER_WORKER=1",
               "-e", "OMPI_MCA_btl_vader_single_copy_mechanism=none",
               "-e", "OMPI_MCA_blt=self,sm,tcp",
               "--cap-add=SYS_PTRACE"]
        if src_mount:
            real_src_mount = self._get_real_mount_path(src_mount)
            cmd.extend(["-v", real_src_mount+":/home/aziugo/worker_scripts/toolchain:ro"])
        if shared_mount:
            cmd.extend(["--mount", 'type=volume,src=' + shared_mount + ',dst=' + api_util.WORKER_WORK_PATH])
        if network_name:
            cmd.append('--network='+str(network_name))
        cmd.extend(['-d', str(image_id)])
        container_id = subprocess.check_output(cmd, cwd=API_PATH).strip()
        return container_id

    def _get_real_mount_path(self, mount_folder):
        """
        Get the real folder to mount for scripts.
        It's easy if the launcher is not a container,
        but otherwise we should look at the container mounting points to mount from real

        :param mount_folder:        The folder you want to mount
        :type mount_folder:         str
        :return:                    The folder to mount
        :rtype:                     str
        """
        current_docker_image = self._get_current_docker_image()
        if not current_docker_image:
            return mount_folder

        cmd = ["docker", "inspect", current_docker_image, '-f', "{{json .Mounts }}"]
        output = subprocess.check_output(cmd)
        try:
            mount_config = json.loads(output)
        except StandardError:
            raise RuntimeError("Unable to get the mount points of the container: invalid json: " + repr(output))
        if mount_config:
            mount_dest = ""
            mount_src = None
            for config in mount_config:
                if mount_folder.startswith(config["Destination"]) and len(config["Destination"]) > len(mount_dest):
                    mount_dest = config["Destination"]
                    mount_src = config["Source"]
            if mount_src:
                remaining_path = mount_folder[len(mount_dest):].lstrip("/").lstrip("\\")
                mount_folder = os.path.join(mount_src, *os.path.split(remaining_path))
        return mount_folder
