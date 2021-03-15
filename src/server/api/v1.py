# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core lib
import re
import logging
import base64
import os

# Specific libs
import flask
from flask import Blueprint, g, jsonify, request, url_for
from flask import current_app as app
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

# Project libs
from lib import order_by
from lib import type_util
from lib import date_util
from lib import file_util
from lib import error_util
from core import api_util
from core import web_util
import models.users
import models.provider_config
import models.projects
import models.jobs
import models.calc
import models.meshes


api_v1 = Blueprint('v1', __name__)
log = logging.getLogger("aziugo")


def abort(code, *args, **kwargs):
    if args:
        log.debug("Aborting with code " + str(code) + ", " + str(args[0]))
    else:
        log.debug("Aborting with code " + str(code) + ", without reason: " + repr(args) + ", " + repr(kwargs))
    flask.abort(code, *args, **kwargs)


def resp(data="ok"):
    """
    Return the json of the response

    :param data:        The data of the response. Optional, default "ok"
    :type data:         any
    :return:            The http response
    :rtype:             tuple[flask.Response, int]
    """
    results = (jsonify({
        "success": 1,
        "error_msgs": [],
        "data": data
    }), 200)
    # log.debug("response = "+repr(data))
    return results


# ----------------------- Hooks -------------------------------------------

@api_v1.before_request
def before_request():
    """
    Called before each request
    """

    # Authenticate
    if 'Authorization' not in request.headers:
        abort(401)
    key = base64.b64decode(re.sub(r"Basic\s", '', request.headers['Authorization']))
    if ":" not in key:
        abort(401)
    login, password = key.split(":", 1)
    user_data = models.users.authenticate(login, password)
    if not user_data:
        abort(401)

    # initialize user information
    g.user = {
        "id": user_data['id'],
        "login": login,
        "rank": user_data['user_rank']
    }


@api_v1.errorhandler(Exception)
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
    response = jsonify({
      "success": 0,
      "error_msgs": [msg],
      "data": None
    })
    if code in [401, 403]:  # Unauthorized
        response.headers['WWW-Authenticate'] = 'Basic realm="' + str(g.API_SERVER) + '" charset="UTF-8"'
    return response, code


# ----------------------- Users -------------------------------------------

@api_v1.route('/user/status/', methods=['GET'])
def user_status():
    """ Show current user information """
    # Check params
    if not web_util.check_request_params(request):
        abort(400)

    # Real work
    credit = models.users.get_credit(g.user['id'])
    return resp({
        "user_status": models.users.rank_to_str(g.user["rank"]),
        "credit": api_util.price_to_float(credit)
    })


# ----------------------- Jobs------------------------------------------------

@api_v1.route('/jobs/list/', methods=['GET', "POST"])
def job_list():
    # Check params
    if not web_util.check_request_params(request, optional=["project_codename", 'offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    project_uid = None
    if "project_codename" in params:
        if not type_util.is_string(params['project_codename']) or not params['project_codename'].strip():
            abort(400, "invalid value for project_codename")
        project_uid = params['project_codename'].strip()
    offset = 0
    if 'offset' in params.keys():
        if not type_util.ll_int(params['offset']) or int(params['offset']) < 0:
            abort(400, "invalid value for offset")
        offset = int(params['offset'])
    limit = None
    if 'limit' in params.keys():
        if not type_util.ll_int(params['limit']) or int(params['limit']) <= 0:
            abort(400, "invalid value for limit")
        limit = int(params['limit'])
    order = order_by.OrderBy(["job_id", "project_uid", "start_time", "end_time", "status"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: "+order.issue)

    # Real work
    jobs = []
    for job in models.jobs.list_jobs(g.user['id'], project_uid=project_uid, offset=offset, limit=limit, order=order):
        jobs.append({
            'job_id': int(job['id']),
            'project_name': job['project_uid'],
            'start': "-" if not job['start_time'] else date_util.format_date(job['start_time']),
            'end': "-" if not job['end_time'] else date_util.format_date(job['end_time']),
            'ncoins': api_util.price_to_float(models.jobs.get_job_consume(job['id'])) * -1,
            "status": models.jobs.job_status_to_str(job['status']),
            'progress': float(job['progress'])
        })
    return resp(jobs)


@api_v1.route('/jobs/cancel/', methods=['GET', 'POST'])
def job_cancel():
    # Check params
    if not web_util.check_request_params(request, "job_id", optional=["reason"]):
        abort(400)
    params = web_util.get_req_params(request)
    job = models.jobs.get_job(int(params['job_id']))
    if not job:
        abort(404)
    if job["user_id"] != g.user["id"]:
        abort(403, "This is not your job")

    # Real work
    log.info("Killing job "+str(job["id"])+" from user request")
    models.jobs.cancel_job(job["id"])
    return resp("canceled")


@api_v1.route('/jobs/status/', methods=['GET'])
def job_status():
    # Check params
    if not web_util.check_request_params(request, "job_id"):
        abort(400)
    params = web_util.get_req_params(request)
    job = models.jobs.get_job(int(params['job_id']))
    if not job:
        abort(404)
    if job["user_id"] != g.user["id"]:
        abort(403, "This is not your job")

    # Real work
    return resp({
        'job_id': int(job['id']),
        'project_name': job['project_uid'],
        'start': "-" if not job['start_time'] else date_util.format_date(job['start_time']),
        'end': "-" if not job['end_time'] else date_util.format_date(job['end_time']),
        'ncoins': api_util.price_to_float(models.jobs.get_job_consume(job['id'])) * -1,
        "status": models.jobs.job_status_to_str(job['status']),
        'progress': float(job['progress'])
    })


# ----------------------- Provider -------------------------------------------

@api_v1.route('/providers/list/', methods=['GET', 'POST'])
def provider_list():
    # Check params
    if not web_util.check_request_params(request, optional=['offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    offset = 0
    if 'offset' in params.keys():
        if not type_util.ll_int(params['offset']) or int(params['offset']) < 0:
            abort(400, "invalid value for offset")
        offset = int(params['offset'])
    limit = None
    if 'limit' in params.keys():
        if not type_util.ll_int(params['limit']) or int(params['limit']) <= 0:
            abort(400, "invalid value for limit")
        limit = int(params['limit'])
    order = order_by.OrderBy(["name", "location"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: "+order.issue)

    # Real work
    result = []
    for provider in g.providers.values():
        result.append({"name": provider['name'], "location": provider['location']})
    order.sort_list_in_place(result)
    result = result[offset:(offset+limit if limit > 1 else None)]
    return resp(result)


@api_v1.route('/providers/details/', methods=['GET', 'POST'])
def provider_detail():
    # Check params
    if not web_util.check_request_params(request, "provider"):
        abort(400)
    params = web_util.get_req_params(request)
    if params["provider"] not in g.providers.keys():
        abort(404)

    # Real work
    operations = models.provider_config.list_operations(params["provider"], g.user["rank"], include_machines=True)
    machines = models.provider_config.list_machines(params["provider"])
    if not machines:
        machines = []
    prices = models.provider_config.list_machine_prices(params["provider"], [m["machine_code"] for m in machines],
                                                        models.users.all_ranks())
    if not prices:
        prices = []
    granularity_list = set([p["sec_granularity"] for p in prices])
    if len(granularity_list) == 0:
        log.warning("No prices for for provider " + str(params["provider"]))
        granularity = 300
    elif len(granularity_list) > 1:
        log.warning("Multiple granularity for provider "+str(params["provider"]))
        granularity = max(*granularity_list)
    else:
        granularity, = granularity_list

    running_machines = models.jobs.get_running_machines_list(params["provider"])
    machine_description_list = []
    for machine in machines:
        running = running_machines[machine["machine_code"]] if machine["machine_code"] in running_machines.keys() else 0
        spot_index = 0.0
        if params["provider"].endswith("_spot"):
            spot_index = models.provider_config.get_spot_index(params["provider"], machine["machine_code"])
        machine_descr = {
            "name": machine["machine_code"],
            "cores": machine["nbr_cores"],
            "ram": api_util.bytes_to_gbytes(machine["ram_size"]),
            "availability": int(machine["nbr_available"]) - running,
            "availability_max": machine["nbr_available"],
            "spot_index": spot_index,
            "prices": {}
        }
        for price in prices:
            if price["machine_uid"] != machine["uid"]:
                continue
            float_price = api_util.price_to_float(price["sec_price"])
            machine_descr["prices"][models.users.rank_to_str(price["user_rank"])] = float_price*3600
        machine_description_list.append(machine_descr)
    machine_description_list = sorted(machine_description_list, key=lambda x: (x["cores"], x["ram"]))

    return resp({
        'granularity': granularity,
        'fix_prices': {op["operation_name"]: api_util.price_to_float(op["fixed_cost"]) for op in operations},
        'configurations': {
            op["operation_name"]: {
                "cluster": op["cluster_limit"],
                "machines": op["machines"]
            } for op in operations if op["machines"] and op["cluster_limit"]},
        "machines_list": machine_description_list
    })


@api_v1.route('/provider/availability/', methods=['GET', 'POST'])
def provider_availability():
    # Check params
    if not web_util.check_request_params(request, "provider"):
        abort(400)
    params = web_util.get_req_params(request)
    if params["provider"] not in g.providers.keys():
        abort(404)

    # Real work
    result = {}
    machines = models.provider_config.list_machines(params["provider"])
    running_machines = models.jobs.get_running_machines_list(params["provider"])
    if not machines:
        return resp(result)
    for machine in machines:
        machine_code = machine["machine_code"]
        running = running_machines[machine_code] if machine_code in running_machines.keys() else 0
        result[machine_code] = int(machine["nbr_available"]) - running
    return resp(result)


# ----------------------- Storage -------------------------------------------

@api_v1.route('/storages/list/', methods=['GET'])
def storage_list():
    # Check params
    if not web_util.check_request_params(request, optional=['offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    offset = 0
    if 'offset' in params.keys():
        if not type_util.ll_int(params['offset']) or int(params['offset']) < 0:
            abort(400, "invalid value for offset")
        offset = int(params['offset'])
    limit = None
    if 'limit' in params.keys():
        if not type_util.ll_int(params['limit']) or int(params['limit']) <= 0:
            abort(400, "invalid value for limit")
        limit = int(params['limit'])
    order = order_by.OrderBy(["name", "location", "type"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)

    # Real work
    result = []
    for storage in g.storages.values():
        result.append({"name": storage.name, "type": storage.type, "location": storage.location})
    order.sort_list_in_place(result)
    result = result[offset:(offset + limit if limit > 1 else None)]
    return resp(result)


# ----------------------- Project -------------------------------------------

@api_v1.route('/project/status/', methods=['GET', 'POST'])
def project_status():
    # Check params
    if not web_util.check_request_params(request, 'project_codename'):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404)

    # Real work
    spent = models.projects.get_already_spent(g.user['id'], params['project_codename'])

    analyzed_data_url = None
    if project['status'] == models.projects.PROJECT_STATUS_ANALYSED:
        if project["storage"] not in g.storages.keys():
            log.error("Project storage "+repr(project["storage"])+" is not part of known storages: " +
                      repr(g.storages.keys()))
            raise RuntimeError("Storage issue")
        file_info = models.projects.get_file_by_key(g.user['id'], project["uid"], models.projects.PROJECT_FILE_ANALYSED)
        if not file_info:
            log.error("Not analysed data in project file list")
            raise RuntimeError("Storage issue")
        filename = file_info['filename']
        storage = g.storages[project["storage"]]
        if storage.type == "local_filesystem":
            analyzed_data_url = url_for('public.local_file', storage_name=project["storage"], subpath=filename,
                                        _external=True, _scheme='https')
        else:
            analyzed_data_url = storage.get_file_url(filename)

    return resp({
        'project_status': models.projects.project_status_to_str(project['status']),
        'project_url': analyzed_data_url,
        'already_spent': api_util.price_to_float(spent)
    })


@api_v1.route('/project/create_and_analyse/', methods=['POST'])
def create_and_analyse_project():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', "provider", 'machine', 'nbr_machines',
                                         optional=['storage'], allow_files=True):
        log.warning("Bad params: "+repr(web_util.get_req_params(request)))
        abort(400, "Bad params")
    params = web_util.get_req_params(request)
    storage_name = params["storage"] if "storage" in params else None
    uploaded_files = request.files.getlist("files[]")
    if not uploaded_files:
        log.warning("No file sent with request /project/create_and_analyse")
        abort(400, "No files")
    if len(uploaded_files) != 1:
        log.warning("Too many uploaded files")
        abort(400, "Too many uploaded files")
    if not type_util.ll_int(params['nbr_machines']) or int(params['nbr_machines']) <= 0:
        log.warning("bad parameter nbr_machines")
        abort(400, "bad parameter nbr_machines")
    if params["provider"] not in g.providers.keys():
        log.warning("unknown provider "+str(params["provider"]))
        abort(404, "unknown provider "+str(params["provider"]))
    if storage_name is None:
        storage_name = g.providers[params["provider"]]['default_storage']
        if storage_name is None:
            storage_name = g.default_storage
    elif storage_name not in g.storages.keys():
        log.warning("unknown storage " + str(storage_name))
        abort(404, "unknown storage " + str(storage_name))
    machine = models.provider_config.get_machine(params["provider"], params["machine"])
    if not machine:
        log.warning("unknown machine " + str(params["machine"]) + " for provider " + str(params["provider"]))
        abort(404, "unknown machine " + str(params["machine"]) + " for provider " + str(params["provider"]))

    # Real work
    if models.users.get_credit(g.user['id']) <= 0:
        log.warning("not enough credits")
        abort(400, "not enough credits")
    project = models.projects.create_project(g.user['id'], params['project_codename'], storage_name)
    if not project:
        log.warning("Project already exists: "+repr(params['project_codename']))
        abort(400, "Project already exists")
    operation = models.provider_config.get_operation(params["provider"], "anal", g.user["rank"], True)
    if not operation:
        log.error("No operation 'anal' defined for provider "+params["provider"])
        abort(400, "No operation configured for this provider")
    if models.users.get_credit(g.user['id']) <= int(operation['fixed_cost']):
        log.warning("not enough credits")
        abort(400, "not enough credits")

    if int(operation['cluster_limit']) < int(params["nbr_machines"]):
        log.warning("Too many machines requested for cluster limit")
        abort(400, "You requested too many machines")
    if params["machine"] not in operation['machines']:
        log.warning("Machine "+repr(params["machine"])+" not allowed for operation 'anal'")
        abort(400, "Machine "+repr(params["machine"])+" not allowed for operation 'anal'")
    used_machines = models.jobs.get_running_machines(params['provider'], machine['machine_code'])
    available = int(machine['nbr_available']) - used_machines
    if int(params['nbr_machines']) > available:
        log.warning("sorry, we don't have the resources available right now")
        abort(400, "sorry, we don't have the resources available right now")

    price = models.provider_config.get_machine_price(params["provider"], machine["machine_code"], g.user["rank"])
    if not price:
        log.error("No price configured for machine "+repr(machine["machine_code"])+" of provider " +
                  params["provider"]+" for user rank "+g.user["rank"])
        abort(500, "No price configured")

    provider_cost = models.provider_config.get_machine_provider_cost(params["provider"], machine["machine_code"])
    provider_cost_id = provider_cost["id"] if provider_cost else None
    if provider_cost_id is None:
        log.warning("No cost detected for " + repr(machine["machine_code"]) + " of provider " + params["provider"])

    # Save uploaded file
    uploaded_file = uploaded_files[0]
    uploaded_file_dir = os.path.join(g.TMP_FOLDER, "uploaded_files")
    prefix, suffix = os.path.splitext(secure_filename(uploaded_file.filename))
    tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    uploaded_file.save(tmp_file_path)

    # Create job and add new task
    job = models.jobs.create_job(g.user['id'], params['project_codename'], operation['id'],
                                 provider_cost_id, price['id'], params["nbr_machines"])
    models.jobs.push_task(job["id"], models.jobs.TASK_UPLOAD_AND_ANALYSE,
                          project_file=tmp_file_path,
                          provider=params["provider"],
                          machine=params["machine"],
                          nbr_machines=params["nbr_machines"],
                          storage=storage_name,
                          client_login=g.user['login'],
                          client_ip=request.remote_addr,
                          api_version="1")
    return resp(int(job["id"]))


@api_v1.route('/project/create_and_link/', methods=['POST'])
def create_and_link_project():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', optional=['storage'], allow_files=True):
        abort(400)
    params = web_util.get_req_params(request)
    storage_name = params["storage"] if "storage" in params else None
    uploaded_files = request.files.getlist("files[]")
    if not uploaded_files:
        log.warning("No file sent with request /project/create_and_link")
        abort(400)
    if len(uploaded_files) < 2:
        abort(400, "Missing uploaded files")
    if len(uploaded_files) > 2:
        abort(400, "Too many uploaded files")
    if storage_name is None:
        storage_name = g.providers[params["provider"]]['default_storage']
        if storage_name is None:
            storage_name = g.default_storage
    elif storage_name not in g.storages.keys():
        abort(404, "unknown storage " + str(storage_name))

    # Real work
    if models.users.get_credit(g.user['id']) <= 0:
        abort(400, "not enough credits")

    project = models.projects.create_project(g.user['id'], params['project_codename'], storage_name)
    if not project:
        abort(400, "Project already exists")

    unused_provider = g.providers.keys()[0]
    operation = models.provider_config.get_operation(unused_provider, "anal", g.user["rank"], True)
    if not operation:
        log.error("No operation 'anal' defined for provider " + unused_provider)
        abort(400, "No operation configured for this provider")
    if models.users.get_credit(g.user['id']) <= int(operation['fixed_cost']):
        abort(400, "not enough credits")

    # Save uploaded file
    uploaded_file_dir = os.path.join(g.TMP_FOLDER, "uploaded_files")
    project_file = uploaded_files[0]
    prefix, suffix = os.path.splitext(secure_filename(project_file.filename))
    project_tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    project_file.save(project_tmp_file_path)
    anal_file = uploaded_files[1]
    prefix, suffix = os.path.splitext(secure_filename(anal_file.filename))
    anal_tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    anal_file.save(project_tmp_file_path)

    # Create job and add new task
    job = models.jobs.create_job(g.user['id'], params['project_codename'], operation['id'])
    models.jobs.push_task(job["id"], models.jobs.TASK_UPLOAD_AND_LINK,
                          project_file=project_tmp_file_path,
                          anal_file=anal_tmp_file_path,
                          storage=storage_name,
                          client_login=g.user['login'],
                          client_ip=request.remote_addr,
                          api_version="1")
    return resp(int(job["id"]))


@api_v1.route('/project/analyse/', methods=['POST'])
def analyse_project():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', "provider", 'machine', 'nbr_machines',
                                         allow_files=True):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['nbr_machines']) or int(params['nbr_machines']) <= 0:
        abort(400, "bad parameter nbr_machines")
    if params["provider"] not in g.providers.keys():
        abort(404, "unknown provider "+str(params["provider"]))
    machine = models.provider_config.get_machine(params["provider"], params["machine"])
    if not machine:
        abort(404, "unknown machine " + str(params["machine"]) + " for provider " + str(params["provider"]))
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "Project doesn't exists")
    uploaded_files = request.files.getlist("files[]")
    if not uploaded_files:
        log.warning("No file sent with request /project/create_and_analyse")
        abort(400)
    if len(uploaded_files) != 1:
        abort(400, "Too many uploaded files")

    # Real work
    if models.users.get_credit(g.user['id']) <= 0:
        abort(400, "not enough credits")
    operation = models.provider_config.get_operation(params["provider"], "anal", g.user["rank"], True)
    if not operation:
        log.error("No operation 'anal' defined for provider "+params["provider"])
        abort(400, "No operation configured for this provider")
    if models.users.get_credit(g.user['id']) <= int(operation['fixed_cost']):
        abort(400, "not enough credits")
    if int(operation['cluster_limit']) < int(params["nbr_machines"]):
        log.warning("Too many machines requested for cluster limit")
        abort(400, "You requested too many machines")
    if params["machine"] not in operation['machines']:
        abort(400, "Machine "+repr(params["machine"])+" not allowed for operation 'anal'")
    used_machines = models.jobs.get_running_machines(params['provider'], machine['machine_code'])
    available = int(machine['nbr_available']) - used_machines
    if int(params['nbr_machines']) > available:
        abort(400, "sorry, we don't have the resources available right now")

    price = models.provider_config.get_machine_price(params["provider"], machine["machine_code"], g.user["rank"])
    if not price:
        log.error("No price configured for machine "+repr(machine["machine_code"])+" of provider " +
                  params["provider"]+" for user rank "+g.user["rank"])
        abort(500, "No price configured")

    provider_cost = models.provider_config.get_machine_provider_cost(params["provider"], machine["machine_code"])
    provider_cost_id = provider_cost["id"] if provider_cost else None
    if provider_cost_id is None:
        log.warning("No cost detected for " + repr(machine["machine_code"]) + " of provider " + params["provider"])

    # Save uploaded file
    uploaded_file = uploaded_files[0]
    uploaded_file_dir = os.path.join(g.TMP_FOLDER, "uploaded_files")
    prefix, suffix = os.path.splitext(secure_filename(uploaded_file.filename))
    tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    uploaded_file.save(tmp_file_path)

    # Create job and add new task
    job = models.jobs.create_job(g.user['id'], params['project_codename'], operation['id'],
                                 provider_cost_id, price['id'], params["nbr_machines"])
    models.jobs.push_task(job["id"], models.jobs.TASK_UPLOAD_AND_ANALYSE,
                          project_file=tmp_file_path,
                          provider=params["provider"],
                          machine=params["machine"],
                          nbr_machines=params["nbr_machines"],
                          storage=project['storage'],
                          client_login=g.user['login'],
                          client_ip=request.remote_addr,
                          api_version="1")
    return resp(int(job["id"]))


@api_v1.route('/project/remove/', methods=['POST'])
def project_delete():
    # Check params
    if not web_util.check_request_params(request, 'project_codename'):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))

    # Real work
    models.projects.delete_project(g.user['id'], params['project_codename'])
    return resp()

# --------------------- Meshes -----------------------------


@api_v1.route('/mesh/create/', methods=['POST'])
def create_mesh():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', "mesh_name", 'provider', 'machine',
                                         "nbr_machines", allow_files=True):
        abort(400)
    params = web_util.get_req_params(request)
    uploaded_files = request.files.getlist("files[]")
    if not uploaded_files:
        log.warning("No file sent with request /project/create_and_analyse")
        abort(400)
    if len(uploaded_files) != 1:
        abort(400, "Too many uploaded files")
    if not type_util.ll_int(params['nbr_machines']) or int(params['nbr_machines']) <= 0:
        abort(400, "bad parameter nbr_machines")
    if params["provider"] not in g.providers.keys():
        abort(404, "unknown provider "+str(params["provider"]))
    machine = models.provider_config.get_machine(params["provider"], params["machine"])
    if not machine:
        abort(404, "unknown machine " + str(params["machine"]) + " for provider " + str(params["provider"]))
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    if project['status'] != models.projects.PROJECT_STATUS_ANALYSED:
        abort(400, "Project is not analysed")

    # Real work
    if models.users.get_credit(g.user['id']) <= 0:
        abort(400, "not enough credits")

    log.info("Creating mesh " + str(params['mesh_name']) + " of project " + params['project_codename'] +
             " from web api request")
    models.meshes.create_mesh(g.user['id'], params['project_codename'], params['mesh_name'], overwrite=True)
    operation = models.provider_config.get_operation(params["provider"], "mesh", g.user["rank"], True)
    if not operation:
        log.error("No operation 'mesh' defined for provider "+params["provider"])
        abort(400, "No operation configured for this provider")
    if models.users.get_credit(g.user['id']) <= int(operation['fixed_cost']):
        abort(400, "not enough credits")
    if int(operation['cluster_limit']) < int(params["nbr_machines"]):
        log.warning("Too many machines requested for cluster limit")
        abort(400, "You requested too many machines")
    if params["machine"] not in operation['machines']:
        abort(400, "Machine "+repr(params["machine"])+" not allowed for operation 'mesh'")
    used_machines = models.jobs.get_running_machines(params['provider'], machine['machine_code'])
    available = int(machine['nbr_available']) - used_machines
    if int(params['nbr_machines']) > available:
        abort(400, "sorry, we don't have the resources available right now")

    price = models.provider_config.get_machine_price(params["provider"], machine["machine_code"], g.user["rank"])
    if not price:
        log.error("No price configured for machine "+repr(machine["machine_code"])+" of provider " +
                  params["provider"]+" for user rank "+g.user["rank"])
        abort(500, "No price configured")

    provider_cost = models.provider_config.get_machine_provider_cost(params["provider"], machine["machine_code"])
    provider_cost_id = provider_cost["id"] if provider_cost else None
    if provider_cost_id is None:
        log.warning("No cost detected for " + repr(machine["machine_code"]) + " of provider " + params["provider"])

    # Save uploaded file
    uploaded_file = uploaded_files[0]
    uploaded_file_dir = os.path.join(g.TMP_FOLDER, "uploaded_files")
    prefix, suffix = os.path.splitext(secure_filename(uploaded_file.filename))
    tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    uploaded_file.save(tmp_file_path)

    # Create job and add new task
    job = models.jobs.create_job(g.user['id'], params['project_codename'], operation['id'],
                                 provider_cost_id, price['id'], params["nbr_machines"])
    models.jobs.push_task(job["id"], models.jobs.TASK_MESH,
                          project_codename=params['project_codename'],
                          mesh_param_file=tmp_file_path,
                          mesh_name=params["mesh_name"],
                          provider_name=params["provider"],
                          machine=params["machine"],
                          nbr_machines=params["nbr_machines"],
                          client_login=g.user['login'],
                          client_ip=request.remote_addr,
                          api_version="1")
    return resp(int(job["id"]))


@api_v1.route('/mesh/list/', methods=['GET', 'POST'])
def list_meshes():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', optional=['offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    offset = 0
    if 'offset' in params.keys():
        if not type_util.ll_int(params['offset']) or int(params['offset']) < 0:
            abort(400, "invalid value for offset")
        offset = int(params['offset'])
    limit = None
    if 'limit' in params.keys():
        if not type_util.ll_int(params['limit']) or int(params['limit']) <= 0:
            abort(400, "invalid value for limit")
        limit = int(params['limit'])
    order = order_by.OrderBy(["name", "status"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)

    meshes = models.meshes.get_project_meshes(g.user['id'], project['uid'], offset=offset, limit=limit, order=order)
    result = []
    for mesh in meshes:
        result.append({
            'name': mesh['name'],
            'status': models.meshes.status_to_str(mesh['status']),
            'mesh_parameters': 'TODO ZOPEN'
        })
    return resp(result)


@api_v1.route('/mesh/show/', methods=['GET', 'POST'])
def get_mesh():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', 'mesh_name'):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    mesh = models.meshes.get_mesh(g.user['id'], params['project_codename'], params['mesh_name'])
    if not mesh:
        abort(404, "unknown mesh " + str(params["mesh_name"]))

    if mesh['status'] != models.meshes.STATUS_COMPUTED:
        return resp({
            'status': models.meshes.status_to_str(mesh['status']),
            'mesh_data_url': None,
            'preview_url': None
        })

    result_file_info = models.projects.get_file_by_id(g.user['id'], params['project_codename'], mesh['result_file_id'])
    if not result_file_info:
        abort(404, "Unable to find the result file")
    preview_file_info = models.projects.get_file_by_id(g.user['id'], params['project_codename'],
                                                       mesh['preview_file_id'])
    if not preview_file_info:
        abort(404, "Unable to find the preview file")

    storage = g.storages[project["storage"]]
    filename = str(result_file_info['filename'])
    if storage.type == "local_filesystem":
        mesh_data_url = url_for('public.local_file', storage_name=project["storage"], subpath=filename,
                                _external=True, _scheme='https')
    else:
        mesh_data_url = storage.get_file_url(filename)

    filename = str(preview_file_info['filename'])
    if storage.type == "local_filesystem":
        preview_url = url_for('public.local_file', storage_name=project["storage"], subpath=filename,
                              _external=True, _scheme='https')
    else:
        preview_url = storage.get_file_url(filename)

    return resp({
        'status': models.meshes.status_to_str(mesh['status']),
        'mesh_data_url': mesh_data_url,
        'preview_url': preview_url
    })


@api_v1.route('/mesh/remove/', methods=['POST'])
def mesh_delete():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', 'mesh_name'):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    mesh = models.meshes.get_mesh(g.user['id'], params['project_codename'], params['mesh_name'])
    if not mesh:
        abort(404, "unknown mesh " + str(params["mesh_name"]))

    # Real work
    models.meshes.delete_mesh(g.user['id'], params['project_codename'], mesh['name'])
    return resp()


# --------------------- Calculations -----------------------------

@api_v1.route('/calculation/run/', methods=['GET', 'POST'])
def calculation_run():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', 'mesh_name', 'calculation_name', 'provider',
                                         'machine', 'nbr_machines', optional=['split_results'], allow_files=True):
        abort(400)
    params = web_util.get_req_params(request)
    uploaded_files = request.files.getlist("files[]")
    if not uploaded_files:
        log.warning("No file sent with request /calculation/run")
        abort(400)
    if len(uploaded_files) != 1:
        abort(400, "Too many uploaded files")
    if not type_util.ll_int(params['nbr_machines']) or int(params['nbr_machines']) <= 0:
        abort(400, "bad parameter nbr_machines")
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    mesh = models.meshes.get_mesh(g.user['id'], params['project_codename'], params['mesh_name'])
    if not mesh:
        abort(404, "unknown mesh " + str(params["mesh_name"]))
    if mesh['status'] != models.meshes.STATUS_COMPUTED:
        abort(400, "Mesh " + str(params["mesh_name"]) + " is not ready")
    if not mesh["result_file_id"]:
        log.error("Mesh "+mesh['id']+" seems corrupted: no 'result_file_id'")
        abort(400, "Mesh " + str(params["mesh_name"]) + " is not ready")
    if params["provider"] not in g.providers.keys():
        abort(404, "unknown provider "+str(params["provider"]))
    machine = models.provider_config.get_machine(params["provider"], params["machine"])
    if not machine:
        abort(404, "unknown machine " + str(params["machine"]) + " for provider " + str(params["provider"]))
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    if project['status'] != models.projects.PROJECT_STATUS_ANALYSED:
        abort(400, "Project is not analysed")
    operation = models.provider_config.get_operation(params["provider"], "calc", g.user["rank"], True)
    if not operation:
        log.error("No operation 'calc' defined for provider " + params["provider"])
        abort(400, "No operation configured for this provider")
    if models.users.get_credit(g.user['id']) <= int(operation['fixed_cost']):
        abort(400, "not enough credits")
    if params["machine"] not in operation['machines']:
        abort(400, "Machine " + repr(params["machine"]) + " not allowed for operation 'mesh'")
    if int(operation['cluster_limit']) < int(params["nbr_machines"]):
        log.warning("Too many machines requested for cluster limit")
        abort(400, "You requested too many machines")
    split_results = False
    if "split_results" in params.keys():
        if not type_util.ll_bool(params['split_results']):
            log.warning("Bad param split_results")
            abort(400, "Bad param split_results")
        split_results = type_util.to_bool(params['split_results'])
    used_machines = models.jobs.get_running_machines(params['provider'], machine['machine_code'])
    available = int(machine['nbr_available']) - used_machines
    if int(params['nbr_machines']) > available:
        abort(400, "sorry, we don't have the resources available right now")

    # Real work
    if models.users.get_credit(g.user['id']) <= 0:
        abort(400, "not enough credits")
    calc = models.calc.create_calc(g.user['id'], params['project_codename'], mesh['id'], params['calculation_name'])
    price = models.provider_config.get_machine_price(params["provider"], machine["machine_code"], g.user["rank"])
    if not price:
        log.error("No price configured for machine " + repr(machine["machine_code"]) + " of provider " +
                  params["provider"] + " for user rank " + g.user["rank"])
        abort(500, "No price configured")

    provider_cost = models.provider_config.get_machine_provider_cost(params["provider"], machine["machine_code"])
    provider_cost_id = provider_cost["id"] if provider_cost else None
    if provider_cost_id is None:
        log.warning("No cost detected for " + repr(machine["machine_code"]) + " of provider " + params["provider"])

    # Save uploaded file
    uploaded_file = uploaded_files[0]
    uploaded_file_dir = os.path.join(g.TMP_FOLDER, "uploaded_files")
    prefix, suffix = os.path.splitext(secure_filename(uploaded_file.filename))
    tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    uploaded_file.save(tmp_file_path)

    # Create job and add new task
    job = models.jobs.create_job(g.user['id'], params['project_codename'], operation['id'],
                                 provider_cost_id, price['id'], params["nbr_machines"])
    models.jobs.push_task(job["id"], models.jobs.TASK_CALC,
                          project_codename=params['project_codename'],
                          mesh_name=mesh["name"],
                          calc_id=calc["id"],
                          calc_param_file=tmp_file_path,
                          provider_name=params["provider"],
                          machine=params["machine"],
                          nbr_machines=params["nbr_machines"],
                          split_results=split_results,
                          client_login=g.user['login'],
                          client_ip=request.remote_addr,
                          api_version="1")
    return resp({
        "calculation_id": int(calc['id']),
        "job_id": int(job["id"])
    })


@api_v1.route('/calculation/restart/', methods=['GET', 'POST'])
def calculation_restart():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', 'calculation_name', 'provider',
                                         'machine', 'nbr_machines', "nbr_iterations", optional=['split_results'],
                                         allow_files=True):
        abort(400)
    params = web_util.get_req_params(request)
    uploaded_files = request.files.getlist("files[]")
    if not uploaded_files:
        log.warning("No file sent with request /calculation/restart")
        abort(400)
    if len(uploaded_files) != 1:
        abort(400, "Too many uploaded files")
    if not type_util.ll_int(params['nbr_machines']) or int(params['nbr_machines']) <= 0:
        abort(400, "bad parameter nbr_machines")
    if not type_util.ll_int(params['nbr_iterations']) or int(params['nbr_iterations']) <= 0:
        abort(400, "bad parameter nbr_iterations")
    split_results = False
    if "split_results" in params.keys():
        if not type_util.ll_bool(params['split_results']):
            log.warning("Bad param split_results")
            abort(400, "Bad param split_results")
        split_results = type_util.to_bool(params['split_results'])
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    if project['status'] != models.projects.PROJECT_STATUS_ANALYSED:
        abort(400, "Project is not analysed")
    calc = models.calc.get_calc_by_name(g.user['id'], params['project_codename'], params['calculation_name'])
    if not calc:
        abort(404, "unknown calculation " + str(params["calculation_name"]))
    if calc['status'] not in (models.calc.STATUS_COMPUTED, models.calc.STATUS_STOPPED):
        abort(400, "Calculation " + str(params["calculation_name"]) + " is not ready")
    if params["provider"] not in g.providers.keys():
        abort(404, "unknown provider "+str(params["provider"]))
    machine = models.provider_config.get_machine(params["provider"], params["machine"])
    if not machine:
        abort(404, "unknown machine " + str(params["machine"]) + " for provider " + str(params["provider"]))
    operation = models.provider_config.get_operation(params["provider"], "calc", g.user["rank"], True)
    if not operation:
        log.error("No operation 'calc' defined for provider " + params["provider"])
        abort(400, "No operation configured for this provider")
    if models.users.get_credit(g.user['id']) <= int(operation['fixed_cost']):
        abort(400, "not enough credits")
    if params["machine"] not in operation['machines']:
        abort(400, "Machine " + repr(params["machine"]) + " not allowed for operation 'mesh'")
    if int(operation['cluster_limit']) < int(params["nbr_machines"]):
        log.warning("Too many machines requested for cluster limit")
        abort(400, "You requested too many machines")
    price = models.provider_config.get_machine_price(params["provider"], machine["machine_code"], g.user["rank"])
    if not price:
        log.error("No price configured for machine " + repr(machine["machine_code"]) + " of provider " +
                  params["provider"] + " for user rank " + g.user["rank"])
        abort(500, "No price configured")
    used_machines = models.jobs.get_running_machines(params['provider'], machine['machine_code'])
    available = int(machine['nbr_available']) - used_machines
    if int(params['nbr_machines']) > available:
        abort(400, "sorry, we don't have the resources available right now")

    # Real work
    if models.users.get_credit(g.user['id']) <= 0:
        abort(400, "not enough credits")
    provider_cost = models.provider_config.get_machine_provider_cost(params["provider"], machine["machine_code"])
    provider_cost_id = provider_cost["id"] if provider_cost else None
    if provider_cost_id is None:
        log.warning("No cost detected for " + repr(machine["machine_code"]) + " of provider " + params["provider"])

    # Save uploaded file
    uploaded_file = uploaded_files[0]
    uploaded_file_dir = os.path.join(g.TMP_FOLDER, "uploaded_files")
    prefix, suffix = os.path.splitext(secure_filename(uploaded_file.filename))
    tmp_file_path = file_util.unique_filename(dir=uploaded_file_dir, prefix=prefix, suffix=suffix)
    uploaded_file.save(tmp_file_path)

    # Create job and add new task
    job = models.jobs.create_job(g.user['id'], params['project_codename'], operation['id'], provider_cost_id,
                                 price['id'], params["nbr_machines"])

    models.jobs.push_task(job["id"], models.jobs.TASK_RESTART_CALC,
                          project_codename=params['project_codename'],
                          calc_id=calc["id"],
                          calc_param_file=tmp_file_path,
                          provider_name=params["provider"],
                          machine=params["machine"],
                          nbr_machines=int(params["nbr_machines"]),
                          nbr_iterations=int(params['nbr_iterations']),
                          split_results=split_results,
                          client_login=g.user['login'],
                          client_ip=request.remote_addr,
                          api_version="1")

    return resp({
        "job_id": int(job["id"])
    })


@api_v1.route('/calculation/show/', methods=['GET', 'POST'])
def calculation_show():
    # Check params
    if not web_util.check_request_params(request, "project_codename", "calculation_name"):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    calc = models.calc.get_calc_by_name(g.user['id'], params['project_codename'], params['calculation_name'])
    if not calc:
        abort(404, "unknown calculation " + str(params["calculation_name"]))

    # Real work
    storage = g.storages[project["storage"]]
    follow_url = None
    follow_date = None
    if calc['status_file_id'] is not None:
        follow_file = models.projects.get_file_by_id(g.user['id'], params['project_codename'], calc['status_file_id'])
        if not follow_file:
            log.warning("calculation status file is missing for calculation "+str(calc['id']))
        else:
            follow_date = follow_file['change_date']
            if storage.type == "local_filesystem":
                follow_url = url_for('public.local_file', storage_name=project["storage"],
                                     subpath=follow_file['filename'], _external=True, _scheme='https')
            else:
                follow_url = storage.get_file_url(follow_file['filename'])

    result_url = None
    if calc['result_file_id'] is not None:
        result_file = models.projects.get_file_by_id(g.user['id'], params['project_codename'], calc['result_file_id'])
        if not result_file:
            log.warning("calculation result file is missing for calculation "+str(calc['id']))
        elif storage.type == "local_filesystem":
            result_url = url_for('public.local_file', storage_name=project["storage"],
                                 subpath=result_file['filename'], _external=True, _scheme='https')
        else:
            result_url = storage.get_file_url(result_file['filename'])

    iterations_url = None
    if calc['iterations_file_id'] is not None:
        iterations_file = models.projects.get_file_by_id(g.user['id'], params['project_codename'],
                                                         calc['iterations_file_id'])
        if not iterations_file:
            # log.warning("calculation iterations file is missing for calculation " + str(calc['id']))
            pass
        elif storage.type == "local_filesystem":
            iterations_url = url_for('public.local_file', storage_name=project["storage"],
                                     subpath=iterations_file['filename'], _external=True, _scheme='https')
        else:
            iterations_url = storage.get_file_url(iterations_file['filename'])

    reduce_url = None
    if calc['iterations_file_id'] is not None:
        reduce_file = models.projects.get_file_by_id(g.user['id'], params['project_codename'], calc['reduce_file_id'])
        if not reduce_file:
            # log.warning("calculation iterations file is missing for calculation " + str(calc['id']))
            pass
        elif storage.type == "local_filesystem":
            reduce_url = url_for('public.local_file', storage_name=project["storage"],
                                 subpath=reduce_file['filename'], _external=True, _scheme='https')
        else:
            reduce_url = storage.get_file_url(reduce_file['filename'])

    nbr_coins = 0
    if calc['job_id']:
        job = models.jobs.get_job(int(calc['job_id']))
        if job:
            nbr_coins = api_util.price_to_float(models.jobs.get_job_consume(job['id'])) * -1

    return resp({
        "calculation_id": calc['id'],
        "job_id": calc['job_id'],
        "status": models.calc.status_to_str(calc['status']),
        "start_date": date_util.dt_to_timestamp(calc['last_start_date']),
        "stop_date": date_util.dt_to_timestamp(calc['last_stop_date']),
        "follow_url": follow_url,
        "follow_date": date_util.dt_to_timestamp(follow_date),
        "result_url": result_url,
        "iterations_url": iterations_url,
        "reduce_url": reduce_url,
        'nbr_coins': nbr_coins,
    })


@api_v1.route('/calculation/stop/', methods=['GET', 'POST'])
def calculation_stop():
    # Check params
    if not web_util.check_request_params(request, "project_codename", "calculation_name"):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    calc = models.calc.get_calc_by_name(g.user['id'], params['project_codename'], params['calculation_name'])
    if not calc:
        abort(404, "unknown calculation " + str(params["calculation_name"]))

    # Real work
    models.calc.set_calc_status(g.user['id'], params['project_codename'], calc['name'], models.calc.STATUS_STOPPED)
    return resp()


@api_v1.route('/calculation/remove/', methods=['POST'])
def calculation_delete():
    # Check params
    if not web_util.check_request_params(request, "project_codename", "calculation_name"):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    calc = models.calc.get_calc_by_name(g.user['id'], params['project_codename'], params['calculation_name'])
    if not calc:
        abort(404, "unknown calculation " + str(params["calculation_name"]))

    # Real work
    models.calc.delete_calc(g.user['id'], params['project_codename'], calc['name'])
    return resp()


@api_v1.route('/calculation/list/', methods=['GET', 'POST'])
def list_calc():
    # Check params
    if not web_util.check_request_params(request, 'project_codename', optional=['offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    project = models.projects.get_project(g.user['id'], params['project_codename'])
    if not project:
        abort(404, "unknown project " + str(params["project_codename"]))
    offset = 0
    if 'offset' in params.keys():
        if not type_util.ll_int(params['offset']) or int(params['offset']) < 0:
            abort(400, "invalid value for offset")
        offset = int(params['offset'])
    limit = None
    if 'limit' in params.keys():
        if not type_util.ll_int(params['limit']) or int(params['limit']) <= 0:
            abort(400, "invalid value for limit")
        limit = int(params['limit'])
    order = order_by.OrderBy(["name", "status"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)

    calculations = models.calc.get_project_calculations(g.user['id'], project['uid'],
                                                        offset=offset, limit=limit, order=order)
    result = []
    for calc in calculations:
        result.append({
            'name': calc['name'],
            'status': models.calc.status_to_str(calc['status']),
        })
    return resp(result)
