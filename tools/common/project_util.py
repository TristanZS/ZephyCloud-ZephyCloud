#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This script provide common functions called by other scripts
"""

# Core python libraries
import sys
import os
import re
import json
import platform
import socket
import shutil
import subprocess
import contextlib
import tempfile
import glob
import random
import ctypes
import getpass
import logging
import numbers
import copy
import warnings

# Third party libraries
import ruamel.yaml
import Crypto.PublicKey.RSA
import paramiko
import cryptography.utils


# We can remove this with the next paramiko version
warnings.filterwarnings("ignore", category=cryptography.utils.CryptographyDeprecationWarning)


# Hack to fix ruamel bug on json dumping
import functools

def json_default(obj):
    import ruamel.yaml.comments

    if isinstance(obj, ruamel.yaml.comments.CommentedMap):
        return obj._od
    if isinstance(obj, ruamel.yaml.comments.CommentedSeq):
        return obj._lst
    raise TypeError

json.dumps = functools.partial(json.dumps, default=json_default)



# The list of admin ssh public used to give admin access on servers
DASHBOARD_SSH_KEYS_URL = "https://dashboard.aziugo.com/admin/users/keys/list/default/ssh.json?group=dev"

# The default password of generated users on servers and workers
DEFAULT_PASSWORD_URL = "https://dashboard.aziugo.com/api/users/secrets/data/slug/sysadmin-default-password.html"


# Certificate Constants:
SSH_KEY_SIZE = 4096


def is_float(var):
    try:
        float(var)
        return True
    except ValueError:
        return False


def is_string(var):
    if sys.version_info[0] > 2:
        return isinstance(var, str)
    else:
        return isinstance(var, basestring)


def is_primitive(var):
    if sys.version_info[0] > 2:
        return isinstance(var, (str, int, bool, float))
    else:
        return isinstance(var, (basestring, int, long, bool, float))


def ll_float(var):
    """
    Check parameter can be cast as a valid float

    :param var:     The variable to check
    :type var:      any
    :return:        True if the value can be cast to float
    :rtype:         bool
    """
    try:
        float(var)
        return True
    except (ValueError, TypeError):
        return False

def has_filled_value(dictionary, key):
    """
    Check if a dictionary has a valid non empty value for given key

    :param dictionary:      The dictionary to check
    :type dictionary:       dict[str, any]
    :param key:             The key to check
    :type key:              str
    :return:                True if there is a non empty value
    :rtype:                 bool
    """
    if key not in dictionary.keys():
        return False
    if not dictionary[key]:
        return False
    if is_string(dictionary[key]) and not dictionary[key].strip():
        return False
    return True


def env_is_on(key):
    """
    Check if an environment variable is on

    :param key:     The environment variable name
    :type key:      str
    :return:        True if the environment variable is on
    :rtype:         bool
    """
    if key not in os.environ.keys():
        return False
    if not os.environ[key]:
        return False
    if is_string(os.environ[key]) and not os.environ[key].strip():
        return False
    return str(os.environ[key]).strip().lower() in ('yes', 'true', 't', 'y', '1', 'o', 'oui', 'on')


def str2bool(value, default=False):
    """
    Convert a string to bool
    Raise error if not a valid bool

    :param value:       The value to cast
    :type value:        str|bool|None
    :param default:     The default value if not able to parse. Optional, default False
    :type default:      any
    :return:            The boolean value
    :rtype:             bool
    """
    if not value:
        return default
    if isinstance(value, bool):
        return value
    if str(value).lower() in ('yes', 'true', 't', 'y', '1', 'o', 'oui', 'on'):
        return True
    elif str(value).lower() in ('no', 'false', 'f', 'n', '0', 'non', 'off'):
        return False
    else:
        return default


def strict_str2bool(value):
    """
    Convert a string to bool
    Raise error if not a valid bool

    :param value:       The value to cast
    :type value:        str
    :return:            The boolean value
    :rtype:             bool
    """
    if str(value).lower() in ('yes', 'true', 't', 'y', '1', 'o', 'oui', 'on'):
        return True
    elif str(value).lower() in ('no', 'false', 'f', 'n', '0', 'non', 'off'):
        return False
    else:
        raise RuntimeError('Boolean value expected.')


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


def is_valid_hostname(hostname, use_ssh_config=False):
    """
    Check a hostname is a valid FQDN

    :param hostname:            The domain name
    :type hostname:             str
    :param use_ssh_config:      Can we use the full domain name if in local user ssh config ? Optional, default False
    :type use_ssh_config:       bool
    :return:                    True if the input is an FQDN
    :rtype:                     bool
    """
    if use_ssh_config:
        hostname = get_fqdn_from_domain(hostname)
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    if "." not in hostname:
        return False
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def is_admin():
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except (KeyboardInterrupt, SystemExit): raise
        except:
            raise False
    else:
        return os.getuid() == 0


def is_valid_location(location):
    return location in ("eu", "cn", "us", "ca", "in", "ko", "ja", "sg", "au", "br")


def get_host_ip():
    """
    Get the current host main IP address

    :return:    The host IP address used to ping 8.8.8.8
    :rtype:     str
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        if sock is not None:
            sock.close()


def which(exec_name):
    """
    Get path of an executable
    Raise error if not found

    :param exec_name:       The binary name
    :type exec_name:        str
    :return:                The path to the executable file
    :rtype:                 str
    """
    path = os.getenv('PATH')
    available_exts = ['']
    if "windows" in platform.system().lower():
        additional_exts = [ext.strip() for ext in os.getenv('PATHEXT').split(";")]
        available_exts += ["."+ext if ext[0] != "." else ext for ext in additional_exts]
    for folder in path.split(os.path.pathsep):
        for ext in available_exts:
            exec_path = os.path.join(folder, exec_name+ext)
            if os.path.exists(exec_path) and os.access(exec_path, os.X_OK):
                return exec_path
    raise RuntimeError("Unable to find path for executable "+str(exec_name))


def has_exec_installed(exec_name):
    """
    Check if an executable file is installer and is in PATH

    :param exec_name:   The name of the executable to find
    :type exec_name:    str
    :return:            True if we have found the binary
    :rtype:             bool
    """
    exec_bin = None
    try:
        exec_bin = shutil.which(exec_name)
    except AttributeError:  # Python 2
        from distutils.spawn import find_executable
        try:
            exec_bin = find_executable(exec_name)
        except:
            pass
    if not exec_bin:
        return False
    return True


def load_conf():
    """
    Load the default config file

    :return:    The configuration
    :rtype:     any
    """
    script_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.abspath(os.path.join(script_path, "..", ".."))

    config_file = os.path.join(project_path, "config.local.yml")
    if not os.path.exists(config_file):
        config_file = os.path.join(project_path, "config.yml")
    with open(config_file, "r") as fh:
        conf = ruamel.yaml.YAML().load(fh)
    return conf


def get_sanitized_user():
    username = re.sub('[^a-z]+', '', getpass.getuser().lower())
    if not username:
        username = "user"
    return username


def get_domain_conf(conf, domain):
    """
    Get the domain configuration

    :param conf:        The global configuration, loaded form config.yml
    :type conf:         dict[str, any]
    :param domain:      The domain we want
    :type domain:       str
    :return:            The domain configuration
    :rtype:             dict[str, any]
    """
    domain_conf = dict(copy.deepcopy(conf["servers"]["default"]))
    api_name = conf["api_name"].strip()
    user_name = get_sanitized_user()
    domain_order = []

    for raw_domain_name in conf["servers"].keys():
        substituted_domain_name = raw_domain_name.replace("%API_NAME%", api_name).replace("%LOCAL_USER%", user_name)
        if substituted_domain_name == domain:
            domain_order.append(raw_domain_name)

    domain_order = sorted(domain_order, key=lambda x: x.count("%"))
    for raw_domain_name in domain_order:
        domain_conf.update(dict(copy.deepcopy(conf["servers"][raw_domain_name])))
    return domain_conf


def get_all_domains():
    """
    Get all known domains from configuration file

    :return:    The list of all known domains
    :rtype:     list[str]
    """
    conf = load_conf()
    api_name = conf["api_name"].strip()
    user_name = get_sanitized_user()
    results = set([])
    for domain in conf["subdomains"].values():
        results.add(domain.strip().replace("%API_NAME%", api_name).replace("%LOCAL_USER%", get_sanitized_user()))

    for domain in conf["servers"].keys():
        if domain != "default":
            results.add(domain.replace("%API_NAME%", api_name).replace("%LOCAL_USER%", user_name))
    return list(results)


def get_parsed_value(content, labels, default=None):
    """
    Get a value located in an ini-like content

    :param content:     the ini-like content
    :type content:      str
    :param labels:      List of accepted label (the first found will be returned
    :type labels:       list[str]
    :param default:     default value if nothing is found. Optional, default None
    :type default:      any
    :return:            The value found, or the default value
    :rtype:             str|any
    """
    separators = [":", "="]
    for line in content.splitlines():
        for key_label in labels:
            if line.startswith(key_label):
                seps = filter(lambda x: x in line, separators)
                seps_pos = sorted(map(lambda y: line.index(y), seps))
                if not seps_pos:
                    continue
                return line[seps_pos[0]+1:].strip()
    return default


def shell_quote(arg):
    """
    Quote a parameter for shell usage
    Example:
        shell_quote("c'est cool aujourd'hui, il fait beau") => 'c'"'"'est cool aujourd'"'"'hui, il fait beau'

    :param arg:         The argument to quote
    :type arg:          str
    :return:            the quoted argument
    :type:              str
    """
    if sys.version_info[0] >= 3:  # Python 3
        import shlex
        return shlex.quote(arg)
    else:  # Python 2
        import pipes
        return pipes.quote(arg)


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


def run(cmd, cwd=None, env=None):
    """
    Run a system command

    :param cmd:     The command to run
    :type cmd:      str|list[str]
    :param cwd:     The working directory. Optional, default None
    :type cwd:      str|None
    :param env:     Modified environment. Optional, default None
    :type env:      str|None
    :return:        Return the result code, out and err of the command
    :rtype:         tuple[int, str, str]
    """
    child_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env)
    std_out, std_err = child_proc.communicate()
    if child_proc.returncode is None:
        child_proc.wait()
        if child_proc.returncode is None:
            return 257, std_out, std_err
    return int(child_proc.returncode), std_out, std_err


def touch(path):
    """
    Create file if it doesn't exists and set modification date to now
    Equivalent of posix `touch` command

    :param path:    File to touch
    :type path:     str
    """
    with open(path, 'a'):
        os.utime(path, None)


def cli_input(question=None):
    """
    Read an input from keyboard. It replace the old python raw_input. Improvements are:
    - Show question on stderr instead of stdout
    - Compatible with python 3
    - Raise keyboard error when user press Ctrl-D (or any stdin closing method)

    :param question:        The question to ask. Optional, default None
    :type question:         str|None
    :return:                The user inputs
    :rtype:                 str
    """
    old_stdout = sys.stdout
    question_str = None if question is None else question.strip() + " "
    try:
        if sys.version_info[0] >= 3:  # Python 3
            return unicode(input(question_str)).strip()
        else:
            return unicode(raw_input(question_str)).strip()
    except EOFError:
        raise KeyboardInterrupt()
    finally:
        sys.stdout = old_stdout


def read_input(question=None, allow_empty=False, history_key=None):
    """
    Read one input and return it
    It raises KeyboardException if user close stdin

    :param question:        The question to display to user. Optional, default None
    :type question:         str|None
    :param allow_empty:     Do we want empty answers. Optional, default False
    :type allow_empty:      bool
    :param history_key:     Which history we should use. Should math [a-z]+ format. Optional, default None
    :type history_key:      str|None
    :return:                return the trimmed response
    :rtype:                 str
    """
    try:
        import readline
        readline_ok = True
    except ImportError:
        readline_ok = False

    script_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.abspath(os.path.join(script_path, "..", ".."))
    hist_dir = os.path.join(project_path, "tmp", "cmd_history")
    hist_file = os.path.join(hist_dir, history_key) if history_key else None
    if history_key is not None and readline_ok:
        if not os.path.exists(hist_dir):
            os.makedirs(hist_dir)
        if os.path.exists(hist_file):
            readline.read_history_file(hist_file)

    try:
        while True:
            result = cli_input(question)
            if not result and not allow_empty:
                continue
            return result
    finally:
        if readline_ok and history_key:
            readline.write_history_file(hist_file)
            readline.clear_history()


def reading_inputs(question=None, allow_empty=False, history_key=None):
    """
    Read inputs until you can be satisfied with the answer
    It works like an infinite generator so you should use it with `for` and `break`
    It raises KeyboardException if user close stdin

    :param question:        The question to display to user. Optional, default None
    :type question:         str|None
    :param allow_empty:     Do we want empty answers. Optional, default False
    :type allow_empty:      bool
    :param history_key:     Which history we should use. Should math [a-z]+ format. Optional, default None
    :type history_key:      str|None
    :return:                Yield each response, trimmed
    :rtype:                 str
    """

    try:
        import readline
        readline_ok = True
    except ImportError:
        readline_ok = False

    script_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.abspath(os.path.join(script_path, "..", ".."))
    hist_dir = os.path.join(project_path, "tmp", "cmd_history")
    hist_file = os.path.join(hist_dir, history_key) if history_key else None
    if history_key is not None and readline_ok:
        if not os.path.exists(hist_dir):
            os.makedirs(hist_dir)
        if os.path.exists(hist_file):
            readline.read_history_file(hist_file)

    try:
        while True:
            result = cli_input(question)
            if not result and not allow_empty:
                continue
            yield result
    finally:
        if readline_ok and history_key:
            readline.write_history_file(hist_file)
            readline.clear_history()


def can_use_readline():
    """
    Can we use Readline python library

    :return:    True if the readline library is available
    :rtype:     bool
    """
    try:
        import readline
        return True
    except ImportError:
        return False


def simple_read_path(question=None, allow_files=True, allow_folders=False):
    """
    Read a path, providing retry capabilities

    :param question:            What question to display to the user. Optional, default None
    :type question:             str|None
    :param allow_files:         Do we want a file ? Optional, default True
    :type allow_files:          bool
    :param allow_folders:       Do we want a folder ? Optional, default False
    :type allow_folders:        bool
    :return:                    The selected file/folder
    :rtype:                     str
    """

    while True:
        result = cli_input(question)
        answer = os.path.expanduser(result)
        if not answer:
            continue
        if not os.path.exists(answer):
            sys.stderr.write(os.linesep+"Invalid file: " + str(answer) + os.linesep)
            sys.stderr.flush()
            continue
        if os.path.isdir(answer):
            if allow_folders:
                return os.path.abspath(answer)
            else:
                sys.stderr.write(os.linesep + answer + " is not a file"+os.linesep)
                sys.stderr.flush()
        elif not allow_files:
            sys.stderr.write(os.linesep + answer + " is not a folder"+os.linesep)
            sys.stderr.flush()
        else:
            return os.path.abspath(answer)


def read_path(question=None, allow_files=True, allow_folders=False, history_key=None):
    """
    Read a path, providing retry capabilities and auto-completion

    :param question:            What question to display to the user. Optional, default None
    :type question:             str|None
    :param allow_files:         Do we want a file ? Optional, default True
    :type allow_files:          bool
    :param allow_folders:       Do we want a folder ? Optional, default False
    :type allow_folders:        bool
    :param history_key:         Which history we should use. Should math [a-z]+ format. Optional, default None
    :type history_key:          str|None
    :return:                    The selected file
    :rtype:                     str
    """

    # FIXME LATER: improve One choice with slashes

    use_readline = can_use_readline()
    if use_readline:
        import readline

        def path_completer(text, state):
            readline.get_line_buffer().split()
            expanded_text = os.path.expanduser(text)
            tmp = [x for x in glob.glob(os.path.expanduser(text) + '*')][state]
            if tmp:
                tmp = text + tmp[len(expanded_text):]
            return tmp

        script_path = os.path.dirname(os.path.abspath(__file__))
        project_path = os.path.abspath(os.path.join(script_path, "..", ".."))
        hist_dir = os.path.join(project_path, "tmp", "cmd_history")
        hist_file = os.path.join(hist_dir, history_key) if history_key else None
        if history_key is not None:
            if not os.path.exists(hist_dir):
                os.makedirs(hist_dir)
            if os.path.exists(hist_file):
                readline.read_history_file(hist_file)

        old_completer = readline.get_completer_delims()
        readline.set_completer_delims('\t')
        readline.parse_and_bind("tab: complete")
        readline.set_completer(path_completer)
        try:
            return simple_read_path(question, allow_files, allow_folders)
        finally:
            readline.set_completer(None)
            readline.set_completer_delims(old_completer)
            if history_key:
                readline.write_history_file(hist_file)
                readline.clear_history()
    else:
        return simple_read_path(question, allow_files, allow_folders)


@contextlib.contextmanager
def temp_file(content):
    """
    Generate a temporary file, and put the content inside it
    It yield the file path, and ensure file destruction

    :param content:     The content to put inside the temp file
    :type content:      str
    :return:            The temporary file path
    :rtype:             str
    """
    tmp_filename = None
    fd = None
    try:
        fd, tmp_filename = tempfile.mkstemp()
        with open(tmp_filename, "w") as fh:
            fh.write(content)
            fh.flush()
        yield tmp_filename
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_filename is not None:
            os.remove(tmp_filename)


@contextlib.contextmanager
def temp_filename(suffix="", prefix="tmp", dir=None):
    """
    Generate a temporary file, and put the content inside it
    It yield the file path, and ensure file destruction

    :return:            The temporary file path
    :rtype:             str
    """
    tmp_filename = None
    fd = None
    try:
        fd, tmp_filename = tempfile.mkstemp(suffix, prefix, dir)
        yield tmp_filename
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_filename is not None:
            os.remove(tmp_filename)


@contextlib.contextmanager
def temp_folder(parent_folder=None):
    """
    Create a temporary folder, yield it and then remove it

    :param parent_folder:   The place where we will create the temporary folder. Optional, default None
    :type parent_folder:    str|None
    :return:                The created temporary folder path
    :rtype:                 str
    """
    if parent_folder and not os.path.exists(parent_folder):
        os.makedirs(parent_folder)
    output_path = tempfile.mkdtemp(dir=parent_folder)
    try:
        yield output_path
    finally:
        shutil.rmtree(output_path)


def rerun_as_root():
    """ Rerun the same script but as root (asking for root password of UCA elevation on windows """
    # Ensure to prepend the interpreter name and convert script name to absolute path
    if os.path.basename(sys.argv[0]).endswith(".py"):
        argv = [sys.executable, os.path.abspath(sys.argv[0])]
        argv.extend(sys.argv[1:])
    else:
        argv = [sys.executable, os.path.abspath(sys.argv[1])]
        argv.extend(sys.argv[2:])

    if platform.system().lower() == "windows":
        import ctypes

        shell32 = ctypes.windll.shell32

        if shell32.IsUserAnAdmin():
            return

        if hasattr(sys, '_MEIPASS'):  # Support pyinstaller wrapped program.
            arguments = map(unicode, argv[2:])  # FIXME: Not sure about that
        else:
            arguments = map(unicode, argv[1:])
        argument_line = u' '.join(arguments)
        executable = unicode(sys.executable)
        ret = shell32.ShellExecuteW(None, u"runas", executable, argument_line, unicode(os.getcwd()), 1)
        if int(ret) <= 32:
            sys.stderr.write('Error(ret=%d): cannot elevate privilege.' % (ret,))
            sys.stderr.flush()
            sys.exit(5)
        sys.exit(0)
    else:  # Assume *nix
        if os.geteuid() == 0:
            return
        sudo_path = which("sudo")
        argv.insert(0, sudo_path)
        os.execv(sudo_path, argv)


def run_as_root(cmd):
    """
    Run a command as root/admin (asking for root password of UCA elevation on windows

    :param cmd:     The command to run
    :type cmd:      list[str]
    """
    # Ensure to prepend the interpreter name and convert script name to absolute path
    if os.path.basename(sys.argv[0]).endswith(".py"):
        argv = [sys.executable, os.path.abspath(sys.argv[0])]
        argv.extend(sys.argv[1:])
    else:
        argv = [sys.executable, os.path.abspath(sys.argv[1])]
        argv.extend(sys.argv[2:])

    if platform.system().lower() == "windows":
        import ctypes

        shell32 = ctypes.windll.shell32

        if shell32.IsUserAnAdmin():
            subprocess.check_call(cmd)
        else:
            ret = shell32.ShellExecuteW(None, u"runas", cmd[0], cmd[1:], None, 1)
            if int(ret) <= 32:
                raise RuntimeError("Command failed with code "+str(ret))
    else:  # Assume *nix
        if os.geteuid() == 0:
            subprocess.check_call(cmd)
        else:
            subprocess.check_call(["sudo"]+cmd)


_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def generate_salt():
    """
    Generate a random string

    :return:        The random string
    :rtype:         str
    """
    result = ''
    for i in range(16):
        result += str(random.choice(_ALPHABET))
    return result


def get_current_git_commit():
    """
    Get the current commit hash if possible

    :return:    The current commit hash, or None if we can't
    :rtype:     str|None
    """
    if not has_exec_installed("git"):
        return None
    script_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.abspath(os.path.join(script_path, "..", ".."))

    code, out, err = run(["git", "rev-parse", "HEAD"], cwd=project_path)
    if code != 0 or not out.strip():
        return None
    return str(out.splitlines()[0]).strip()


def generate_ssh_keys(size=SSH_KEY_SIZE):
    """
    Generate an SSH key pair

    :param size:    The key size. Optional, default 4096
    :type size:     int
    :return:        The public and private keys
    :rtype:         tuple[str, str]
    """
    rsa_key = Crypto.PublicKey.RSA.generate(size)
    priv_key = rsa_key.exportKey('PEM')
    pubkey = rsa_key.publickey().exportKey(format='OpenSSH')
    return pubkey, priv_key


class ConfError(RuntimeError):
    """ A Config specific Exception """
    pass


def check_conf(ok, description="Invalid config"):
    """
    Check an assertion
    Raise a ConfError in case the assertion is False

    :param ok:              An assertion
    :type ok:               bool
    :param description:     Error specific description. Optional, default "Invalid config"
    :type description:      str
    """
    if not ok:
        raise ConfError(str(description) + "."+ os.linesep+ "Please check config.yml file")


def check_basic_conf(conf):
    """
    Check the config file is fully configured
    Raise ConfError in case of failure

    :param conf:        The config file to check
    :type conf:         dict[str, any]
    """

    check_conf("api_name" in conf, "No 'api_name' defined")
    check_conf(bool(re.match(r"^[a-z]+$", conf["api_name"])), "'api_name' is not valid")
    api_name = conf["api_name"]
    check_conf("subdomains" in conf, "No 'subdomains' defined")
    for subdomain in ("dev", "stage", "prod"):
        check_conf(subdomain in conf['subdomains'], "No '"+subdomain+"' defined in 'subdomains'")
        full_subdomain = conf['subdomains'][subdomain].replace("%API_NAME%", api_name)
        full_subdomain = full_subdomain.replace("%LOCAL_USER%", get_sanitized_user())
        check_conf(is_valid_hostname(full_subdomain),
                   "'" + subdomain + "' defined in 'subdomains' is not a valid domain")
    check_conf("servers" in conf, "no 'servers' section")
    check_conf("default" in conf["servers"], "no 'default' section in 'servers' section")
    check_conf('providers' in conf, "no 'providers' section")
    check_conf('storages' in conf, "no 'storages' section")

    for domain in conf["servers"].keys():
        domain = domain.replace("%API_NAME%", api_name).replace("%LOCAL_USER%", get_sanitized_user())
        if domain != "default":
            check_conf(is_valid_hostname(domain), "'" + domain + "' is not a valid domain in 'servers'")
            domain_conf = get_domain_conf(conf, domain)
        else:
            domain_conf = conf["servers"][domain]
        check_conf("email" in domain_conf, "no 'email' section for domain " + repr(domain))
        check_conf("log_level" in domain_conf, "no 'log_level' section for domain " + repr(domain))
        log_lvl = logging.getLevelName(domain_conf["log_level"].strip().upper())
        check_conf(isinstance(log_lvl, numbers.Integral), "'log_level' section for domain "+domain+" is not valid")

        check_conf('providers' in domain_conf, "no 'providers' section for domain " + repr(domain))
        check_conf('storages' in domain_conf, "no 'storages' section for domain " + repr(domain))

        check_conf(len(domain_conf['providers']) > 0, "no providers for domain " + repr(domain))
        check_conf(len(domain_conf['storages']) > 0, "no storages for domain " + repr(domain))

        available_storages = []
        for storage_name in domain_conf['storages']:
            check_conf(storage_name in conf['storages'], "Unknown storage " + repr(storage_name))
            store_conf = conf['storages'][storage_name]
            check_conf('type' in store_conf, "no type for storage " + repr(storage_name))
            available_storages.append(storage_name)

        for provider_name in domain_conf['providers']:
            check_conf(provider_name in conf['providers'], "Unknown provider " + repr(provider_name))
            prov_conf = conf['providers'][provider_name]
            check_conf('type' in prov_conf, "no type for provider " + repr(provider_name))
            check_conf('storage_priority' in prov_conf, "no storage_priority for provider " + repr(provider_name))
            found_storage = False
            for storage_name in prov_conf['storage_priority']:
                if storage_name in available_storages:
                    found_storage = True
                    break
            if not found_storage:
                check_conf(False, "no available storage for provider " + repr(provider_name))


_TEXT_CHARS = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
_BIN_EXT_LIST = ("zip", "woff", "ttf", "swf", "stat", "socket", "pyc", "png", "pdf", "map", "jpg", "jpeg", "init", "ico",
                 "gif", "eot", "db", "cur")


def is_bin_file(path):
    """
    Check if a file is a binary file or a text file.
    /!\\ WARNING: It can have some false-positive or true-negative

    :param path:    A file path
    :type path:     str
    :return:        True if the file is a binary file
    :rtype:         bool
    """
    for ext in _BIN_EXT_LIST:
        if path.lower().endswith("."+ext):
            return True
    with open(path, "r") as fh:
        data = fh.read(1024)
        return bool(data.translate(None, _TEXT_CHARS))


def dos2unix(path):
    """
    Convert a file with Windows end of lines into a unix-eol file
    It replace CRLF ("\r\n") to NL ("\n")
    /!\\ WARNING: If you apply this method on a binary file, you will corrupt it

    :param path:    The path of the file to convert
    :type path:     str
    """
    outsize = 0
    with open(path, 'rb') as infile:
        content = infile.read()
    if "\r" not in content:
        return
    with open(path, 'wb') as output:
        for line in content.splitlines():
            outsize += len(line) + 1
            output.write(line + '\n')


def dos2unix_folder(folder_path):
    """
    Convert recursively all files in a folder from Windows to Unix End of Lines ("\n")

    :param folder_path:    The path of the file to convert
    :type folder_path:     str
    """
    for folder, subs, files in os.walk(folder_path):
        if ".git" in folder or ".svn" in folder:
            continue
        for filename in files:
            file_path = os.path.join(folder, filename)
            if not is_bin_file(file_path):
                dos2unix(file_path)
