# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core
import logging


# Third party
from flask import g, url_for, current_app, jsonify, abort
import werkzeug.datastructures
from werkzeug.exceptions import HTTPException

# Project specific
from lib import meta_util
import storages


log = logging.getLogger("aziugo")


def api_abort(code, error_msg=None):
    try:
        abort(code, error_msg)
        msg = error_msg
    except HTTPException as e:
        msg = e.name
        warning_msg = str(error_msg) + ": " if error_msg else ""
        warning_msg += e.name
        if e.description and current_app.debug:
            msg = e.name + ": " + e.description
            if len(e.description) < 80:
                warning_msg += ": " + e.description
        if code != 404:
            log.warning(warning_msg)
    return api_error_resp(code, msg)


def api_error_resp(code, msg):
    response = jsonify({
        "success": 0,
        "error_msgs": [msg],
        "data": None
    })
    if code in (401, 403):  # Unauthorized
        response.headers['WWW-Authenticate'] = 'Basic realm="' + str(g.API_SERVER) + '" charset="UTF-8"'
    return response, code


@meta_util.func_decorator
def api_error_handler(func, func_args, func_kwargs):
    try:
        return func(*func_args, **func_kwargs)
    except StandardError as e:
        code = 500
        msg = str(e) if current_app.debug else "Internal Error"
        if isinstance(e, HTTPException):
            code = e.code
            msg = e.name
            warning_msg = e.name
            if e.description and current_app.debug:
                msg = e.name + ": " + e.description
                if len(e.description) < 80:
                    warning_msg += ": "+e.description
            if code != 404:
                log.warning(warning_msg)
            if code == 500:
                log.exception(e)
        else:
            log.exception(e)
        return api_error_resp(code, msg)


def get_file_url(storage_name, filename, allow_missing=False):
    if storage_name not in g.storages.keys():
        log.error("Project storage " + repr(storage_name) + " is not part of known storages")
        raise RuntimeError("Storage issue")
    storage = g.storages[storage_name]
    if allow_missing:
        try:
            if storage.type == "local_filesystem":
                return url_for('public.local_file', storage_name=storage_name, subpath=filename,
                               _external=True, _scheme='https')
            else:
                return storage.get_file_url(filename)
        except storages.FileMissingError:
            return None
    else:
        if storage.type == "local_filesystem":
            return url_for('public.local_file', storage_name=storage_name, subpath=filename,
                           _external=True, _scheme='https')
        else:
            return storage.get_file_url(filename)


def get_req_params(request):
    """
    Get the parameters of a request

    :param request:     The flask request object to check
    :type request:      flask.Request
    :return:            The parameter of the request
    :rtype:             werkzeug.datastructures.CombinedMultiDict
    """
    json_params = request.get_json(silent=True)
    if not json_params:
        json_params = werkzeug.datastructures.MultiDict()
    params = werkzeug.datastructures.CombinedMultiDict([json_params, request.form])
    result = {}
    for key in params.keys():
        result[key] = params[key]
    return result


def check_request_params(request, *required_params, **kwargs):
    """
    Check a request to be valid
    It failed if a required parameter is not here,
    But it also failed if a unknown parameter is filled
    For optional parameter use the following example:

      check_json_request(request, "arg1", "arg2", optional=["optioanl_param])

    :param request:             The flask request object to check
    :type request:              flask.Request
    :param required_params:     The required parameters to check for existence
    :type required_params:      str
    :param kwargs:              Some optional fields.
                                Here the description of the fields you can use:
                                  "optional":    list[str] : the list of the optional fields
                                  "allow_files": bool : Do we allow files to be sent. Default False
                                  "strict":      bool : Do we fail on unknown parameter. Default True
    :type kwargs:               any
    :return:                    False if the request parameters are invalid
    :rtype:                     bool
    """
    optional_params = kwargs["optional"] if "optional" in kwargs else []
    allow_files = kwargs["allow_files"] if "allow_files" in kwargs else False
    strict = kwargs["strict"] if "strict" in kwargs else True

    if allow_files:
        unauthorized_file_vars = [k for k in request.files.keys() if k != "files[]"]
        if unauthorized_file_vars and strict:
            log.warning("Bad parameters: unknown file parameters " + ", ".join(unauthorized_file_vars))
            return False
    elif request.files:
        log.warning("Bad parameters: unauthorized files are sent")
        return False

    if request.args:
        log.warning("Bad parameters: found url args: "+repr(request.args.keys()))
        return False

    req_params = get_req_params(request)
    missing_params = []
    if req_params:
        for key_name in required_params:
            if key_name not in req_params.keys():
                missing_params.append(key_name)
    else:
        missing_params = required_params
    if missing_params:
        log.warning("Bad parameters: missing " + ", ".join(missing_params))
        return False

    if req_params and strict:
        unknown_params = []
        for key_name in req_params.keys():
            if key_name not in required_params and key_name not in optional_params:
                unknown_params.append(key_name)
        if unknown_params:
            log.warning("Bad parameters: unknown json parameters " + ", ".join(unknown_params))
            return False
    return True
