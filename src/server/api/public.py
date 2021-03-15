# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import os
import logging

# Specific libs
from flask import Blueprint, Response, send_file, g, abort, escape
from flask import current_app as app
from werkzeug.exceptions import HTTPException

# Project libs:
from lib import error_util


api_public = Blueprint('public', __name__)
log = logging.getLogger("aziugo")


# ----------------------- Routes -------------------------------------------
@api_public.route('/', methods=['GET'])
def home():
    return Response("<html><head></head><boby>Zephycloud API</body></html>")


@api_public.route('/up', methods=['GET'])
def up():
    return Response("<html><head></head><boby>ok</body></html>")


@api_public.route('/robots.txt', methods=['GET'])
def robots_txt():
    return Response("User-agent: *\nDisallow: /\n")


@api_public.route('/local_files/<string:storage_name>/<path:subpath>', methods=['GET'])
def local_file(storage_name, subpath):
    if storage_name not in g.storages:
        abort(404)
    storage = g.storages[storage_name]
    if storage.type != "local_filesystem":
        abort(404)
    sub_folders = subpath.strip("/").split("/")
    file_path = os.path.abspath(os.path.join(storage.path, *sub_folders))
    if not os.path.exists(file_path):
        abort(404)
    basename = os.path.basename(file_path)
    return send_file(file_path, attachment_filename=basename)


@api_public.errorhandler(Exception)
def handle_error(e):
    code = 500
    msg = str(e) if app.debug else "Internal Error"
    if isinstance(e, HTTPException):
        code = e.code
        msg = e.name
        warning_msg = e.name
        if e.description and app.debug:
            msg = e.name + ": " + e.description
            if len(e.description) < 80:
                warning_msg += ": "+e.description
        if code != 404:
            log.warning(warning_msg)
        if code == 500:
            error_util.log_error(log, e)
    else:
        error_util.log_error(log, e)
    response = "<html><body><h1>"+escape(msg)+"</h1></body></html>"
    return response, code
