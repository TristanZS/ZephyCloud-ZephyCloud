#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import uuid
import time
import os
import subprocess
import logging
import copy

# Project libs
from lib import ssh
from lib import file_util
from lib import error_util
from lib import proc_util
from lib import async_util
from lib import type_util
import api_util


log = logging.getLogger("aziugo")


class Cluster(object):
    """
    Aws cluster
    Usage:
        form provider import AwsProvider
        from cluster import Cluster
        from ssh import SshConnection

        provider = AwsProvider('cn')
        with Cluster(provider, machine="m4.large") as cluster:
            ssh_conn = SshConnection(ip=cluster.ip, user=cluster.user)
            ssh_conn.run(["do", "mayages"])

            cluster.add_slaves(2)
            ssh_conn.run(["launch", "compute"])
    """

    # --------------------------------------- Public section section ---------------------------------------------------

    def __init__(self, provider, ssh_user, nbr_cores, job_id=None, tags=None,
                 _debug_no_terminate=False, **creation_options):
        """
        Create a cluster, reserving master instance and initialising it
        Warning: this method can be really long

        :param provider:                The cloud were the cluster should be created
        :type provider:                 provider.Provider
        :param job_id:                  The job id, used for logs and tagging, Optional
        :type job_id:                   str|None
        :param _debug_no_terminate:     Tell the cluster to never kill the instances. Optional, default False
        :type _debug_no_terminate:      bool
        :param creation_options:        The workers creation options> See Cloud.create_workers for more details
        :type creation_options:         any
        """
        self._job_id = str(job_id) if job_id else uuid.uuid4().hex
        self._provider = provider
        self._master = None
        self._slaves = []
        self._user = ssh_user
        self._root_key = provider.get_key_path(root=True)
        self._user_key = provider.get_key_path(root=False)
        self._cluster_pubkey = None
        self._cluster_privkey = None
        self._creation_options = creation_options
        self._cluster_inited = False
        self._no_clean = _debug_no_terminate
        self._worker_group = None
        self._worker_cores = nbr_cores
        self._tags = tags if tags else {}

    def init(self):
        try:
            self._worker_group = self._provider.generate_worker_group(self.job_id)
            self._worker_group.init()
            self._add_master()
        except error_util.all_errors:
            with error_util.before_raising():
                self.clean()

    def add_slaves(self, nbr_slaves):
        """
        Create X slave instances, initialize them and then finalize the master configuration.
        This method can be called multiple times, and is exception-safe
        Warning: this method can be really long, especially with spot instances

        :param nbr_slaves:      The number of slaves computer you want the cluster to create
        :type nbr_slaves:       int
        """
        self._init_cluster()
        new_workers = self._provider.create_workers(nbr_slaves, worker_group=self._worker_group,
                                                    **self._creation_options)
        try:
            slave_index = len(self._slaves)
            for worker in new_workers:
                tags = {}
                for key, val in self._tags.items():
                    if key.startswith("%master%_"):
                        continue
                    if key.startswith("%slave%_"):
                        key = key[len("%slave%_"):]
                    if type_util.is_string(val):
                        tags[key] = val.replace("%slave_index%", str(slave_index+1))
                    else:
                        tags[key] = val
                self._provider.tag_workers([worker], tags)
                slave_index += 1
            self._prepare_slaves_instances(new_workers)
            self._allow_slave_ssh_hosts(new_workers)
            self._update_openfoam_config(new_workers)
        except error_util.all_errors:
            with error_util.before_raising():
                if not self._no_clean or not new_workers:
                    self._try_cleaning(new_workers)
        # finally, all works fine, so we can save the new information
        self._slaves.extend(new_workers)

    @property
    def job_id(self):
        """
        :return:    The job id, used for log and tags
        :rtype:     str
        """
        return self._job_id

    @property
    def master_id(self):
        """
        :return:    The id of the master
        :rtype:     str|None
        """
        if not self._master:
            return None
        return self._master.worker_id

    @property
    def name(self):
        """
        :return:    The cluster name
        :rtype:     str
        """
        return "cluster_"+self.job_id

    @property
    def ip(self):
        """
        :return:    The public ip of the master instance
        :rtype:     str
        """
        return self._master.public_ip if self._master.public_ip else self._master.private_ip

    @property
    def nbr_instances(self):
        """
        :return:    The number of instances created
        :rtype:     int
        """
        return 1+len(self._slaves)

    @property
    def user_home(self):
        """
        :return:    The home folder on instances
        :rtype:     str
        """
        return api_util.WORKER_HOME

    @property
    def user(self):
        """
        :return:    The user name on instances
        :rtype:     str
        """
        return self._user

    @property
    def work_folder(self):
        """
        :return:    The folder of OpenFOAM
        :rtype:     str
        """
        return api_util.WORKER_WORK_PATH

    @property
    def machines_file_path(self):
        """
        :return:    File path of the 'machines' file, used by openfoam, should be in openfoam work folder or user home
        :rtype:     str
        """
        return os.path.join(self.user_home, "machines")

    @property
    def workers(self):
        """
        :return:    The list of workers, with the master at first position
        :rtype:     list[worker.Worker]
        """
        return [self._master] + self._slaves

    def add_tags(self, tags, master_only=False, slaves_only=False):
        """
        Add additional tags to aws instances
        :param tags:            A list of tag_name:tag_value to add to instances
        :type tags:             dict[str, str]
        :param master_only:     Tag only the master, Optional, default: False
        :type master_only:      bool
        :param slaves_only:     Tag only slaves, optional, default: False
        :type slaves_only:      bool
        """
        if slaves_only and master_only:
            raise RuntimeError("Can't tags master only and slave only at the same time")

        workers_to_tag = []
        if not slaves_only:
            workers_to_tag.append(self._master)
        if not master_only:
            workers_to_tag.extend(self._slaves)
        self._provider.tag_workers(workers_to_tag, tags)

    def clean(self):
        """
        Release cloud instances, remove security group and placement group on aws, and clean temporary files
        """
        if self._no_clean:
            log.debug("Cluster cleaning is disabled for debug purpose")
            return
        workers = [self._master]
        workers.extend(self._slaves)
        try:
            self._provider.terminate_workers(workers)
        except error_util.all_errors as e:
            error_util.log_error(log, e)
        self._master = None
        self._slaves = []
        if self._worker_group:
            try:
                self._worker_group.clean()
            except error_util.all_errors as e:
                error_util.log_error(log, e)

    def disable_clean(self):
        self._no_clean = True

    def get_connections(self):
        """
        Get an ssh connection to each worker (master and slaves) of this cluster

        :return:        A list of ssh connection to each worker
        :rtype:         list[lib.ssh.SshConnection]
        """
        ip_list = [self._master.public_ip if self._master.public_ip else self._master.private_ip]
        for slave in self._slaves:
            ip_list.append(slave.public_ip if slave.public_ip else slave.private_ip)
        connections = []
        for ip in ip_list:
            connections.append(ssh.SshConnection(ip, self._user, self._user_key))
        return connections

    # --------------------------------------- Protected section --------------------------------------------------------

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean()

    def _add_master(self):
        """
        Create master master instance and initialising it
        Warning: this method can be really long
        """
        new_workers = []
        try:
            new_workers = self._provider.create_workers(1, self._worker_group, **self._creation_options)
            self._master = new_workers[0]
            tags = {}
            for key, val in self._tags.items():
                if key.startswith("%slave%_"):
                    continue
                if key.startswith("%master%_"):
                    key = key[len("%master%_"):]
                tags[key] = val
            self._provider.tag_workers(new_workers, tags)
        except error_util.all_errors:
            with error_util.before_raising():
                if new_workers:
                    self._try_cleaning(new_workers)

    def _init_cluster(self):
        if self._cluster_inited:
            return
        self._generate_ssh_key()
        self._prepare_master()
        self._cluster_inited = True

    def _try_cleaning(self, new_workers):
        try:
            self._provider.terminate_workers(new_workers)
        except error_util.abort_errors:
            try:
                self._provider.terminate_workers(new_workers)
            except error_util.abort_errors:
                log.warning("Worker cleaned aborted.")
                msg = "Workers of job " + str(self._job_id) + " are not killed. Please kill them manually"
                api_util.send_admin_email("Worker cleaned aborted.", msg)
                log.error(msg)
        except error_util.all_errors as e:
            log.error("Workers of job " + self._job_id + " are not killed. Please kill them manually")
            error_util.log_error(log, e)

    def _generate_ssh_key(self):
        """
        Protected, Generate an ssh key, cluster specific, to allow cluster communication, and save public key content
        in the cluster object for further usage
        """
        with file_util.temp_folder() as folder:
            key_file_path = os.path.join(folder, "id_rsa_cluster")
            _ = subprocess.check_output(["ssh-keygen", "-q",
                                         "-N", "",
                                         "-t", "rsa",
                                         "-b", "4096",
                                         "-C", 'cluster_'+self._worker_group.get_name(),
                                         "-f", key_file_path], stderr=subprocess.PIPE)
            with open(key_file_path, 'r') as content_file:
                self._cluster_privkey = content_file.read()
            with open(key_file_path+".pub", 'r') as content_file:
                self._cluster_pubkey = content_file.read()

    def _prepare_slaves_instances(self, workers):
        """
        Launch all the instances initialisation in parallel (using sub-processes) and kill them all if one fail

        :param workers:             The details of the instances to prepare
        :type workers:              list[worker.Worker]
        """
        running_threads = set([])
        all_threads = set([])

        # starting sub-process for parallel instance initialisation
        slave_index = len(self._slaves)
        for worker in workers:
            slave_ip = worker.public_ip if worker.public_ip else worker.private_ip
            slave_initializer_thread = _SlaveInitializer(self, slave_ip, slave_index)
            running_threads.add(slave_initializer_thread)
            all_threads.add(slave_initializer_thread)
            slave_initializer_thread.start()
            slave_index += 1

        failed_thread = None
        # waiting for all process to finish or for the first to fail
        while failed_thread is None and len(running_threads) > 0:
            time.sleep(0.1)
            for thread in copy.copy(running_threads):
                if thread.is_alive():
                    continue
                running_threads.discard(thread)
                if not thread.succeed() != 0:
                    log.error("Slave initialization failed with exit code " + str(thread.get_exception()))
                    failed_thread = thread
                    break

        if failed_thread is not None:
            failed_thread.reraise()

        for thread in all_threads:
            thread.join()

    def _prepare_master(self):
        """
        Protected, Prepare the master instance, installing ssh keys, updating software and preparing nfs share folder
        """
        try:
            ssh_conn = ssh.SshConnection(self.ip, "root", self._root_key)
            try:
                log.info("Waiting for master to be ready")
                ssh_conn.wait_for_connection()
            except error_util.abort_errors: raise
            except error_util.all_errors as e:
                raise RuntimeError("Unable to connect to master instance (ip = " + self.ip + "): "+e.message)
            log.info("Start cluster master initialization")

            ssh_conn.run(["mkdir", "-p", self.work_folder])
            ssh_conn.run(["chown", "-R", self.user+":"+self.user, self.work_folder])

            # SSh config
            ssh_conn.run(["mkdir", "-p", self.user_home + "/.ssh"])
            user_auth_file = self.user_home + "/.ssh/authorized_keys"
            ssh_conn.run(["sed", "-i", "/cluster_/d", user_auth_file])
            ssh_conn.run("echo '' >> " + proc_util.shell_quote(user_auth_file), shell=True)
            ssh_conn.run("echo " + proc_util.shell_quote(self._cluster_pubkey) + " >> " +
                         proc_util.shell_quote(user_auth_file), shell=True)
            with file_util.temp_file(self._cluster_privkey) as priv_key:
                ssh_conn.send_file(priv_key, self.user_home + "/.ssh/id_rsa")
            with file_util.temp_file(self._cluster_pubkey) as pub_key:
                ssh_conn.send_file(pub_key, self.user_home + "/.ssh/id_rsa.pub")
            ssh_conn.run(["chmod", "600", self.user_home + "/.ssh/id_rsa"])
            ssh_conn.run(["chmod", "644", self.user_home + "/.ssh/id_rsa.pub"])
            ssh_conn.run(["chown", "-R", self.user + ":" + self.user, self.user_home + "/.ssh"])

            if self._provider.type == "docker":
                return  # no need for this
            ssh_conn.run(["sed", "-i", "/"+self.work_folder.replace("/", "\\/")+"/d", '/etc/exports'])
            ssh_conn.run(["sh", "-c", "echo '"+self.work_folder+"  *(rw,sync,no_subtree_check)' >> /etc/exports"])
            ssh_conn.run("exportfs -ra")
            ssh_conn.run("service nfs-kernel-server start")
            ssh_conn.run("echo '"+str(self.ip) + "' > '" + self.machines_file_path + "'", shell=True)
            log.info("Master initialized")
        except error_util.abort_errors: return
        except error_util.all_errors as e:
            with error_util.before_raising():
                error_util.log_error(log, e)

    def _prepare_slave(self, slave_ip, slave_index):
        """
        Protected, Prepare the slave instance, allowing ssh access, updating software and mounting nfs share folder

        :param slave_ip:         The public ip of the slave to prepare, used to establish ssh connection
        :type slave_ip:          str
        :param slave_index:      The index of the new slave (used for logs)
        :type slave_index:       int
        """
        try:
            ssh_conn = ssh.SshConnection(slave_ip, "root", self._root_key)
            try:
                ssh_conn.wait_for_connection()
            except error_util.abort_errors: raise
            except error_util.all_errors as e:
                raise RuntimeError("Unable to connect to slave instance (ip = " + self.ip + "): "+e.message)
            log.info("Start slave " + str(slave_index + 1) + " initialisation")

            ssh_conn.run(["umount", self.work_folder], can_fail=True)
            ssh_conn.run(["mkdir", "-p", self.work_folder])
            ssh_conn.run(["chown", "-R", self.user + ":" + self.user, self.work_folder])

            # SSh config
            ssh_conn.run(["mkdir", "-p", self.user_home + "/.ssh"])
            user_auth_file = self.user_home + "/.ssh/authorized_keys"
            ssh_conn.run(["sed", "-i", "/cluster_/d", user_auth_file])
            ssh_conn.run("echo '' >> " + proc_util.shell_quote(user_auth_file), shell=True)
            ssh_conn.run("echo " + proc_util.shell_quote(self._cluster_pubkey) + " >> " +
                         proc_util.shell_quote(user_auth_file), shell=True)
            with file_util.temp_file(self._cluster_privkey) as priv_key:
                ssh_conn.send_file(priv_key, self.user_home + "/.ssh/id_rsa")
            with file_util.temp_file(self._cluster_pubkey) as pub_key:
                ssh_conn.send_file(pub_key, self.user_home + "/.ssh/id_rsa.pub")
            ssh_conn.run(["chmod", "600", self.user_home + "/.ssh/id_rsa"])
            ssh_conn.run(["chmod", "644", self.user_home + "/.ssh/id_rsa.pub"])
            ssh_conn.run(["chown", "-R", self.user + ":" + self.user, self.user_home + "/.ssh"])

            if self._provider.type == "docker":
                return  # no need for this
            master_ip = self._master.private_ip if self._master.private_ip else self._master.public_ip
            ssh_conn.run(["find", self.work_folder, "-mindepth", "1", "-delete"])
            ssh_conn.run(["mount", "-t", "nfs", master_ip+":"+self.work_folder, self.work_folder])
            log.info("Slave "+str(slave_index+1)+" initialized")
        except error_util.abort_errors: return
        except error_util.all_errors as e:
            with error_util.before_raising():
                log.error("Slave "+str(slave_index+1)+" initialisation failed: " + str(e))

    def _allow_slave_ssh_hosts(self, workers):
        """
        Protected, ensure the master instance can establish ssh connection to the new slaves smoothly

        :param workers:         The details of the instances to prepare
        :type workers:          list[worker.Worker]
        """
        new_private_ips = map(lambda x: x.private_ip if x.private_ip else x.public_ip, workers)
        ssh_conn = ssh.SshConnection(self.ip, "root", self._root_key)
        # adding new instance ssh identity to allow smooth ssh connection from master
        for private_ip in new_private_ips:
            ssh_conn.run(["touch", "/root/.ssh/known_hosts"])
            ssh_conn.run(["ssh-keygen", "-R", private_ip])
            ssh_conn.run("ssh-keyscan -H '" + private_ip + "' >> '/root/.ssh/known_hosts'", shell=True)

        ssh_conn = ssh.SshConnection(self.ip, self._user, self._user_key)
        # adding new instance ssh identity to allow smooth ssh connection from master
        for private_ip in new_private_ips:
            ssh_conn.run(["touch", self.user_home + "/.ssh/known_hosts"])
            ssh_conn.run(["ssh-keygen", "-R", private_ip])
            ssh_conn.run("ssh-keyscan -H '" + private_ip + "' >> '" + self.user_home + "/.ssh/known_hosts'", shell=True)

    def _update_openfoam_config(self, new_workers):
        """
        Protected, Generate a new instance list on the master instance for OpenFoam to use it

        :param new_workers:         The details of the instances to prepare
        :type new_workers:          list[worker.Worker]
        """

        machines_file_content = str(self._master.private_ip if self._master.private_ip else self._master.public_ip)
        machines_file_content += " slots="+str(self._worker_cores - 1)+" max-slots="+str(self._worker_cores - 1)+"\n"
        for worker in self._slaves:
            machines_file_content += str(worker.private_ip if worker.private_ip else worker.public_ip)
            machines_file_content += " slots=" + str(self._worker_cores) + " max-slots=" + str(self._worker_cores)+"\n"
        for worker in new_workers:
            machines_file_content += str(worker.private_ip if worker.private_ip else worker.public_ip)
            machines_file_content += " slots=" + str(self._worker_cores) + " max-slots=" + str(self._worker_cores)+"\n"

        ssh_conn = ssh.SshConnection(self.ip, "root", self._root_key)
        with file_util.temp_file(machines_file_content) as machine_file:
            ssh_conn.send_file(machine_file, self.machines_file_path)
        ssh_conn.run(["chmod", "644", self.machines_file_path])
        ssh_conn.run("sync")


class _SlaveInitializer(async_util.AbstractThread):
    def __init__(self, cluster, slave_ip, slave_index):
        super(_SlaveInitializer, self).__init__()
        self._cluster = cluster
        self._slave_ip = slave_ip
        self._slave_index = slave_index

    def work(self):
        cluster = self._cluster
        cluster._prepare_slave(self._slave_ip, self._slave_index)
