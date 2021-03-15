# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This file configure gunicorn.
It use environment variables and config file to setup logging and binding of gunicorn

Usage:
    gunicorn -c "gunicorn_config.py" my_app_file:my_app
"""

# Python core libs
import os
import ConfigParser
import logging
import sys
import tempfile


API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Trivial config
workers = 4
timeout = 600


def is_string(var):
    """
    Check if parameter is a string

    :param var:     The variable to test
    :type var:      any
    :return:        True is the variable is a string or unicode
    :rtype:         bool
    """
    if sys.version_info[0] >= 3:
        return isinstance(var, str)
    else:
        return isinstance(var, basestring)


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
    if is_string(os.environ[key]) and not os.environ[key].strip():
        return False
    return str(os.environ[key]).strip().lower() in ('no', 'false', 'f', 'n', '0', 'non', 'off')


# Socket config
if "GUNICORN_BIND" in os.environ.keys() and os.environ["GUNICORN_BIND"] and os.environ["GUNICORN_BIND"].strip():
    bind_address = os.environ["GUNICORN_BIND"].strip()
else:
    bind_address = "127.0.0.1"
if "GUNICORN_PORT" in os.environ.keys() and os.environ["GUNICORN_PORT"] and os.environ["GUNICORN_PORT"].strip():
    gunicorn_port = int(os.environ["GUNICORN_PORT"].strip())
else:
    gunicorn_port = 8000
bind = bind_address+":"+str(gunicorn_port)

conf = None
if os.path.exists(os.path.join(API_PATH, 'config.conf')):
    conf = ConfigParser.ConfigParser()
    conf.read(os.path.join(API_PATH, 'config.conf'))

# Logging config
if "LOG_LEVEL" in os.environ.keys() and os.environ["LOG_LEVEL"] and os.environ["LOG_LEVEL"].strip():
    log_level = os.environ["LOG_LEVEL"].strip().upper()
elif conf is not None and conf.has_section("log") and conf.has_option("log", "webapi_level"):
    log_level = conf.get("log", "webapi_level").strip().upper()
else:
    log_level = "WARNING"

if "LOG_OUTPUT" in os.environ.keys() and os.environ["LOG_OUTPUT"] and os.environ["LOG_OUTPUT"].strip():
    log_output = os.environ["LOG_OUTPUT"].strip().lower()
elif conf is not None and conf.has_section("log") and conf.has_option("log", "webapi_output"):
    log_output = conf.get("log", "webapi_output").strip().lower()
else:
    log_output = "stderr"

log_level_int = logging.getLevelName(log_level)
if not isinstance(log_level_int, (int, long)):
    raise RuntimeError("Error: Invalid logging level "+repr(log_level)+"\n")

handlers = {}
if log_output in ("stderr", "stdout"):
    log_file = sys.stderr if log_output == "stderr" else sys.stdout
    if log_file.isatty():
        use_color = not env_is_off("LOG_COLOR")
    else:
        use_color = env_is_on("LOG_COLOR")
    if use_color:
        handlers["mainhandler"] = {
            'class': 'colorlog.StreamHandler',
            'formatter': 'mainformatter',
            'args': "(sys."+log_output+", )"
        }
        formatter = {
            'class': 'colorlog.ColoredFormatter',
            'format': "%(log_color)s%(levelname)-8s%(blue)s%(name)-16s%(reset)s %(white)s%(message)s"
        }
    else:
        handlers["mainhandler"] = {
            'class': 'logging.StreamHandler',
            'formatter': 'mainformatter',
            'args': "(sys." + log_output+", )"
        }
        formatter = {
            'class': 'logging.Formatter',
            'format': "%(levelname)s:%(name)s:%(message)s"
        }
elif log_output == "syslog":
    handlers["mainhandler"] = {
        'class': 'logging.handlers.SysLogHandler',
        'formatter': 'mainformatter',
        'args': "('/dev/log', )"
    }
    formatter = {
        'class': 'logging.Formatter',
        'format': '%(levelname)s %(module)s P%(process)d T%(thread)d %(message)s'
    }
else:
    handlers["mainhandler"] = {
        'class': 'logging.FileHandler',
        'formatter': 'mainformatter',
        'args': "('"+log_output+"', )"
    }
    formatter = {
        'class': 'logging.Formatter',
        'format': '%(asctime)s: %(levelname)-7s: %(name)s - %(message)s'
    }
if log_level_int > logging.DEBUG:
    handlers["null_handler"] = {"class": "NullHandler", "args": "()"}
root_log_level_int = log_level_int if log_level_int > logging.DEBUG else logging.INFO

log_config = "[loggers]\nkeys=root, gunicorn.error, gunicorn.access, aziugo\n\n"
log_config += "[handlers]\nkeys="+", ".join(handlers.keys())+"\n\n"
log_config += "[formatters]\nkeys=mainformatter\n\n"
log_config += "[logger_root]\nlevel="+logging.getLevelName(root_log_level_int)+"\nhandlers=mainhandler\n\n"

log_config += "[logger_gunicorn.error]\nlevel="+logging.getLevelName(root_log_level_int)+"\nhandlers=mainhandler\n"
log_config += "propagate=0\nqualname=gunicorn.error\n\n"

log_config += "[logger_gunicorn.access]\nlevel="+logging.getLevelName(root_log_level_int)+"\n"
if "null_handler" in handlers.keys():
    log_config += "handlers=null_handler\n"
else:
    log_config += "handlers=mainhandler\n"
log_config += "propagate=0\nqualname=gunicorn.access\n\n"

log_config += "[logger_aziugo]\nlevel="+logging.getLevelName(log_level_int)+"\nhandlers=mainhandler\n"
log_config += "propagate=0\nqualname=aziugo\n\n"

for handler_name in handlers.keys():
    log_config += "[handler_"+handler_name+"]\n"
    for prop, value in handlers[handler_name].items():
        log_config += prop+"="+value+"\n"
    log_config += "\n"
    
log_config += "[formatter_mainformatter]\nclass="+formatter["class"]+"\nformat="+formatter["format"]+"\n\n"

fd, tmp_filename = tempfile.mkstemp()
try:
    with open(tmp_filename, "w") as fh:
        fh.write(log_config)
        fh.flush()
finally:
    if fd is not None:
        os.close(fd)

logconfig = tmp_filename
