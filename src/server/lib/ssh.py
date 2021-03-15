# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import os
import subprocess
import time
import shlex
import contextlib
import json
import signal
import datetime

# Project specific libs
import util
import type_util
import error_util
from proc_util import shell_quote


class SshConnection(object):
    """ Utility class to manage an ssh connection to another computer
        Usage:
            from lib.ssh import SshConnection

            ssh_conn = SshConnection(ip, user)
            ssh_conn.ping()
            ssh_conn.run(["echo", "hello"])

        Note: You can run or copy files as another user, but only if your ssh user is a sudoer without password

    """
    # FIXME LATER: port this to Windows

    MAX_ATTEMPT = 3
    RETRY_DELAY = 100  # in ms
    SSH_ARGS = ['-q',
                '-F', '/dev/null',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'IdentitiesOnly=yes',
                '-o', 'BatchMode=yes'
                ]

    @staticmethod
    def unserialize(data):
        """
        Unserialize a connection object

        :param data:    The serialized connection
        :type data:     str|dict[str, str]
        :return:        The connection
        :rtype:         SshConnection
        """
        if type_util.is_json(data):
            data = json.loads(data)

        for field in ("ip", "user", "key_file"):
            if field not in data.keys():
                raise RuntimeError("Invalid ssh serialization, not field "+field+" defined")
        return SshConnection(data['ip'], data['user'], data["key_file"])

    def __init__(self, ip, user, key_file="id_rsa"):
        """
        Create an ssh connection
        Usage:
            ssh_conn = SshConnection(ip, user)

        :param ip:          The ip of the server, required
        :type ip:           str
        :param user:        The server user, required
        :type user:         str
        :param key_file:    Optional, the name of the private key file. Default: id_rsa
                            It should be located in $HOME/.ssh if not absolute
        :type key_file:     str
        """
        self._priv_key_path = str(key_file)
        if not os.path.exists(self._priv_key_path):
            user_home = os.path.expanduser('~')
            self._priv_key_path = str(os.path.join(user_home, ".ssh", key_file))
            if not os.path.exists(self._priv_key_path):
                raise RuntimeError("No "+self._priv_key_path + " found")
        self._ip = ip
        self._user = user
        if not user:
            raise RuntimeError("Invalid ssh user")
        if not ip:
            raise RuntimeError("Invalid ssh ip")

    def serialize(self):
        return json.dumps({'ip': self._ip, "user": self._user, "key_file": self._priv_key_path})

    @property
    def client_ip(self):
        return self._ip

    @property
    def client_user(self):
        return self._user

    def ping(self):
        """
        Try to establish a ssh connection. No multiple retry

        :return:    True if the ssh connection is established, False otherwise
        :rtype:     bool
        """
        try:
            cmd = ['ssh']
            cmd.extend(SshConnection.SSH_ARGS)
            cmd.extend(["-o", "ConnectTimeout=5"])
            cmd.extend(['-i', self._priv_key_path, self._user + "@" + self._ip])
            cmd.append("echo ssh_ping")

            new_env = os.environ.copy()
            new_env["LC_ALL"] = "en_US.UTF-8"
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, env=new_env)
            if not out.strip():
                return False
            if out.strip() != 'ssh_ping':
                raise RuntimeError("Strange output while pinging: " + out)
            return True
        except subprocess.CalledProcessError:
            return False

    def __nonzero__(self):
        return self.ping()

    def wait_for_connection(self, timeout=300, can_fail=False, delay=2000):
        """
        Try to connect using ssh during 'timeout' seconds

        :param timeout:         Timeout to connect, in seconds, default: 5 min
        :type timeout:          int|float|datetime.timedelta|datetime.datetime|None
        :param can_fail:        Should we skip if we can't connect, default: False
        :type can_fail:         bool
        :param delay:           Delay between attempts, in ms, default: 2 seconds
        :type delay:            int
        :return:                True if success, False if failure and can_fail=True, raise an exception otherwise
        :rtype:                 bool
        """
        if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
            time_limit = None
        elif isinstance(timeout, datetime.datetime):
            time_limit = timeout
        else:
            if not isinstance(timeout, datetime.timedelta):
                timeout = datetime.timedelta(milliseconds=int(float(timeout) * 1000))
            time_limit = datetime.datetime.utcnow() + timeout

        while True:
            if self.ping():
                return True
            if time_limit is not None and datetime.datetime.utcnow() > time_limit:
                if can_fail:
                    return False
                else:
                    raise RuntimeError("Unable to connect to " + self._ip + " after " + str(timeout))
            time.sleep(float(delay)/1000)

    def send_file(self, src, dest, mode=None, max_retry=None, delay=None, as_user=None):
        """
        Send a local file to the server
        Warning: this doesn't work for folders.

        :param src:         The file to send
        :type src:          str
        :param dest:        Where to place the file
        :type dest:         str
        :param mode:        The file mode (ex: 0o644), optional, default None
        :type mode:         int|None
        :param max_retry:   Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:    int|None
        :param delay:       The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:        int|None
        :param as_user:     run command as user, default None
        :type as_user:      str|None
        :return:            True in case of success, raise an exception otherwise
        :rtype:             bool
        """
        max_retry = max_retry if max_retry is not None else SshConnection.MAX_ATTEMPT
        delay = delay if delay is not None else SshConnection.RETRY_DELAY

        if not os.path.exists(src):
            raise RuntimeError("source file "+src+" doesn't exists, unable to send it to server "+self._ip)
        if os.path.isdir(src):
            raise RuntimeError(src + " is a folder, please use send_folder instead")

        cmd = "test -d '"+dest+"' && echo D || (test -f '"+dest+"' && echo F || echo N)"
        code, out, err = self.run(cmd, max_retry=max_retry, delay=delay, shell=True, as_user=as_user)
        out = out.strip()
        if out == "D":  # it's a folder on destination
            # if the dest name is not complete, we recall this method with the complete destination name
            return self.send_file(src, os.path.join(dest, os.path.basename(src)), mode=mode,
                                  max_retry=max_retry, delay=delay, as_user=as_user)

        if out == "F":  # it's a file on destination
            self.run(["rm", "-f", dest], max_retry=max_retry, delay=delay, as_user=as_user)
        elif out == "N":  # it doesn't exists on destination
            self.run(["mkdir", "-p", os.path.dirname(dest)], max_retry=max_retry, delay=delay, as_user=as_user)
        else:
            raise RuntimeError("Unknown testing response: "+str(out)+" stderr is "+repr(err))

        dest_file = dest if not as_user else self.run(["mktemp"], max_retry=max_retry, delay=delay)[1]
        dest_file = dest_file.strip()

        i = 0
        while True:
            try:

                cmd = ['scp']
                cmd.extend(SshConnection.SSH_ARGS)
                cmd.extend(['-i', self._priv_key_path])
                cmd.extend([src, self._user + "@" + self._ip + ":" + dest_file])
                new_env = os.environ.copy()
                new_env["LC_ALL"] = "en_US.UTF-8"
                subprocess.check_call(cmd, stderr=subprocess.STDOUT, env=new_env)
                if as_user:
                    self.run(["mv", dest_file, dest], max_retry=max_retry, delay=delay, as_user=as_user)
                if mode is not None:
                    self.run(["chmod", "{0:o}".format(mode), dest_file], max_retry=max_retry, delay=delay, as_user=as_user)
                self.run(["test", "-f", dest], max_retry=0, as_user=as_user)
                return True
            except (subprocess.CalledProcessError, RuntimeError):
                with error_util.saved_stack() as err:
                    i += 1
                    if i >= max_retry:
                        err.reraise()
                    time.sleep(float(delay) / 1000)

    def su_send_file(self, src, dest, max_retry=None, delay=None):
        """
        Send a local file to the server as root user
        Warning: this doesn't work for folders.

        :param src:         The file to send
        :type src:          str
        :param dest:        Where to place the file
        :type dest:         str
        :param max_retry:   Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:    int|None
        :param delay:       The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:        int|None
        :return:            True in case of success, raise an exception otherwise
        :rtype:             bool
        """
        return self.send_file(src, dest, max_retry, delay, as_user="root" if self._user != "root" else None)

    def send_folder(self, src, dest, max_retry=None, delay=None, as_user=None):
        """
        Send a local folder to the server

        :param src:         The file to send
        :type src:          str
        :param dest:        Where to place the folder
        :type dest:         str
        :param max_retry:   Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:    int|None
        :param delay:       The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:        int|None
        :param as_user:     run command as user, default None
        :type as_user:      str|None
        :return:            True in case of success, raise an exception otherwise
        :rtype:             bool
        """
        max_retry = max_retry if max_retry is not None else SshConnection.MAX_ATTEMPT
        delay = delay if delay is not None else SshConnection.RETRY_DELAY

        if not os.path.exists(src):
            raise RuntimeError("source folder "+src+" doesn't exists, unable to send it to server "+self._ip)
        if not os.path.isdir(src):
            raise RuntimeError(src + " is a file, please use send_file instead")

        code, out, err = self.run("test -d '"+dest+"' && echo D || (test -f '"+dest+"' && echo F || echo N)",
                                  max_retry=max_retry, delay=delay, shell=True, as_user=as_user)
        out = out.strip()
        if out == "F":  # it's a file on destination
            raise RuntimeError(dest + " is a file on target server "+self._ip+", it can't contains anything")

        if out == "N":  # it doesn't exists on destination
            self.run(["mkdir", "-p", os.path.dirname(dest)], max_retry=max_retry, delay=delay, as_user=as_user)
        else:  # out == "D":  it's a folder on destination
            self.run(["rm", "-rf", dest], max_retry=max_retry, delay=delay, as_user=as_user)

        dest_folder = dest if not as_user else self.run(["mktemp", "-d"], max_retry=max_retry, delay=delay)[1]
        dest_folder = dest_folder.strip()

        i = 0
        while True:
            try:
                cmd = ['scp', '-r']
                cmd.extend(SshConnection.SSH_ARGS)
                cmd.extend(['-i', self._priv_key_path])
                cmd.extend([src, self._user + "@" + self._ip + ":" + dest_folder])
                new_env = os.environ.copy()
                new_env["LC_ALL"] = "en_US.UTF-8"
                subprocess.check_call(cmd, stderr=subprocess.STDOUT, env=new_env)
                if as_user:
                    tmp_path = util.path_join(dest_folder, os.path.basename(dest))
                    self.run(["mv", tmp_path, dest], max_retry=max_retry, delay=delay, as_user=as_user)
                self.run(["test", "-d", dest], max_retry=0, as_user=as_user)
                return True
            except (subprocess.CalledProcessError, RuntimeError):
                with error_util.saved_stack() as err:
                    i += 1
                    if i >= max_retry:
                        err.reraise()
                    time.sleep(float(delay) / 1000)

    def su_send_folder(self, src, dest, max_retry=None, delay=None):
        """
        Send a local folder to the server as root user

        :param src:         The file to send
        :type src:          str
        :param dest:        Where to place the folder
        :type dest:         str
        :param max_retry:   Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:    int|None
        :param delay:       The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:        int|None
        :return:            True in case of success, raise an exception otherwise
        :rtype:             bool
        """
        return self.send_folder(src, dest, max_retry, delay, as_user="root" if self._user != "root" else None)

    def file_exists(self, remote_filename, max_retry=None, delay=None):
        """
        Check if filename exists on server.

        :param remote_filename: The file to check
        :type remote_filename:  str
        :param max_retry:       Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:        int|None
        :param delay:           The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:            int|None
        :return:                True in case of success, raise an exception otherwise
        :rtype:                 bool
        """
        max_retry = max_retry if max_retry is not None else SshConnection.MAX_ATTEMPT
        delay = delay if delay is not None else SshConnection.RETRY_DELAY

        cmd = "test -f '" + remote_filename + "' && echo F || echo N"
        code, out, err = self.run(cmd, max_retry=max_retry, delay=delay, shell=True)
        out = out.strip()
        return out == "F"

    def folder_exists(self, remote_filename, max_retry=None, delay=None):
        """
        Check if folder exists on server.

        :param remote_filename: The file to check
        :type remote_filename:  str
        :param max_retry:       Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:        int|None
        :param delay:           The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:            int|None
        :return:                True in case of success, raise an exception otherwise
        :rtype:                 bool
        """
        max_retry = max_retry if max_retry is not None else SshConnection.MAX_ATTEMPT
        delay = delay if delay is not None else SshConnection.RETRY_DELAY

        cmd = "test -d '" + remote_filename + "' && echo D || echo N"
        code, out, err = self.run(cmd, max_retry=max_retry, delay=delay, shell=True)
        out = out.strip()
        return out == "D"

    def get_file(self, remote_src, local_dest, max_retry=None, delay=None):
        """
        Get distant file and store it locally
        Warning: this doesn't work for folders.

        :param remote_src:      The file to fetch
        :type remote_src:       str
        :param local_dest:      Where to place the file locally
        :type local_dest:       str
        :param max_retry:       Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:        int|None
        :param delay:           The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:            int|None
        :return:                True in case of success, raise an exception otherwise
        :rtype:                 bool
        """
        max_retry = max_retry if max_retry is not None else SshConnection.MAX_ATTEMPT
        delay = delay if delay is not None else SshConnection.RETRY_DELAY

        cmd = "test -d '" + remote_src + "' && echo D || (test -f '" + remote_src + "' && echo F || echo N)"
        code, out, err = self.run(cmd, max_retry=max_retry, delay=delay, shell=True)
        out = out.strip()
        if out != "F":  # it's not a file
            raise RuntimeError(remote_src + " is not a file, unable to fetch it")

        if os.path.exists(local_dest):
            if os.path.isdir(local_dest):
                local_dest = os.path.join(local_dest, os.path.basename(remote_src))
        else:
            local_dest_folder = os.path.dirname(local_dest)
            if not os.path.exists(local_dest_folder):
                os.makedirs(local_dest_folder)
            elif os.path.isfile(local_dest_folder):
                raise RuntimeError(local_dest_folder+" is a file, unable to put data in "+local_dest)

        # FIXME LATER: implement for folders and for as_user
        i = 0
        while True:
            try:
                cmd = ['scp']
                cmd.extend(SshConnection.SSH_ARGS)
                cmd.extend(['-i', self._priv_key_path])
                cmd.extend([self._user + "@" + self._ip + ":" + remote_src, local_dest])
                new_env = os.environ.copy()
                new_env["LC_ALL"] = "en_US.UTF-8"
                subprocess.check_call(cmd, stderr=subprocess.STDOUT, env=new_env)
                return True
            except (subprocess.CalledProcessError, RuntimeError):
                with error_util.saved_stack() as err:
                    i += 1
                    if i >= max_retry:
                        err.reraise()
                    time.sleep(float(delay) / 1000)

    def run(self, cmd, max_retry=None, delay=None, can_fail=False, ensure_not_killed=False, shell=False, as_user=None):
        """
        Run a command on the server

        :param cmd:                 The command to execute
        :type cmd:                  str|list[str]
        :param max_retry:           Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:            int|None
        :param delay:               The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:                int|None
        :param can_fail:            Should we skip in case of failure ? default: False
                                    Warning: imply no retry or delay
        :type can_fail:             bool
        :param ensure_not_killed:   Ensure the process is not killed if the python session died, using nohup
        :type ensure_not_killed:    bool
        :param shell:               Do we want the command to be interpreted by a shell ? Default False
        :type shell:                bool
        :param as_user:             Run command as specific user, default None
        :type as_user:              str|None
        :return:                    return code, stdout, and stderr
                                    If the return code is greater than 256, it means we can't get the return code
                                    If the return code is negative, it's the number of the signal
        :rtype:                     Tuple[int, str, str]
        """
        max_retry = max_retry if max_retry is not None else SshConnection.MAX_ATTEMPT
        delay = delay if delay is not None else SshConnection.RETRY_DELAY

        i = 0
        while True:
            ssh_cmd = ['ssh']
            ssh_cmd.extend(SshConnection.SSH_ARGS)
            ssh_cmd.extend(['-i', self._priv_key_path, self._user + "@" + self._ip])
            if type(cmd) in (list, tuple) and shell:
                extended_cmd = " ".join(cmd)
            elif type(cmd) in (list, tuple):
                extended_cmd = " ".join(map(lambda x: shell_quote(x), cmd))
            elif shell:
                extended_cmd = cmd
            else:
                extended_cmd = " ".join(map(lambda x: shell_quote(x), shlex.split(cmd)))

            if ensure_not_killed:
                if shell:
                    extended_cmd = "nohup bash -c "+shell_quote(extended_cmd)+" </dev/null"
                else:
                    extended_cmd = "nohup "+extended_cmd+" </dev/null"

            if as_user:
                if shell and not ensure_not_killed:
                    extended_cmd = "sudo -u '" + as_user + "' bash -c " + shell_quote(extended_cmd) + " </dev/null"
                else:
                    extended_cmd = "sudo -u '" + as_user + "' " + extended_cmd

            ssh_cmd.append(extended_cmd)
            new_env = os.environ.copy()
            new_env["LC_ALL"] = "en_US.UTF-8"
            child_proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                          env=new_env)
            std_out, std_err = child_proc.communicate()
            ret_code = child_proc.returncode
            if ret_code is None:
                ret_code = child_proc.wait()
                if ret_code is None:
                    return 257, std_out, std_err
            if int(ret_code) == 0:
                return int(ret_code), std_out, std_err
            elif can_fail:
                return int(ret_code), std_out, std_err
            i += 1
            if i >= max_retry:
                raise subprocess.CalledProcessError(int(ret_code), ssh_cmd, std_out+std_err)
            time.sleep(delay / 1000)

    def su_run(self, cmd, max_retry=None, delay=None, can_fail=False, ensure_not_killed=False, shell=False):
        """
        Run a command on the server as root

        :param cmd:                 The command to execute
        :type cmd:                  str|list[str]
        :param max_retry:           Number of retry in case of failure, default: SshConnection.MAX_ATTEMPT
        :type max_retry:            int|None
        :param delay:               The sleep time before a new retry, in ms, default: SshConnection.RETRY_DELAY
        :type delay:                int|None
        :param can_fail:            Should we skip in case of failure ? default: False
                                    Warning: imply no retry or delay
        :type can_fail:             bool
        :param ensure_not_killed:   Ensure the process is not killed if the python session died, using nohup
        :type ensure_not_killed:    bool
        :param shell:               Do we want the command to be interpreted by a shell ? Default False
        :type shell:                bool
        :return:                    return code, stdout, and stderr
                                    If the return code is greater than 256, it means we can't get the return code
                                    If the return code is negative, it's the number of the signal
        :rtype:                     Tuple[int, str, str]
        """
        force_root = "root" if self._user != "root" else None
        return self.run(cmd, max_retry, delay, can_fail, ensure_not_killed, shell, as_user=force_root)

    def run_async(self, cmd, shell=False, as_user=None):
        """
        Run a detached command on the server

        :param cmd:                 The command to execute
        :type cmd:                  str|list[str]
        :param shell:               Do we want the command to be interpreted by a shell ? Default False
        :type shell:                bool
        :param as_user:             Run command as specific user, default None
        :type as_user:              str|None
        :return:                    The process created so you can wait for it or kill it
        :rtype:                     AsyncProc
        """
        ssh_cmd = ['ssh']
        ssh_cmd.extend(SshConnection.SSH_ARGS)
        ssh_cmd.extend(['-i', self._priv_key_path, self._user + "@" + self._ip])
        if type(cmd) in (list, tuple) and shell:
            extended_cmd = " ".join(cmd)
        elif type(cmd) in (list, tuple):
            extended_cmd = " ".join(map(lambda x: shell_quote(x), cmd))
        elif shell:
            extended_cmd = cmd
        else:
            extended_cmd = " ".join(map(lambda x: shell_quote(x), shlex.split(cmd)))

        core_cmd = extended_cmd
        if shell:
            extended_cmd = "nohup bash -c "+shell_quote(extended_cmd)+" >/dev/null 2>&1 </dev/null & echo $!"
        else:
            extended_cmd = "nohup "+extended_cmd+" >/dev/null 2>&1 </dev/null & echo $!"

        if as_user:
            extended_cmd = "sudo -u '"+as_user+"' "+extended_cmd

        ssh_cmd.append(extended_cmd)
        new_env = os.environ.copy()
        new_env["LC_ALL"] = "en_US.UTF-8"
        child_proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
        std_out, std_err = child_proc.communicate()
        ret_code = child_proc.returncode
        if ret_code is None:
            ret_code = child_proc.wait()
            if ret_code is None:
                ret_code = 257
        if int(ret_code) != 0:
            raise RuntimeError("Unable to launch command: "+str(std_out)+str(std_err))
        pid = int(str(std_out).strip())
        return AsyncProc(pid, core_cmd, self)

    def su_run_async(self, cmd, shell=False):
        """
        Run a detached command on the server as root

        :param cmd:                 The command to execute
        :type cmd:                  str|list[str]
        :param shell:               Do we want the command to be interpreted by a shell ? Default False
        :type shell:                bool
        :return:                    The process created so you can wait for it or kill it
        :rtype:                     subprocess.Popen
        """
        return self.run_async(cmd, shell, as_user="root" if self._user != "root" else None)

    @contextlib.contextmanager
    def send_file_pipe(self, output_file, as_user=None):
        dest = output_file
        code, out, err = self.run("test -d '"+dest+"' && echo D || (test -f '"+dest+"' && echo F || echo N)",
                                  shell=True, as_user=as_user)
        out = out.strip()
        if out == "F":  # it's a file on destination
            raise RuntimeError(dest + " is a file on target server "+self._ip+", it can't contains anything")
        if not os.path.dirname(dest):
            raise RuntimeError(dest + " should be an absolute path")

        if out == "N":  # it doesn't exists on destination
            self.run(["mkdir", "-p", os.path.dirname(dest)], as_user=as_user)
        else:  # out == "D":  it's a folder on destination
            self.run(["rm", "-rf", dest], as_user=as_user)

        dest_folder = dest if not as_user else self.run(["mktemp", "-d"])[1]
        dest_folder = dest_folder.strip()

        cmd = ['ssh']
        cmd.extend(SshConnection.SSH_ARGS)
        cmd.extend(['-i', self._priv_key_path])
        cmd.extend([self._user + "@" + self._ip, 'cat > "' + dest + '"'])
        new_env = os.environ.copy()
        new_env["LC_ALL"] = "en_US.UTF-8"
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, env=new_env)
        yield proc.stdin

    @contextlib.contextmanager
    def read_file_pipe(self, src_file, as_user=None):
        code, out, err = self.run("test -d '" + src_file + "' && echo D || (test -f '" + src_file + "' && echo F || echo N)",
                                  shell=True, as_user=as_user)
        out = out.strip()
        if out != "F":  # it's a file on destination
            raise RuntimeError(src_file + " doesn't exists")

        cmd = ['ssh']
        cmd.extend(SshConnection.SSH_ARGS)
        cmd.extend(['-i', self._priv_key_path])
        cmd.extend([self._user + "@" + self._ip, 'cat "' + src_file + '"'])
        new_env = os.environ.copy()
        new_env["LC_ALL"] = "en_US.UTF-8"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=new_env)
        yield proc.stdout

    def get_file_size(self, file_path, as_user=None):
        code, out, err = self.run(['stat', '--printf=%s', file_path], as_user=as_user)
        if code != 0 or not type_util.ll_int(out.strip()):
            raise IOError("Unable to read the file size: "+str(out)+", "+str(err))
        return int(out.strip())

    def get_file_creation_date(self, file_path, as_user=None):
        code, out, err = self.run(['stat', '--printf=%W', file_path], as_user=as_user)
        if code != 0 or not type_util.ll_int(out.strip()):
            raise IOError("Unable to read the file size: "+str(out)+", "+str(err))
        if int(out.strip()) == 0:
            code, out, err = self.run(['stat', '--printf=%Y', file_path], as_user=as_user)
            if code != 0 or not type_util.ll_int(out.strip()):
                raise IOError("Unable to read the file size: " + str(out) + ", " + str(err))
        return datetime.datetime.utcfromtimestamp(int(out.strip()))

    def get_file_md5(self, file_path, as_user=None):
        code, out, err = self.run(['md5sum', file_path], as_user=as_user)
        if code != 0 or not out.strip():
            raise IOError("Unable to read the file md5: "+str(out)+", "+str(err))
        return str(out).split()[0]

    def gess_type(self, file_path, as_user=None):
        code, out, err = self.run(['file', '-b', '--mime-type', file_path], as_user=as_user)
        if code != 0 or not out.strip():
            return None
        return out.strip()

    def get_file_slice(self, file_path, offset, size):
        curl_cmd = ["curl", "-k", '-r', str(offset)+"-"+str(offset+size)]
        curl_cmd.extend(['-u', self._user+":"])
        curl_cmd.extend(['--key', self._priv_key_path, "--pubkey", self._priv_key_path + ".pub"])
        curl_cmd.extend(["sftp://"+self._ip+"/"+file_path])

        new_env = os.environ.copy()
        new_env["LC_ALL"] = "en_US.UTF-8"

        child_proc = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                      env=new_env)
        std_out, std_err = child_proc.communicate()
        ret_code = child_proc.returncode
        if ret_code is None:
            ret_code = child_proc.wait()
            if ret_code is None:
                raise RuntimeError("Unable to get file slice: "+str(std_out)+", "+str(std_err))
        if int(ret_code) == 0:
            return std_out
        else:
            raise RuntimeError("Unable to get file slice: " + str(std_out) + ", " + str(std_err))

    def __eq__(self, other):
        """
        Compare two connections

        :param other:   Other object to compare with
        :type other:    SshConnection|any
        :return:        True if 'other' param is equivalent to this one
        :rtype:         bool
        """
        if not isinstance(other, SshConnection):
            return False
        if self._priv_key_path != other._priv_key_path:
            return False
        if self._ip != other._ip:
            return False
        if self._user != other._user:
            return False
        return True


class AsyncProc(object):
    def __init__(self, pid, command, conn):
        """
        Represent an async distant processus

        :param pid:         The pid of the proc
        :type pid:          int
        :param command:     The launched command
        :type command:      str
        :param conn:        The connection to the distant machine
        :type conn:         SshConnection
        """
        super(AsyncProc, self).__init__()
        self._pid = pid
        self._command = command
        self._conn = conn

    def is_running(self):
        return self._conn.folder_exists("/proc/" + str(self._pid))

    def is_distant(self):
        return True

    @property
    def pid(self):
        return self._pid

    @property
    def returncode(self):
        return None

    def poll(self):
        return None

    def communicate(self, input=None):
        return (None, None)

    def wait(self):
        self._conn.run(["wait", str(self._pid)], can_fail=True)
        return None

    def terminate(self):
        self._conn.run(["kill", str(self._pid)], can_fail=True)

    def kill(self):
        self.send_signal(signal.SIGKILL)

    def send_signal(self, send_signal):
        self._conn.run(["kill", "-s", str(send_signal), str(self._pid)], can_fail=True)

    def stdin(self):
        return None

    def stdout(self):
        return None

    def stderr(self):
        return None

    def __str__(self):
        return "<AsyncProc (pid:"+str(self._pid)+")>"
