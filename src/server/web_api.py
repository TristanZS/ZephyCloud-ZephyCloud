# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
Web API script
"""

# Python core libs
import os
import json
import logging
import datetime

# Specific libs
from flask import Flask, g, escape, request, jsonify
from flask.json import JSONEncoder
try:
    from werkzeug.contrib.fixers import ProxyFix
except ImportError:
    from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException

# Project libs
from lib import util
from lib import error_util
from lib import date_util
import core.api_util
import core.storages


# Global datetime to json encoder
class TimestampJSONEncoder(JSONEncoder):
    def default(self, o):
        try:
            if isinstance(o, datetime.datetime):
                return date_util.dt_to_timestamp(o)
        except StandardError:
            pass
        return super(TimestampJSONEncoder, self).default(o)


class AzgFlask(Flask):
    json_encoder = TimestampJSONEncoder

app = AzgFlask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024
app.config.from_object(__name__)
app_config_data = {}
log = logging.getLogger("aziugo")


# ----------------------- Hooks -------------------------------------------

@app.before_request
def before_request():
    """
    Called before each request
    """

    # Put all precomputed data into request specific object Flask.g
    for key in app_config_data.keys():
        setattr(g, key, app_config_data[key])

    # Define wrappers for connections to database and redis
    core.api_util.DatabaseContext.get_conn()
    core.api_util.RedisContext.get_data_conn()
    core.api_util.RedisContext.get_pubsub_conn()


@app.teardown_request
def teardown_request(exception):
    if exception:
        log.exception(exception)
    core.api_util.RedisContext.clean()
    core.api_util.DatabaseContext.clean()


@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    msg = str(e) if app.debug else "Internal Error"
    if isinstance(e, HTTPException):
        code = int(e.code)
        msg = e.name
        warning_msg = e.name
        if e.description and app.debug:
            msg = e.name + ": " + e.description
            if len(e.description) < 80:
                warning_msg += ": "+e.description
        if code != 404:
            log.warning(warning_msg)
            error_util.log_error(log, e)
    else:
        error_util.log_error(log, e)
    if code == 404 and request.path.strip("/").split("/")[0] in ("v1", "admin"):
        response = jsonify({"success": 0, "error_msgs": [msg], "data": None})
    else:
        response = "<html><body><h1>" + escape(msg) + "</h1></body></html>"
    return response, code


# ---------------------- Application initialisation ------------------------

def setup_app_config(conf_data):
    # Load providers
    provider_names = json.loads(conf_data["conf"].get("general", "allowed_providers"))
    providers = {}
    for provider_name in provider_names:
        providers[provider_name] = {
            'name': provider_name,
            'type': conf_data["conf"].get("provider_"+provider_name, "type"),
            'location': conf_data["conf"].get("provider_"+provider_name, "location"),
            'default_storage': conf_data["conf"].get("provider_"+provider_name, "default_storage"),
        }
    conf_data["providers"] = providers

    # Load storages
    storage_names = json.loads(conf_data["conf"].get("general", "allowed_storages"))
    storages = {}
    for storage_name in storage_names:
        storages[storage_name] = core.api_util.get_storage(storage_name)
    conf_data["storages"] = storages
    conf_data["default_storage"] = sorted(conf_data["storages"].keys())[0]

    # Load redis config
    if util.has_filled_value(os.environ, "REDIS_HOST"):
        redis_host = os.environ["REDIS_HOST"]
    elif conf_data["conf"].has_section("redis") and conf_data["conf"].has_option("redis", "host"):
        redis_host = conf_data["conf"].get("redis", "host")
    else:
        redis_host = "localhost"
    if util.has_filled_value(os.environ, "REDIS_PORT"):
        redis_port = os.environ["REDIS_PORT"]
    elif conf_data["conf"].has_section("redis") and conf_data["conf"].has_option("redis", "port"):
        redis_port = conf_data["conf"].get("redis", "port")
    else:
        redis_port = 6379
    if util.has_filled_value(os.environ, "REDIS_DATA_DB"):
        redis_data_db = os.environ["REDIS_DATA_DB"]
    elif conf_data["conf"].has_section("redis") and conf_data["conf"].has_option("redis", "data_db"):
        redis_data_db = conf_data["conf"].get("redis", "data_db")
    else:
        redis_data_db = 0
    if util.has_filled_value(os.environ, "REDIS_PUBSUB_DB"):
        redis_pubsub_db = os.environ["REDIS_PUBSUB_DB"]
    elif conf_data["conf"].has_section("redis") and conf_data["conf"].has_option("redis", "pubsub_db"):
        redis_pubsub_db = conf_data["conf"].get("redis", "pubsub_db")
    else:
        redis_pubsub_db = 1

    core.api_util.RedisContext.set_params(api_name, full_server_name, redis_host, redis_port, redis_data_db,
                                          redis_pubsub_db)
    core.api_util.DatabaseContext.load_conf()

    # Create temp directory
    try:
        os.makedirs(conf_data["TMP_FOLDER"])
    except OSError:  # Use this strategy because sometime docker is slow to mount disk
        pass

    # Create upload file folder
    try:
        os.makedirs(os.path.join(conf_data["TMP_FOLDER"], "uploaded_files"))
    except OSError:  # Use this strategy because sometime docker is slow to mount disk
        pass


def setup_app_blueprints(flask_app):
    from api.v1 import api_v1
    from api.admin import api_admin
    from api.public import api_public

    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app)
    flask_app.register_blueprint(api_public)
    flask_app.register_blueprint(api_v1, url_prefix="/v1")
    flask_app.register_blueprint(api_admin, url_prefix="/admin")


# Load conf
api_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app_config_data["conf"] = core.api_util.get_conf()

# Main application constants
api_name = app_config_data["conf"].get('general', 'api_name')
app_config_data["WEB_ROOT"] = os.path.join(api_path, "app")
app_config_data["API_SERVER"] = app_config_data["conf"].get('general', 'server')
app_config_data["API_NAME"] = api_name
app_config_data["TMP_FOLDER"] = os.path.abspath(app_config_data["conf"].get('general', 'tmp_folder'))

app.config['PREFERRED_URL_SCHEME'] = "https"
PREFERRED_URL_SCHEME = "https"
full_server_name = app_config_data["conf"].get('general', 'server')
if full_server_name.startswith("http"):
    app.config['SERVER_NAME'] = full_server_name.split("/")[2]
    SERVER_NAME = full_server_name.split("/")[2]
else:
    app.config['SERVER_NAME'] = full_server_name.split("/")[0]
    SERVER_NAME = full_server_name.split("/")[0]


# Initialise app
setup_app_config(app_config_data)
setup_app_blueprints(app)


if __name__ == '__main__':
    core.api_util.wait_for_postgres()
    # Do general initialization here
    app.run(host='0.0.0.0')
