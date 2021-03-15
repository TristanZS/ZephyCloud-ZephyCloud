#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This file provide utilities to manage ssh connections to a server
It try to manage user ssh config, local keys, etc...
It doesn't manage connection errors and auto-retry

Example:
>> ssh_params = SshParams("my.domain", login="my_user")
>> with secure_shell.using_ssh(ssh_params) as ssh:
>>     ssh.run("echo 'hello world'")
"""

# Core libs
import contextlib
import logging
import getpass
import os
import socket
import sys
import tempfile
import tarfile
import time
import warnings
import platform
import subprocess

# Third party libs
import paramiko
from paramiko.py3compat import u
import cryptography.utils

# Project specific files
import project_util


# We can remove this with the next paramiko version
warnings.filterwarnings("ignore", category=cryptography.utils.CryptographyDeprecationWarning)


@contextlib.contextmanager
def using_interactive_ssh(params, save_passphrase=True, wait_for_connection=False):
    """
    Start ssh connection.
    It will ask for passphrase and can optionally wait for connection
    It yields the connection to ensure connection closing

    :param params:                  Ssh connection parameters
    :type params:                   SshParams
    :param save_passphrase:         Do we want to save passphrase inside the SshParam instance
                                    after success. Optional, default True
    :type save_passphrase:          bool
    :param wait_for_connection:     Do we loop until the server open it's ssh port ? Optional, default False
    :type wait_for_connection:      bool
    :return:                        The ssh connection
    :rtype:                         InteractiveSsh
    """
    ssh = None
    try:
        ssh = paramiko.client.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        ssh.load_system_host_keys()
        passphrase = params.passphrase

        while True:
            try:
                ssh.connect(params.domain, params.port, params.login, password=params.password,
                            key_filename=params.key, passphrase=passphrase, look_for_keys=False)
                if save_passphrase:
                    params.passphrase = save_passphrase
                break
            except paramiko.ssh_exception.NoValidConnectionsError:
                exc_info = sys.exc_info()
                if wait_for_connection:
                    time.sleep(1)
                else:
                    raise exc_info[0], exc_info[1], exc_info[2]
            except paramiko.ssh_exception.BadHostKeyException as e:
                sys.stderr.write("Host key for server " + str(params.domain) + " has changed" + os.linesep)
                raise e
            except paramiko.SSHException as e:
                if is_passphrase_error(e):
                    if passphrase:
                        sys.stderr.write(os.linesep+"Bad passphrase !"+os.linesep)
                        sys.stderr.flush()
                    try:
                        passphrase = getpass.getpass("Key passphrase (for " + params.key + "): ")
                    except EOFError:
                        raise KeyboardInterrupt()
                else:
                    raise RuntimeError("Unable to establish ssh connection: " + str(e))
        conn = InteractiveSsh(ssh, params, passphrase)
        yield conn
    finally:
        if ssh:
            ssh.close()


@contextlib.contextmanager
def using_ssh_transport(domain, port=22):
    """
    Start an ssh transport connection
    It yields the ssh transport

    :param domain:      The domain to connect to
    :type domain:       str
    :param port:        The port to connect to. Optional, default 22
    :type port:         int
    :return:            The transport connection
    :rtype:             paramiko.Transport
    """
    real_domain = get_fqdn_from_domain(domain)
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((real_domain, port))
        transport = paramiko.Transport(sock)
        transport.start_client()

        yield transport
    finally:
        if sock:
            sock.close()


def check_connection(ssh_params):
    """
    Check we succeeds to connect to a server

    :param ssh_params:      The ssh connection parameters
    :type ssh_params:       SshParams
    :return:                The connection success or failure
    :rtype:                 bool
    """
    try:
        with using_interactive_ssh(ssh_params) as conn:
            if not conn.ping():
                return False
    except (KeyboardInterrupt, SystemExit): raise
    except:
        return False
    return True


def get_home_folder():
    """
    Get user home folder (because cygwin make default method fail)

    :return:        The real native user home folder path
    :rtype:         str
    """
    if platform.system().lower() == "windows":
        path = subprocess.check_output(['cmd', '/c', "echo %systemdrive%%homepath%"])
    else:
        path = os.path.expanduser("~")
    return path.rstrip("/").rstrip(os.linesep)


def get_fqdn_from_domain(domain):
    """
    Get the full name of a domain if we can have more information from custom user ssh config

    :param domain:          The domain name. It may be a short name
    :type domain:           str
    :return:                The full domain name if found, the short one otherwise
    :rtype:                 str
    """
    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.join(get_home_folder(), ".ssh", "config")
    if not os.path.exists(user_config_file):
        user_config_file = os.path.join(get_home_folder(), "ssh", "config")

    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config.parse(f)
        user_config = ssh_config.lookup(domain)
        if 'hostname' in user_config:
            return user_config['hostname']
    return domain


def get_auth_methods(domain):
    """
    Try to list all available authentication methods an ssh server allows

    :param domain:      The domain to connect to
    :type domain:       str
    :return:            The list of allowed authentication methods
    :rtype:             list[str]
    """
    with using_ssh_transport(domain) as transport:
        auth_methods = []
        try:
            transport.auth_none(project_util.get_sanitized_user())
        except paramiko.BadAuthenticationType as e:
            auth_methods = e.allowed_types
        return auth_methods


class SshParams(object):
    """
    Represent required parameters to connect to an ssh server
    """
    def __init__(self, domain, login=None, key=None, passphrase=None):
        """
        :param domain:      The domain to connect to. Can be an alias configured in user ssh config file
        :type domain:       str
        :param login:       Specify ssh user, Optional, default None
        :type login:        str|None
        :param key:         Specify ssh key path, Optional, default None
        :type key:          str|None
        :param passphrase:  Specify key passphrase, Optional, default None
        :type passphrase:   str|None
        """
        super(SshParams, self).__init__()
        self.domain = domain
        self.port = 22
        self.login = None
        self.key = None
        self.password = None
        self.passphrase = None
        self.proxy_sock = None

        ssh_config = paramiko.SSHConfig()
        user_config_file = os.path.join(get_home_folder(), ".ssh", "config")
        if not os.path.exists(user_config_file):
            user_config_file = os.path.join(get_home_folder(), "ssh", "config")

        if os.path.exists(user_config_file):
            with open(user_config_file) as f:
                ssh_config.parse(f)
            user_config = ssh_config.lookup(domain)
            user_config = {k.lower(): v for k, v in user_config.items()}  # lowercase every key
            if 'hostname' in user_config:
                self.domain = user_config['hostname']
            if 'username' in user_config:
                self.login = user_config['username']
            if 'user' in user_config:
                self.login = user_config['user']
            if 'port' in user_config:
                self.port = int(user_config['port'])
            if "identityfile" in user_config:
                id_files = user_config['identityfile']
                if type(id_files) not in (list, tuple):
                    id_files = [id_files]
                for id_file in id_files:
                    key_file = os.path.abspath(os.path.expanduser(id_file))
                    if os.path.exists(key_file):
                        self.key = key_file
                        break
            if 'proxycommand' in user_config:
                self.proxy_sock = paramiko.ProxyCommand(user_config['proxycommand'])

        if not self.login:
            self.login = project_util.get_sanitized_user()
        if login:
            self.login = login
        if key:
            self.key = key
        if passphrase:
            self.passphrase = passphrase


def is_passphrase_error(e):
    """
    Detect if an error is related to an ssh passphrase issue

    :param e:       The error to check
    :type e:        Exception
    :return:        True if the error is related to an ssh passphrase
    :rtype:         bool
    """
    if isinstance(e, paramiko.ssh_exception.SSHException):
        if isinstance(e, paramiko.ssh_exception.BadHostKeyException):
            return False
        return True
    if "not deserialize key data" in str(e) or "not a valid OPENSSH private key file" in str(e):
        return True
    return False


class InteractiveSsh(object):
    """
    Class corresponding to an established ssh connection
    You should not instantiate this class directly, you should prefer `using_ssh`
    """
    def __init__(self, ssh_conn, ssh_params, passphrase):
        """
        :param ssh_conn:        The established ssh connection
        :type ssh_conn:         paramiko.client.SSHClient
        :param ssh_params:      The connection parameters
        :type ssh_params:       SshParams
        :param passphrase:      The ssh key passphrase, usefull for auto-reconnection
        :type passphrase:       str|None
        """
        super(InteractiveSsh, self).__init__()
        self._ssh = ssh_conn
        self._params = ssh_params
        self._cache_sftp = None
        self._sudo_password = None
        self._use_posix_shell = InteractiveSsh._has_termios()
        self._passphrase = passphrase
        logging.raiseExceptions = False

    def try_run(self, cmd, as_user=None, quiet_stdout=False):
        """
        Run a command on the distant server

        :param cmd:             The command to run
        :type cmd:              list[str]|str
        :param as_user:         The user you would to impersonate. Optional, default None
        :type as_user:          str
        :param quiet_stdout:    Do you want distant stdout to be forwarded to this stdout
        :type quiet_stdout:     bool
        :return:                The exit status, stdout and stderr of the command
        :rtype:                 tuple[int, str, str]
        """
        if type(cmd) in (list, tuple):
            final_cmd = " ".join([project_util.shell_quote(x) for x in cmd])
        else:
            final_cmd = cmd

        sudo_password = None
        if as_user is not None and self._params.login != as_user:
            sudo_password = self._get_sudo_password()
            final_cmd = "sudo -H -S -p '' -u '" + as_user + "' sh -c " + project_util.shell_quote(final_cmd)

        return self._exec_cmd(final_cmd, quiet_stdout, sudo_password)

    def run(self, cmd, as_user=None, quiet=True):
        """
        Run a command on the distant server
        Raise Error on failure

        :param cmd:             The command to run
        :type cmd:              list[str]|str
        :param as_user:         The user you would to impersonate. Optional, default None
        :type as_user:          str
        :param quiet:           Do you want to hide the output. Optional, default True
        :type quiet:            bool
        """
        self.check_output(cmd, as_user, quiet)

    def check_output(self, cmd, as_user=None, quiet=True):
        """
        Run a command on the distant server
        Raise Error on failure

        :param cmd:             The command to run
        :type cmd:              list[str]|str
        :param as_user:         The user you would to impersonate. Optional, default None
        :type as_user:          str
        :param quiet:           Do you want to hide the output. Optional, default True
        :type quiet:            bool
        :return:                The stdout of the command
        :rtype:                 str
        """
        code, out, err = self.try_run(cmd, as_user, quiet)
        if code != 0:
            raise RuntimeError("Unable to run command "+repr(cmd)+":"+os.linesep+str(err))
        return out

    def ping(self):
        """
        Test the connection

        :return:        True if the ping worked
        :rtype:         bool
        """
        try:
            stdin, stdout, stderr = self._ssh.exec_command("echo ssh_ping")
            code = stdout.channel.recv_exit_status()
            if code != 0:
                return False
            if "ssh_ping" not in stdout.read():
                return False
            return True
        except (KeyboardInterrupt, SystemExit): raise
        except:
            return False

    def exists(self, path, as_user=None):
        """
        Check if a file or a folder exists on the server

        :param path:        The path on the server to check
        :type path:         str
        :param as_user:     The user you would to impersonate. Optional, default None
        :type as_user:      str
        :return:            True if the file exists
        :rtype:             bool
        """
        code, out, err = self.try_run(["test", "-e", path], as_user)
        return code == 0

    def is_file(self, path, as_user=None):
        """
        Check if the path exists and is a file on the server

        :param path:        The path on the server to check
        :type path:         str
        :param as_user:     The user you would to impersonate. Optional, default None
        :type as_user:      str
        :return:            True if the file exists
        :rtype:             bool
        """
        code, out, err = self.try_run(["test", "-f", path], as_user)
        return code == 0 and not err

    def is_folder(self, path, as_user=None):
        """
        Check if the path exists and is a folder on the server

        :param path:        The path on the server to check
        :type path:         str
        :param as_user:     The user you would to impersonate. Optional, default None
        :type as_user:      str
        :return:            True if the folder exists
        :rtype:             bool
        """
        code, out, err = self.try_run(["test", "-d", path], as_user)
        return code == 0 and not err

    def send_file(self, src, dest, overwrite=False, as_user=None):
        """
        Send a local file on the server
        Raise exception in case of failure
        WARNING: You only can send files to unix-like server

        :param src:         The file path to send on local machine
        :type src:          str
        :param dest:        The path where to place the file on the server
        :type dest:         str
        :param overwrite:   Define if we should overwrite the file or raise an error if the file already exists
                            on the server. Optional, default False
        :type overwrite:    bool
        :param as_user:     The user you would to impersonate. Optional, default None
        :type as_user:      str
        """
        if dest[0] != "/":
            raise RuntimeError("destination path should be absolute")
        if not os.path.exists(src):
            raise RuntimeError("file '"+src+"' doesn't exists")
        if not os.path.isfile(src):
            raise RuntimeError("'" + src + "' is not a file")
        if dest[-1] == "/":
            dest += os.path.basename(src)
        elif self.is_folder(dest, as_user):
            dest = dest+"/"+os.path.basename(src)
        folder = os.path.dirname(dest)
        self.run(["mkdir", "-p", folder], as_user)

        if self.exists(dest, as_user):
            if self.is_folder(dest, as_user):
                raise RuntimeError("'"+dest+"' is a folder")
            if overwrite:
                self.run(["rm", "-f", dest], as_user)
            else:
                raise RuntimeError("'" + dest + "' already exists")

        if as_user is None or as_user == self._params.login:
            self._sftp.put(src, dest, confirm=True)
        else:
            tmp_file = self.check_output("mktemp").strip()
            self._sftp.put(src, tmp_file, confirm=True)
            self.run(["chmod", "666", tmp_file])
            self.run(["cp", tmp_file, dest], as_user)
            self.run(["rm", tmp_file])

    def send_folder(self, src, dest, overwrite=False, as_user=None):
        """
        Send a local folder and it's content on the server
        Raise exception in case of failure
        WARNING: You only can send files to unix-like server

        :param src:         The folder path to send on local machine
        :type src:          str
        :param dest:        The path where to place the folder on the server
        :type dest:         str
        :param overwrite:   Define if we should replace the folder or raise an error if the file already exists
                            on the server. Optional, default False
        :type overwrite:    bool
        :param as_user:     The user you would to impersonate. Optional, default None
        :type as_user:      str
        """
        if dest[0] != "/":
            raise RuntimeError("destination path should be absolute")
        if not os.path.exists(src):
            raise RuntimeError("file '"+src+"' doesn't exists")
        if not os.path.isdir(src):
            raise RuntimeError("'" + src + "' is not a folder")
        if dest[-1] == "/":
            dest += os.path.basename(src)
        if self.exists(dest, as_user):
            if overwrite:
                self.run(["rm", "-rf", dest], as_user)
            else:
                raise RuntimeError("'"+dest+"' already exists")
        self.run(["mkdir", "-p", os.path.dirname(dest)], as_user)

        tar_filename = None
        fd = None
        try:
            tar_fh = None
            try:
                fd, tar_filename = tempfile.mkstemp(suffix=".tar.gz")
                tar_fh = tarfile.open(tar_filename, "w:gz")
                tar_fh.add(src, recursive=True, arcname=os.path.basename(dest))
            finally:
                if tar_fh:
                    tar_fh.close()
            tmp_file = self.check_output(["mktemp", "--suffix", ".tar.gz"]).strip()
            self._sftp.put(tar_filename, tmp_file, confirm=True)
            self.run(["chmod", "666", tmp_file])
            self.run(["tar", "-xz", "-C", os.path.dirname(dest), "-f", tmp_file], as_user)
            self.run(["rm", tmp_file])
        finally:
            if fd is not None:
                os.close(fd)
            if tar_filename is not None:
                os.remove(tar_filename)

    @property
    def _sftp(self):
        """
        Get an sftp connection on the server

        :return:    The sftp connection
        :rtype:     paramiko.SFTPClient
        """
        if self._cache_sftp is None:
            self._cache_sftp = self._ssh.open_sftp()
        return self._cache_sftp

    def _check_sudo_pwd(self, sudo_pwd=None, silent_error=False):
        """
        Check if given sudo pasword works

        :param sudo_pwd:        The password to check, or None if we want to check without pwd. Optional, default None
        :type sudo_pwd:         str|None
        :param silent_error:    Hide error message if it fails. Optional, default False
        :type silent_error:     bool
        :return:                True if the passwotrd works, False otherwise
        :rtype:                 bool
        """
        if sudo_pwd is None or sudo_pwd == "":
            stdin, stdout, stderr = self._ssh.exec_command("sudo -n true")
        else:
            stdin, stdout, stderr = self._ssh.exec_command("echo '" + sudo_pwd + "' | sudo -S -p '' true")
        result = stdout.channel.recv_exit_status()
        if int(result) == 0:
            return True

        if not silent_error:
            sys.stderr.write(stderr.read())
            sys.stderr.flush()
            sys.stdout.write(stdout.read())
            sys.stdout.flush()
        return False

    def _get_sudo_password(self):
        """
        Ask and test a sudo password, and save it.
        Raise KeyboardInterrupt if the user cancel

        :return:    The sudo password
        :rtype:     str
        """
        try:
            import keyring
            use_keyring = True
        except StandardError:
            use_keyring = False

        if self._sudo_password is not None:
            return self._sudo_password

        # Check for empty password
        if self._check_sudo_pwd(None, True):  # No need for password
            self._sudo_password = ""
            return self._sudo_password

        tested = set([])

        # Try using system keyring if available
        if use_keyring:
            keyring.get_keyring()
            sudo_pwd = keyring.get_password(self._params.domain, self._params.login)
            if sudo_pwd != None and self._check_sudo_pwd(sudo_pwd):
                self._sudo_password = sudo_pwd
                keyring.set_password(self._params.domain, self._params.login, sudo_pwd)
                return sudo_pwd
            tested.add(sudo_pwd)

        # Ask the user until it's good or the user cancel
        while True:
            full_login = self._params.login+"@"+self._params.domain
            try:
                full_login_str = full_login.encode("utf-8")
                sudo_pwd = getpass.getpass("[sudo] password for "+full_login_str+": ").strip()
            except EOFError:
                raise KeyboardInterrupt()
            if not sudo_pwd or sudo_pwd in tested:
                sys.stderr.write(os.linesep+"This password has already been tested, please retry."+os.linesep)
                sys.stderr.flush()
                continue
            if self._check_sudo_pwd(sudo_pwd):
                self._sudo_password = sudo_pwd
                if use_keyring:
                    keyring.set_password(self._params.domain, self._params.login, sudo_pwd)
                return sudo_pwd
            tested.add(sudo_pwd)

    def _exec_cmd(self, final_cmd, quiet_stdout, sudo_password=None):
        """
        Run a command on the server, core implementation

        :param final_cmd:           The command to run
        :type final_cmd:            str
        :param quiet_stdout:        Should we hide the command stdout
        :type quiet_stdout:         bool
        :param sudo_password:       Sudo password to use. Optional, default None
        :type sudo_password:        str|None
        :return:                    The exit status, stdout and stderr of the command
        :rtype:                     tuple[int, str, str]
        """
        if self._ssh.get_transport() is None:
            self._reconnect()
        with self._ssh.get_transport().open_session() as chan:
            chan.get_pty()
            chan.exec_command(final_cmd)
            if self._has_termios():
                return InteractiveSsh._posix_shell(chan, quiet_stdout, sudo_password)
            else:
                return InteractiveSsh._windows_shell(chan, quiet_stdout, sudo_password)

    def _reconnect(self):
        try:
            self._ssh.close()
        except Exception as e:
            sys.stderr.write("Warning: "+str(e)+"\n")
            sys.stderr.flush()

        self._ssh.connect(self._params.domain, self._params.port, self._params.login, password=self._params.password,
                          key_filename=self._params.key, passphrase=self._passphrase, look_for_keys=False)

    @staticmethod
    def _has_termios():
        """
        Detect the kind of terminal emulation we can use

        :return:        True if we can use Posix like terminal emulation, False otherwise
        :rtype:         bool
        """
        try:
            import termios
            import tty
            return True
        except ImportError:
            return False

    @staticmethod
    def _posix_shell(chan, quiet=False, sudo_password=None):
        """
        wrap a command into a shell for interactive purpose, posix implementation
        Warning: Not tested

        :param chan:                The paramiko corresponding channel
        :type chan:                 paramiko.Channel
        :param quiet:               Should we hide command stdout? Optional, default False
        :type quiet:                bool
        :param sudo_password:       The sudo password. Optional, default None
        :type sudo_password:        str|None
        :return:                    The exit status, stdout and stderr of the command
        :rtype:                     tuple[int, str, str]
        """
        import select
        import termios
        import tty

        stdout_buffer = ""
        stderr_buffer = ""

        old_tty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)

            left_strip_finished = True  # Hack to hide empty lines from sudo password question
            if sudo_password:
                chan.send(sudo_password+"\n")
                left_strip_finished = False

            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        while chan.recv_stderr_ready():
                            err_data = u(chan.recv_stderr(1))
                            stderr_buffer += err_data
                            if not quiet:
                                sys.stderr.write(err_data)
                            sys.stderr.write(err_data)
                        sys.stderr.flush()
                        while chan.recv_ready():
                            bytes = chan.recv(1)
                            try:
                                x = u(bytes)
                            except UnicodeDecodeError:
                                x = str(x)
                            if len(x) == 0:
                                break
                            stdout_buffer += x
                            if not stdout_buffer:
                                continue
                            if not left_strip_finished and stdout_buffer.strip() in ("", sudo_password):
                                stdout_buffer = ""
                            else:
                                left_strip_finished = True
                                if not quiet:
                                    sys.stdout.write(x)
                        if not quiet:
                            sys.stdout.flush()
                    except socket.timeout:
                        pass
                    if chan.closed:
                        break
                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break
                    chan.send(x)
            return int(chan.recv_exit_status()), stdout_buffer, stderr_buffer
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)

    @staticmethod
    def _windows_shell(chan, quiet=False, sudo_password=None):
        """
        wrap a command into a shell for interactive purpose, windows implementation
        Warning: Not tested

        :param chan:                The paramiko corresponding channel
        :type chan:                 paramiko.Channel
        :param quiet:               Should we hide command stdout? Optional, default False
        :type quiet:                bool
        :param sudo_password:       The sudo password. Optional, default None
        :type sudo_password:        str
        :return:                    The exit status, stdout and stderr of the command
        :rtype:                     tuple[int, str, str]
        """
        import threading
        import msvcrt

        class StdStreamMemory(object):
            def __init__(self):
                super(StdStreamMemory, self).__init__()
                self.stdout_buffer = ""
                self.stderr_buffer = ""
        mem = StdStreamMemory()

        first_empty_found = True
        if sudo_password:
            chan.send(sudo_password + "\n")
            first_empty_found = False

        def write_all(sock, std_mem, out_quiet, empty_found):
            first_blank_found = empty_found
            while True:
                while chan.recv_stderr_ready():
                    err_data = u(chan.recv_stderr(1024))
                    std_mem.stderr_buffer += err_data
                    if not first_blank_found and std_mem.stderr_buffer == "\n":
                        first_blank_found = True
                        std_mem.stderr_buffer = ""
                    else:
                        sys.stderr.write(err_data)
                    sys.stderr.flush()
                while chan.recv_ready():
                    data = sock.recv(256)
                    if not data:
                        sys.stdout.flush()
                        break
                    std_mem.stdout_buffer += data
                    if not first_blank_found and std_mem.stdout_buffer == "\n":
                        first_blank_found = True
                        std_mem.stdout_buffer = ""
                    elif not out_quiet:
                        sys.stdout.write(data)
                        sys.stdout.flush()
                if chan.exit_status_ready():
                    return

        writer = threading.Thread(target=write_all, args=(chan, mem, quiet, first_empty_found))
        writer.start()

        try:
            while writer.is_alive():
                if msvcrt.kbhit():
                    d = sys.stdin.read(1)
                    if not d:
                        break
                    chan.send(d)
        except EOFError:
            # user hit ^Z or F6
            pass
        return int(chan.recv_exit_status()), mem.stdout_buffer, mem.stderr_buffer
