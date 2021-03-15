# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libraries
import json
import os
import signal
import contextlib
import socket
import sys
import string
import random
import traceback

# Project specific libs
import type_util

PATH_TYPE_UNIX = 1
PATH_TYPE_WINDOWS = 2


def path_join(first, *args, **kwargs):
    """
    Concatenate path for other system.
    You could provide the "os" param to specify the os.
    If you wanrt to calculate a path for the current machine, you should use os.path.join instead

    :param first:   The first path element
    :type first:    str
    :param args:    The other path parts
    :type args:     str
    :param os:      Which kind of os you want to join. Optional, default PATH_TYPE_UNIX
    :type os:       int
    :return:        A valid unix path
    :rtype:         str
    """
    os_type = PATH_TYPE_UNIX
    if "os" in kwargs:
        if kwargs['os'] not in (PATH_TYPE_UNIX, PATH_TYPE_WINDOWS):
            raise RuntimeError("unknown os type "+repr(kwargs['os']))
        os_type = kwargs['os']

    if os_type == PATH_TYPE_UNIX:
        result = first.rstrip("/")
        for arg in args:
            result += "/" + arg.strip("/")
        return result
    else:  # os_type == PATH_TYPE_WINDOWS:
        result = first.rstrip("/").rstrip("\\")
        for arg in args:
            result += "\\" + arg.strip("/").rstrip("\\")
        return result


def float_equals(val1, val2):
    """
    Check if 2 float values are equals

    :param val1:    The first value
    :type val1:     float
    :param val2:    The second value
    :type val2:     float
    :return:        True if the values can be considered as equal
    :rtype:         bool
    """
    return abs(float(val1) - float(val2)) < 1e-07


def round_int(value, round_to):
    """
    Round a value by an arbitrary integer

    :param value:       The value you want to round
    :type value:        float|int
    :param round_to:    The value you want the result to be a multiple of
    :type round_to:     int
    :return:            the rounded value (ex: round_int(67, 5) => 65)
    :rtype:             int
    """
    return int((value + int(round_to)/2) // round_to * round_to)


def format_float(value, precision=4):
    str_format = "{:."+str(precision)+'f}'
    result = str_format.format(float(value)).rstrip('0').rstrip('.')
    if result == "" or result == "-" or result == "-0":
        return "0"
    return result


def has_flag(value, flag):
    """
    Check if a value contains specific bits

    :param value:       A numerical value (usually a status)
    :type value:        int
    :param flag:        A flag, usually one or an addition of powers of two
    :type flag:         int
    :return:            True if the value contains all bits of flag
    :rtype:             bool
    """
    return (value & flag) == flag


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
    if type_util.is_string(dictionary[key]) and not dictionary[key].strip():
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
    if type_util.is_string(os.environ[key]) and not os.environ[key].strip():
        return False
    return str(os.environ[key]).strip().lower() in ('yes', 'true', 't', 'y', '1', 'o', 'oui', 'on')


def env_is_off(key):
    """
    Check if an environment variable is off

    :param key:     The environment variable name
    :type key:      str
    :return:        True if the environment variable is on
    :rtype:         bool
    """
    if key not in os.environ.keys():
        return False
    if not os.environ[key]:
        return False
    if type_util.is_string(os.environ[key]) and not os.environ[key].strip():
        return False
    return str(os.environ[key]).strip().lower() in ('no', 'false', 'f', 'n', '0', 'non', 'off')


class TimeoutError(RuntimeError):
    pass


def _raise_timeout(*unused):
    raise TimeoutError()


@contextlib.contextmanager
def using_timeout(timeout):
    """
    This method should be used via the 'with' keyword
    This method raise a TimeoutError after timeout seconds if we didn't exit the 'with'
    If None or 0 given as timeout, it never raise errors

    :param timeout:     The timeout, in seconds
    :type timeout:      int|float|datetime.timedelta|None
    """
    if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
        yield
    else:
        if type_util.ll_float(timeout):
            timeout = int(float(timeout))
        else:
            timeout = timeout.seconds

        try:
            signal.signal(signal.SIGALRM, _raise_timeout)
            signal.alarm(timeout)
            yield
        finally:
            signal.alarm(0)


def tcp_port_status(host, port):
    """
    Ping a tcp port

    :param host:    The hostname or ip of a distant machine
    :type host:     str
    :param port:    The port to ping
    :type port:     int|str
    :return:        True if we successfully ping the server, False otherwise
    :rtype:         bool
    """
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((host, int(port)))
        s.shutdown(2)
        return True
    except StandardError:
        return False


class SaltChars(object):
    chars = string.ascii_letters + string.digits


def generate_salt(length=12):
    """
    Generate a new salt string

    :param length:      The length of the salt to generate. Optional, default 12
    :type length:       int
    :return:            the generated salt
    :rtype:             str
    """
    salt = ''
    for i in range(length):
        salt += SaltChars.chars[random.randint(0, len(SaltChars.chars) - 1)]
    return salt


def write_conf(filename, data, section="Job"):
    """
    Write a dictionary as config file> For complex objects, values are saved as json dump

    :param filename:    The config file name and path
    :type filename:     str
    :param data:        The data to save
    :type data:         dict[str, str]
    :param section:     The config file main section. Optional, default "Job"
    :type section:      str
    """
    if sys.version_info[0] >= 3:
        # FIXME PYTHON3: implement this
        raise NotImplementedError()
    else:
        import ConfigParser
        conf = ConfigParser.RawConfigParser()

    conf.add_section(section)
    for key, value in data.items():
        if type_util.is_primitive(value):
            conf.set(section, str(key), str(value))
        else:
            conf.set(section, str(key), json.dumps(value))

    with open(filename, 'wb') as configfile:
        conf.write(configfile)


def load_ini_file(filename):
    if sys.version_info[0] >= 3:
        # FIXME PYTHON3: implement this
        raise NotImplementedError()
    else:
        import ConfigParser
        conf = ConfigParser.ConfigParser()
    conf.read(filename)
    return conf


def compute_variance(data):
    y_squared_dot = sum(i * i for i in data)
    y_dot_squared = sum(data) ** 2
    return (y_squared_dot - y_dot_squared / len(data)) / (len(data) - 1)


def get_stack_str():
    try:
        raise RuntimeError("To get stack")
    except RuntimeError as e:
        return "".join(traceback.format_stack())
