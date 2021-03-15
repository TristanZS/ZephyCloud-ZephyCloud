# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core lib
import re
import base64
import hashlib
import logging
import json
import collections
import datetime

# Specific libs
from flask import Blueprint, g, jsonify, request, abort
from flask import current_app as app
from werkzeug.exceptions import HTTPException

# Project libs
from lib import pg_util
from lib import type_util
from lib import order_by
from lib import error_util
from lib import date_util
from core import api_util
from core import web_util
import models.users
import models.projects
import models.provider_config
import models.jobs
import models.meshes
import models.calc
import models.currencies


api_admin = Blueprint('admin', __name__)
log = logging.getLogger("aziugo")


def resp(data="ok", pagination_count=None):
    """
    Return the json of the response

    :param data:        The data of the response. Optional, default "ok"
    :type data:         any
    :return:            The http response
    :rtype:             tuple[flask.Response, int]
    """
    response = {
        "success": 1,
        "error_msgs": [],
        "data": data
    }
    if pagination_count is not None:
        response["total"] = pagination_count
    return jsonify(response), 200


# ----------------------- Hooks -------------------------------------------

@api_admin.before_request
def before_request():
    """
    Called before each request
    """
    if 'Authorization' not in request.headers:
        abort(401)
    key = re.sub(r"Basic\s", '', request.headers['Authorization'])
    key = base64.b64decode(key)
    if ":" not in key:
        abort(401)
    login, password = key.split(":", 1)
    h = hashlib.sha256()
    h.update(password)
    h.update(g.conf.get("admin", "salt"))
    password = unicode(h.hexdigest())
    if login != g.conf.get("admin", "login") or password != g.conf.get("admin", "password"):
        abort(401)
    # log.info("admin logged in")


@api_admin.errorhandler(Exception)
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
    if code in (401, 403):  # Unauthorized
        response.headers['WWW-Authenticate'] = 'Basic realm="' + str(g.API_SERVER) + '" charset="UTF-8"'
    return response, code


# ----------------------- Routes -------------------------------------------
@api_admin.route('/', methods=['GET'])
def home():
    """
    Show a simple page
    """
    return "<p>Admin section</p>"


@api_admin.route('/search/', methods=['POST'])
def search():
    """
    Search for users or projects or job_id
    """
    # Check params
    if not web_util.check_request_params(request, 'term'):
        abort(400)
    params = web_util.get_req_params(request)
    term = params['term'].strip()
    if len(term) == 0:
        abort(400, "empty term parameter")
    return resp({
        "users": models.users.search(term, True),
        "projects": models.projects.search(term, True)
    })

# ----------------------- Users -------------------------------------------


@api_admin.route('/users/', methods=['GET', 'POST'])
def users_list():
    """
    Get data for users
    """
    # Check params
    if not web_util.check_request_params(request, optional=['include_deleted', 'offset', "limit", "order", "filter",
                                                            "email", "rank"]):
        abort(400)
    params = web_util.get_req_params(request)
    include_deleted = False
    if 'include_deleted' in params.keys():
        if not type_util.ll_bool(params['include_deleted']):
            abort(400, "invalid value for include_deleted")
        include_deleted = type_util.to_bool(params['include_deleted'])

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
    order = order_by.OrderBy(["user_id", "login", "rank", "credit", "email"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: "+order.issue)

    filter_param = None
    if "filter" in params.keys():
        filter_param = params['filter']
    rank = None
    if "rank" in params.keys():
        if not models.users.is_rank_str(params['rank']):
            abort(400, "invalid value for rank")
        rank = models.users.str_to_rank(params['rank'])

    # Real work
    users = models.users.get_users_with_amounts(include_deleted=include_deleted, offset=offset, limit=limit,
                                                order=order, filter=filter_param, rank=rank)
    result = []
    for user in users:
        result.append({
            "id": user['id'],
            "login": user['login'],
            "email": user['email'],
            "rank": models.users.rank_to_str(user['user_rank']),
            "credit": api_util.price_to_float(user['credit']),
            "deleted": user['delete_date'] is not None
        })
    return resp(result, users.full_count)


@api_admin.route('/user/login_available/', methods=['GET', 'POST'])
def login_available():
    # Check params
    if not web_util.check_request_params(request, 'login'):
        abort(400, "Bad params")
    params = web_util.get_req_params(request)
    if not params['login'] or params['login'] == g.conf.get("admin", "login"):
        abort(400, "Invalid login")

    clean_login = api_util.clean_login(params['login'])
    if len(clean_login) == 0 or clean_login != params['login']:
        abort(400, "Invalid login")

    return resp(models.users.get_user(login=clean_login, include_deleted=False) is None)


@api_admin.route('/user/email_available/', methods=['GET', 'POST'])
def email_available():
    # Check params
    if not web_util.check_request_params(request, 'email'):
        abort(400, "Bad params")
    params = web_util.get_req_params(request)
    if not params['email'] or not api_util.is_email_valid(params['email']):
        abort(400, "Invalid email")

    return resp(models.users.get_user(email=params['email'], include_deleted=False) is None)



@api_admin.route('/user/new/', methods=['GET', 'POST'])
def user_new():
    # Check params
    if not web_util.check_request_params(request, 'login', 'email', 'pwd', 'rank', optional=['nbr_coins', 'reason']):
        abort(400, "Bad params")
    params = web_util.get_req_params(request)
    if not params['login'] or params['login'] == g.conf.get("admin", "login"):
        abort(400, "Invalid login")
    if not params['pwd']:
        abort(400, "Invalid password")
    if not models.users.is_rank_str(params['rank']):
        log.warning("Invalid rank: " + params['rank'])
        abort(400)
    if 'nbr_coins' in params and not type_util.ll_float(params['nbr_coins']):
        log.warning("Invalid nbr_coins: " + params['nbr_coins'])
        abort(400, "Invalid nbr_coins")

    # Real work
    if not api_util.is_email_valid(params['email']):
        abort(400, "Bad user email")
    email = params['email']
    login = api_util.clean_login(params['login'])
    if params['login'] != login:
        abort(400, "Bad user login. Do you mean '"+login+"'")
    pwd = params['pwd']
    rank = models.users.str_to_rank(params['rank'])

    user = models.users.create_user(login, pwd, rank, email)
    if user is None:
        abort(400, "User already exists")
    nbr_coins = float(params['nbr_coins']) if 'nbr_coins' in params else 0.0
    reason = str(params['reason']) if 'reason' in params and params["reason"] else "at user creation, from admin"
    if nbr_coins > 0.0:
        models.users.add_user_credits(api_util.price_from_float(nbr_coins), user["id"], reason)
    return resp(user["id"])


@api_admin.route('/user/remove/', methods=['GET', 'POST'])
def user_remove():
    """
    Removes existing user
    """
    # Check params
    if not web_util.check_request_params(request, 'user_id'):
        abort(400, "Bad params")
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])

    # Real work
    user = models.users.get_user(user_id=user_id, include_deleted=True)
    if user is None:
        abort(404, "User doesn't exists")
    if user["delete_date"] is not None:
        abort(404, "User is already deleted")
    models.users.delete_user(user['id'])
    return resp()


@api_admin.route('/user/credit/add/', methods=['GET', 'POST'])
def user_add_credit():
    """
    Adds ZephyCOINS to existing user
    """
    # Check params
    if not web_util.check_request_params(request, 'user_id', 'nbr_coins', optional=['reason']):
        abort(400, "Bad params")
    params = web_util.get_req_params(request)
    if not type_util.ll_float(params['nbr_coins']):
        log.warning("Invalid nbr_coins: " + repr(params['nbr_coins']))
        abort(400)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])

    # Real work
    user = models.users.get_user(user_id=user_id, include_deleted=True)
    if user is None:
        abort(404, "User doesn't exists")
    nbr_coins = float(params['nbr_coins'])
    reason = str(params['reason']) if 'reason' in params and params["reason"] else "from admin back-office"
    new_credit = models.users.add_user_credits(api_util.price_from_float(nbr_coins), user_id, reason)
    float_credit = api_util.price_to_float(new_credit)
    return resp(float_credit)


@api_admin.route('/user/reset_pwd/', methods=['POST'])
def user_reset_pwd():
    """
    Adds ZephyCOINS to existing user
    """
    # Check params
    if not web_util.check_request_params(request, 'email'):
        abort(400, "Bad params")
    params = web_util.get_req_params(request)

    # Real work
    email = params['email']
    user = models.users.get_user(email=email)
    if user is None:
        abort(404)
    new_pwd = models.users.reset_pwd(user["id"])
    return resp(new_pwd)


@api_admin.route('/user/show/', methods=['GET', 'POST'])
def user_show():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, optional=["user_id", "login", "email", 'include_deleted']):
        abort(400)
    params = web_util.get_req_params(request)
    include_deleted = False
    if 'include_deleted' in params.keys():
        if not type_util.ll_bool(params['include_deleted']):
            abort(400, "invalid value for include_deleted")
        include_deleted = type_util.to_bool(params['include_deleted'])
    identifiers = {}
    if "user_id" in params.keys():
        if not type_util.ll_int(params['user_id']):
            abort(400, "Invalid parameter 'user_id'")
        identifiers["user_id"] = int(params['user_id'])
    if "login" in params.keys():
        clean_login = api_util.clean_login(params['login'])
        if len(clean_login) == 0 or clean_login != params["login"]:
            abort(400, "Invalid parameter 'login': bad format")
        identifiers["login"] = clean_login
    if "email" in params.keys():
        if not api_util.is_email_valid(params["email"]):
            abort(400, "Invalid parameter 'email': bad format")
        identifiers["email"] = params["email"]
    if len(identifiers.keys()) == 0:
        abort(400, "No user identifier")
    if len(identifiers.keys()) > 1:
        abort(400, "Too many user identifiers")

    identifiers["include_deleted"] = include_deleted
    user = models.users.get_user(**identifiers)
    if not user:
        abort(404)

    # Real work
    credits = models.users.get_credit(user['id'])
    result = {
        "id": user['id'],
        "login": user['login'],
        "email": user['email'],
        "rank": models.users.rank_to_str(user['user_rank']),
        "credit": api_util.price_to_float(credits),
        "deleted": user['delete_date'] is not None
    }
    return resp(result)


@api_admin.route('/user/consume/', methods=['GET', 'POST'])
def user_consume():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, "user_id", "amount", "description", "details"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])

    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)

    if not type_util.ll_float(params['amount']):
        abort(400)
    amount = float(params['amount'])
    if amount <= 0:
        abort(400)

    # Real work
    int_amount = api_util.price_from_float(amount)
    models.users.charge_user_custom(user_id, int_amount, params['description'], params['details'])
    return resp()


@api_admin.route('/user/report/', methods=['GET', 'POST'])
def user_report():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, "user_id", 'from', optional=["to", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not type_util.ll_float(params['from']):
        abort(400, "invalid value for from")
    from_date = datetime.datetime.utcfromtimestamp(float(params['from']))

    to_date = datetime.datetime.utcnow()
    if 'to' in params.keys():
        if not type_util.ll_float(params['to']):
            abort(400, "invalid value for to")
        to_date = min(to_date, datetime.datetime.utcfromtimestamp(float(params['to'])))

    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)

    order = None
    if 'order' in params.keys():
        order = params['order'].strip().lower()
        if order not in ["description", "date", "project"]:
            abort(400, "invalid order param")

    # Real work
    report = models.users.get_report(from_date, to_date, user_id, order)
    return resp(pg_util.cast_for_json(report[user_id]))


@api_admin.route('/user/change_rank/', methods=['POST'])
def user_change_rank():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, "user_id", 'rank'):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not models.users.is_rank_str(params['rank']):
        abort(400, "invalid value for status")
    rank = models.users.str_to_rank(params['rank'])

    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)

    # Real work
    models.users.set_user_rank(user_id, rank)
    return resp()


# ----------------------- Providers -------------------------------------------

@api_admin.route('/providers/list/', methods=['GET', 'POST'])
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
    order = order_by.OrderBy(["name", "location", "type"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)

    result = []
    for provider in g.providers.values():
        provider_info = {"name": provider['name'], "location": provider['location'], "type": provider["type"]}
        provider_specific = {}
        if provider["type"] in ("aws", "aws_spot"):
            provider_specific['region'] = g.conf.get("provider_"+provider['name'], "aws_region")
        provider_info['provider_specific'] = provider_specific
        result.append(provider_info)
    order.sort_list_in_place(result)
    result = result[offset:(offset+limit if limit else None)]
    return resp(result)


@api_admin.route('/providers/list_all_machines/', methods=['GET', 'POST'])
def provider_list_all_machines():
    # Check params
    if not web_util.check_request_params(request):
        abort(400)

    result = {}
    for provider in g.providers.keys():
        machines = models.provider_config.list_machines(provider)
        result[provider] = [m['machine_code'] for m in machines]
    return resp(result)


# ----------------------- Machines -------------------------------------------

@api_admin.route('/machines/list/', methods=['GET', 'POST'])
def machines_list():
    # Check params
    if not web_util.check_request_params(request, "provider_name", optional=['date', 'offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    if params['provider_name'] not in g.providers.keys():
        abort(404, "Unknown provider")
    at = None
    if 'date' in params:
        if not type_util.ll_int(params['date']):
            abort(400, "bad 'date' param")
        at = min(datetime.datetime.utcnow(), datetime.datetime.utcfromtimestamp(int(params['date'])))
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
    order = order_by.OrderBy(["name", "cores", "ram", "availability"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)

    # Real job
    machines = models.provider_config.list_machines(params['provider_name'], at=at, offset=offset, limit=limit,
                                                    order=order)
    results = []
    for machine in machines:
        cost = models.provider_config.get_machine_provider_cost(params['provider_name'], machine['machine_code'], at=at)
        machine_info = {
            'name': machine['machine_code'],
            'cores': int(machine['nbr_cores']),
            "ram": int(machine['ram_size']),
            "availability": int(machine['nbr_available']),
            "prices": {},
            "cost_per_hour": api_util.price_to_float(cost["cost_per_sec"] * 3600),
            "cost_currency": cost["currency"],
            "cost_sec_granularity": int(cost["sec_granularity"]),
            "cost_min_sec_granularity": int(cost["min_sec_granularity"])
        }

        sec_granularity = 1
        min_sec_granularity = 1
        auto_update = False
        for rank in models.users.all_ranks():
            price_info = models.provider_config.get_machine_price(params['provider_name'], machine['machine_code'],
                                                                  rank, at=at)
            if price_info["auto_update"]:
                auto_update = True
            price = api_util.price_to_float(price_info['sec_price'] * 3600)
            machine_info["prices"][models.users.rank_to_str(rank)] = price
            sec_granularity = max(sec_granularity, int(price_info['sec_granularity']))
            min_sec_granularity = max(min_sec_granularity, int(price_info['min_sec_granularity']))
        machine_info['price_sec_granularity'] = sec_granularity
        machine_info['price_min_sec_granularity'] = min_sec_granularity
        machine_info['auto_update'] = auto_update
        results.append(machine_info)

    return resp(results)


@api_admin.route('/machines/show/', methods=['GET', 'POST'])
def machines_show():
    # Check params
    if not web_util.check_request_params(request, "provider_name", "machine_name"):
        abort(400)
    params = web_util.get_req_params(request)
    if params['provider_name'] not in g.providers.keys():
        abort(404, "Unknown provider")
    machine = models.provider_config.get_machine(params['provider_name'], params['machine_name'])
    if not machine:
        abort(404, "Unknown machine")

    # Real job
    cost = models.provider_config.get_machine_provider_cost(params['provider_name'], machine['machine_code'])
    machine_info = {
        'name': machine['machine_code'],
        'cores': int(machine['nbr_cores']),
        "ram": int(machine['ram_size']),
        "availability": int(machine['nbr_available']),
        "prices": {},
        "cost_per_hour": api_util.price_to_float(cost["cost_per_sec"] * 3600),
        "cost_currency": cost["currency"],
        "cost_sec_granularity": int(cost["sec_granularity"]),
        "cost_min_sec_granularity": int(cost["min_sec_granularity"])
    }

    sec_granularity = 1
    min_sec_granularity = 1
    auto_update = False
    for rank in models.users.all_ranks():
        price_info = models.provider_config.get_machine_price(params['provider_name'], machine['machine_code'], rank)
        if price_info["auto_update"]:
            auto_update = True
        price = api_util.price_to_float(price_info['sec_price'] * 3600)
        machine_info["prices"][models.users.rank_to_str(rank)] = price
        sec_granularity = max(sec_granularity, int(price_info['sec_granularity']))
        min_sec_granularity = max(min_sec_granularity, int(price_info['min_sec_granularity']))
    machine_info['price_sec_granularity'] = sec_granularity
    machine_info['price_min_sec_granularity'] = min_sec_granularity
    machine_info['auto_update'] = auto_update

    return resp(machine_info)


@api_admin.route('/machines/create/', methods=['GET', 'POST'])
def machines_create():
    # Check params
    if not web_util.check_request_params(request, "provider_name", "machine_name", "cores", "ram", "availability",
                                         "prices", "price_sec_granularity", "price_min_sec_granularity",
                                         "cost_per_hour", "cost_currency", "cost_sec_granularity",
                                         "cost_min_sec_granularity", "auto_update"):
        abort(400)
    params = web_util.get_req_params(request)
    if params['provider_name'] not in g.providers.keys():
        abort(404, "Unknown provider")
    for param in ["cores", "ram", "availability", "price_sec_granularity", "price_min_sec_granularity",
                  "cost_sec_granularity", "cost_min_sec_granularity"]:
        if not type_util.ll_int(params[param]):
            abort(400, "bad value for "+repr(param))
        params[param] = int(params[param])
    if not isinstance(params['prices'], dict):
        abort(400, "bad param 'prices'")
    prices = {}
    for rank in models.users.all_ranks():
        rank_str = models.users.rank_to_str(rank)
        if rank_str not in params['prices'].keys():
            abort(400, "bad param 'prices': missing price for "+rank_str)
        if not type_util.ll_float(params['prices'][rank_str]):
            abort(400, "bad param 'prices': bad format for rank " + rank_str)
        prices[rank] = api_util.price_from_float(float(params['prices'][rank_str]) / 3600.0)
        del params['prices'][rank_str]
    if params['prices']:
        abort(400, "bad param 'prices': unknown rank "+repr(next(iter(params['prices']))))
    if not type_util.ll_float(params['cost_per_hour']):
        abort(400, "bad param 'cost_per_hour': unknown format")
    if not params['machine_name'].strip():
        abort(400, "bad param 'machine_name'")
    if not params['cost_currency'].strip():
        abort(400, "bad param 'cost_currency'")
    if not type_util.ll_bool(params['auto_update'].strip()):
        abort(400, "bad param 'auto_update'")
    machine = models.provider_config.get_machine(params['provider_name'], params['machine_name'])
    if machine:
        abort(400, "machine already exists")

    # Real job
    cost = api_util.price_from_float(float(params["cost_per_hour"]) / 3600.0)
    operations = models.provider_config.list_operations(params['provider_name'])
    auto_update = type_util.to_bool(params['auto_update'].strip())
    with pg_util.Transaction(api_util.DatabaseContext.get_conn()):
        models.provider_config.set_machine_and_prices(params['provider_name'], params['machine_name'].strip(),
                                                      params['cores'], params['ram'], params['availability'], cost,
                                                      params['cost_currency'], params['cost_sec_granularity'],
                                                      params['cost_min_sec_granularity'],
                                                      params["price_sec_granularity"],
                                                      params["price_min_sec_granularity"], prices, auto_update)

        for rank in models.users.all_ranks():
            models.provider_config.set_machine_price(params['provider_name'], params['machine_name'].strip(), rank,
                                                     prices[rank], params["price_sec_granularity"],
                                                     params["price_min_sec_granularity"])

        for operation in operations:
            models.provider_config.add_machine_to_operation(params['provider_name'], operation['operation_name'],
                                                            params['machine_name'])
    return resp()


@api_admin.route('/machines/update/', methods=['GET', 'POST'])
def machines_update():
    # Check params
    if not web_util.check_request_params(request, "provider_name", "machine_name",
                                         optional=["cores", "ram", "availability", "prices", "price_sec_granularity",
                                                   "price_min_sec_granularity", "cost_per_hour", "cost_currency",
                                                   "cost_sec_granularity", "cost_min_sec_granularity", "auto_update"]):
        abort(400)
    params = web_util.get_req_params(request)
    if params['provider_name'] not in g.providers.keys():
        abort(404, "Unknown provider")
    machine = models.provider_config.get_machine(params['provider_name'], params['machine_name'])
    if not machine:
        abort(404, "unknown machine")
    if len(params.keys()) == 2:
        abort(404, "no update params")

    for param in ["cores", "ram", "availability", "price_sec_granularity", "price_min_sec_granularity",
                  "cost_sec_granularity", "cost_min_sec_granularity"]:
        if param in params.keys():
            if not type_util.ll_int(params[param]):
                abort(400, "bad value for "+repr(param))
            params[param] = int(params[param])

    prices = None
    if 'prices' in params:
        if not isinstance(params['prices'], dict):
            abort(400, "bad param 'prices'")
        prices = {}
        str_ranks = [models.users.rank_to_str(r) for r in models.users.all_ranks()]
        for rank_str in params['prices'].keys():
            if rank_str not in str_ranks:
                abort(400, "bad param 'prices': unknown rank "+repr(rank_str))
            if not type_util.ll_float(params['prices'][rank_str]):
                abort(400, "bad param 'prices': bad format for rank " + rank_str)
            rank = models.users.str_to_rank(rank_str)
            prices[rank] = api_util.price_from_float(float(params['prices'][rank_str]) / 3600.0)

    cost = None
    if 'cost_per_hour' in params:
        if not type_util.ll_float(params['cost_per_hour']):
            abort(400, "bad param 'cost_per_hour': unknown format")
        cost = api_util.price_from_float(float(params["cost_per_hour"]) / 3600.0)
    if 'cost_currency' in params and not params['cost_currency'].strip():
        abort(400, "bad param 'cost_currency'")
    if 'auto_update' in params and not type_util.ll_bool(params['auto_update'].strip()):
        abort(400, "bad param 'auto_update'")

    # Real job
    update_params = {}
    if "cores" in params.keys():
        update_params['nbr_cores'] = params['cores']
    if "ram" in params.keys():
        update_params['ram_size'] = params['ram']
    if "availability" in params.keys():
        update_params['nbr_available'] = params['availability']
    if cost is not None:
        update_params['provider_cost_per_sec'] = cost
    if "cost_currency" in params.keys():
        update_params['provider_currency'] = params['cost_currency'].strip()
    if "cost_sec_granularity" in params:
        update_params['provider_sec_granularity'] = params['cost_sec_granularity']
    if "cost_min_sec_granularity" in params:
        update_params['provider_min_sec_granularity'] = params['cost_min_sec_granularity']
    if "price_sec_granularity" in params:
        update_params['price_sec_granularity'] = params['price_sec_granularity']
    if "price_min_sec_granularity" in params:
        update_params['price_min_sec_granularity'] = params['price_min_sec_granularity']
    if "auto_update" in params:
        update_params['auto_update'] = type_util.to_bool(params['auto_update'])
    if prices:
        update_params['prices'] = prices

    models.provider_config.update_machine(params['provider_name'], params['machine_name'], update_params)
    return resp()


@api_admin.route('/machines/remove/', methods=['GET', 'POST'])
def machines_remove():
    # Check params
    if not web_util.check_request_params(request, "provider_name", "machine_name"):
        abort(400)
    params = web_util.get_req_params(request)
    if params['provider_name'] not in g.providers.keys():
        abort(404, "Unknown provider")
    machine = models.provider_config.get_machine(params['provider_name'], params['machine_name'])
    if not machine:
        abort(404, "unknown machine")

    # Real job
    models.provider_config.remove_machine(params['provider_name'], params['machine_name'])
    return resp()


@api_admin.route('/machines/list_toolchains/', methods=['GET', 'POST'])
def machines_list_toolchains():
    # Check params
    if not web_util.check_request_params(request, "provider_name", "machine_name"):
        abort(400)
    params = web_util.get_req_params(request)
    if params['provider_name'] not in g.providers.keys():
        abort(404, "Unknown provider")
    machine = models.provider_config.get_machine(params['provider_name'], params['machine_name'])
    if not machine:
        abort(404, "Unknown machine")

    # Real job
    operations = models.provider_config.list_machine_operations(params['provider_name'], params['machine_name'])
    return resp([o["operation_name"] for o in operations])


# ----------------------- Toolchains -------------------------------------------

@api_admin.route('/toolchains/list/', methods=['GET', "POST"])
def toolchains_list():
    # Check params
    if not web_util.check_request_params(request, optional=["date", 'offset', "limit", "order"]):
        abort(400)
    params = web_util.get_req_params(request)
    at = None
    if 'date' in params:
        if not type_util.ll_int(params['date']):
            abort(400, "bad 'date' param")
        at = min(datetime.datetime.utcnow(), datetime.datetime.utcfromtimestamp(int(params['date'])))
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
    order = order_by.OrderBy(["name", "fixed_price", "machine_limit"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)

    # Real job
    results = []
    toolchain_by_name = {}
    for provider in g.providers:
        operations = models.provider_config.list_operations(provider, at=at, offset=offset, limit=limit, order=order)
        for operation in operations:
            if operation['operation_name'] not in toolchain_by_name.keys():
                toolchain_by_name[operation['operation_name']] = pg_util.row_to_dict(operation)

    for operation in toolchain_by_name.values():
        results.append({
            'name': operation['operation_name'],
            'fixed_price': api_util.price_to_float(operation['fixed_cost']),
            'machine_limit': int(operation['cluster_limit'])
        })
    return resp(results)


@api_admin.route('/toolchains/show/', methods=['GET', "POST"])
def toolchains_show():
    # Check params
    if not web_util.check_request_params(request, "toolchain_name"):
        abort(400)
    params = web_util.get_req_params(request)

    # Real job
    operation = None
    for provider in g.providers:
        operation = models.provider_config.get_operation(provider, params['toolchain_name'])
        if operation:
            break
    if not operation:
        abort(404)
    result = {
        'name': operation['operation_name'],
        'fixed_price': api_util.price_to_float(operation['fixed_cost']),
        'machine_limit': int(operation['cluster_limit'])
    }
    return resp(result)


@api_admin.route('/toolchains/update/', methods=['GET', "POST"])
def toolchains_update():
    # Check params
    if not web_util.check_request_params(request, 'toolchain_name',
                                         optional=['fixed_price', 'machine_limit', 'machines']):
        abort(400)
    params = web_util.get_req_params(request)
    if len(params.keys()) == 1:
        abort(404, "no update params")
    operation = None
    for provider in g.providers:
        operation = models.provider_config.get_operation(provider, params['toolchain_name'])
        if operation:
            break
    if not operation:
        abort(404)
    if "fixed_price" in params.keys() and not type_util.ll_float(params["fixed_price"]):
        abort(400, "bad param 'fixed_price'")
    if "machine_limit" in params.keys() and not type_util.ll_int(params["machine_limit"]):
        abort(400, "bad param 'machine_limit'")
    if "machines" in params.keys():
        if not type_util.is_dict(params["machines"]):
            abort(400, "bad param 'machine_limit'")
        for provider_name, machine_list in params["machines"].items():
            if provider_name not in g.providers.keys():
                abort(404, "Unknown provider "+str(provider_name))
            if not type_util.is_array(machine_list):
                abort(400, "bad param 'machine_limit'")

    with pg_util.Transaction(api_util.DatabaseContext.get_conn()):
        if "fixed_price" in params.keys():
            for provider in g.providers.keys():
                price = api_util.price_from_float(float(params["fixed_price"]))
                models.provider_config.set_operation_cost(provider, params['toolchain_name'], price)

        if "machine_limit" in params.keys():
            for provider in g.providers.keys():
                models.provider_config.set_operation_cluster_limit(provider, params['toolchain_name'],
                                                                   int(params['machine_limit']))

        if "machines" in params.keys():
            for provider in g.providers.keys():
                if provider in params["machines"].keys():
                    machine_list = params['machines'][provider]
                else:
                    machine_list = []
                models.provider_config.set_operation_machines(provider, params['toolchain_name'], machine_list)

    return resp()


@api_admin.route('/toolchains/list_machines/', methods=['GET', "POST"])
def toolchains_list_machines():
    # Check params
    if not web_util.check_request_params(request, "toolchain_name", optional=["provider"]):
        abort(400)
    params = web_util.get_req_params(request)

    provider_list = g.providers.keys()
    if "provider" in params.keys():
        if params["provider"] not in g.providers.keys():
            abort(400)
        provider_list = [params["provider"]]

    # Real job
    machine_list = {}
    found = False
    for provider in provider_list:
        operation = models.provider_config.get_operation(provider, params['toolchain_name'], include_machines=True)
        if not operation:
            continue
        found = True
        machine_list[provider] = operation['machines']
    if not found:
        abort(404)
    return resp(machine_list)


# ------------------------ Transactions --------------------------------------------

@api_admin.route('/transactions/list/', methods=['GET', 'POST'])
def transaction_list():
    # Check params
    if not web_util.check_request_params(request, optional=["user_id", "project_uid", "job_id", 'offset', "limit",
                                                            "order", "description"]):
        abort(400)
    params = web_util.get_req_params(request)
    user_id = None
    if "user_id" in params:
        if not type_util.ll_int(params['user_id']):
            abort(400, "Invalid parameter 'user_id'")
        user_id = int(params['user_id'])
    project_uid = None
    if "project_uid" in params:
        if not params["project_uid"].strip():
            abort(400, "bad param 'project_uid'")
        project_uid = params["project_uid"].strip()
    job_id = None
    if "job_id" in params:
        if not type_util.ll_int(params["job_id"]):
            abort(400, "bad param 'job_id'")
        job_id = int(params["job_id"])
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
    order = order_by.OrderBy(["id", "amount", "date", "job_id", "login", "email", "project_uid", "computing_start",
                              "computing_end", "description"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)
    description=None
    if 'description' in params.keys():
        description = params['description']

    # Real work
    transactions = models.users.list_transactions(user_id, project_uid, job_id, offset=offset, limit=limit, order=order,
                                                  description=description)
    results = []
    for trans in transactions:
        results.append({
            "id": trans['id'],
            "amount": api_util.price_to_float(trans['amount']),
            "date": trans['date'],
            "description": trans['description'],
            "job_id": trans['job_id'],
            "computing_start": trans['computing_start'],
            "computing_end": trans['computing_end'],
            "project_uid": trans['project_uid'],
            "login": trans['login'],
            "email": trans['email'],
            "user_id": trans['user_id']
        })
    return resp(results, transactions.full_count)


@api_admin.route('/transactions/cancel/', methods=['GET', 'POST'])
def transaction_cancel():
    # Check params
    if not web_util.check_request_params(request, "transaction_ids", "reason"):
        abort(400)
    params = web_util.get_req_params(request)
    if not params["reason"].strip():
        abort(400, "bad param 'reason'")
    if type_util.is_string(params['transaction_ids']):
        if not type_util.is_json(params['transaction_ids']):
            abort(400, "bad param 'transaction_ids'")
        params['transaction_ids'] = json.loads(params['transaction_ids'])
    if not isinstance(params['transaction_ids'], collections.Iterable):
        abort(400, "bad param 'transaction_ids'")
    if not params['transaction_ids']:
        abort(400, "bad param 'transaction_ids'")
    transaction_ids = []
    for trans_id in params['transaction_ids']:
        if not type_util.is_int(trans_id):
            abort(400, "bad param 'transaction_ids'")
        transaction_ids.append(int(trans_id))
    if len(transaction_ids) != len(set(transaction_ids)):  # we check for doubloons
        abort(400, "bad param 'transaction_ids'")

    # Real job
    models.users.cancel_transactions(transaction_ids, params["reason"])
    return resp()


# ------------------------ computations --------------------------------------------

@api_admin.route('/computations/list/', methods=['GET', 'POST'])
def computation_list():
    # Check params
    if not web_util.check_request_params(request, optional=['project_uid', "user_id", 'offset', "limit", "order",
                                                            "status"]):
        abort(400)
    params = web_util.get_req_params(request)
    user_id = None
    if "user_id" in params:
        if not type_util.ll_int(params['user_id']):
            abort(400, "Invalid parameter 'user_id'")
        user_id = int(params['user_id'])
    project_uid = None
    if "project_uid" in params:
        if not params["project_uid"].strip():
            abort(400, "bad param 'project_uid'")
        project_uid = params["project_uid"].strip()
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
    order = order_by.OrderBy(["job_id", "project_uid", "status", "start_time", "end_time", "email", "user_id", "login"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)
    possible_status = None
    if "status" in params.keys():
        try:
            possible_status = models.jobs.job_status_from_str(str(params["status"]).strip().lower())
        except StandardError:
            abort(400, "invalid status: " + str(params["status"]))
    # Real work
    jobs = models.jobs.list_jobs(user_id=user_id, project_uid=project_uid, join_user=True, offset=offset, limit=limit,
                                 order=order, possible_status=possible_status)
    results = []
    for job in jobs:
        results.append({
            "job_id": job['id'],
            "login": job['login'],
            "email": job['email'],
            "user_id": job["user_id"],
            "project_uid": job['project_uid'],
            "status": models.jobs.job_status_to_str(job['status']),
            "progress": job['progress'],
            "create_date": job['create_date'],
            "start_time": job['start_time'],
            "end_time": job['end_time'],
            "has_logs": job['logs'] is not None and len(job['logs'].strip()) > 0
        })
    return resp(results, jobs.full_count)


@api_admin.route('/computations/show/', methods=['GET', 'POST'])
def computation_show():
    # Check params
    if not web_util.check_request_params(request, "job_id"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params["job_id"]):
        abort(400, "bad param 'job_id'")
    job_id = params["job_id"]
    job = models.jobs.get_job(job_id)
    if not job:
        abort(404)

    # Real work
    user = models.users.get_user(user_id=job["user_id"], include_deleted=True)
    operation = models.provider_config.get_operation_by_id(job["operation_id"])
    cost = models.provider_config.get_machine_provider_cost_by_id(job["provider_cost_id"])
    price = models.provider_config.get_machine_price_by_id(job["machine_price_id"])
    if price is None:
        machine = None
    else:
        machine = models.provider_config.get_machine_by_uid(price['machine_uid'])

    storage_consumption = 0
    mesh = models.meshes.get_mesh_by_job_id(job['id'])
    toolchain_specific = {}
    if mesh:
        # toolchain_specific["preview_file"] = mesh["preview_file_id"]
        toolchain_specific['mesh_id'] = mesh['id']

    calc = models.calc.get_calc_by_job_id(job['id'])
    if calc:
        toolchain_specific['calc_id'] = calc['id']

    computation_consumption = models.jobs.get_job_consume(job['id'])

    result = {
        "job_id": job['id'],
        "login": user['login'],
        "email": user['email'],
        "user_id": user['id'],
        "project_uid": job['project_uid'],
        "status": models.jobs.job_status_to_str(job['status']),
        "progress": job['progress'],
        "create_date": job['create_date'],
        "start_time": job['start_time'],
        "end_time": job['end_time'],
        "has_logs": job['has_logs'],
        "provider": operation["provider_code"],
        "machine": machine['machine_code'] if machine else None,
        "nbr_machines": job['nbr_machines'],
        "user_rank": models.users.rank_to_str(operation["user_rank"]),
        "toolchain_name": operation["operation_name"],
        "toolchain_id": operation["id"],
        "fixed_price": api_util.price_to_float(operation["fixed_cost"]),
        "cost_per_sec_per_machine": api_util.price_to_float(cost["cost_per_sec"]) if cost else None,
        "cost_currency": cost["currency"] if cost else None,
        "cost_min_sec_granularity": cost["min_sec_granularity"] if cost else None,
        "cost_sec_granularity": cost["sec_granularity"] if cost else None,
        "price_per_sec_per_machine": api_util.price_to_float(price["sec_price"]) if price else None,
        "price_min_sec_granularity": price["min_sec_granularity"] if price else None,
        "price_sec_granularity": price["sec_granularity"] if price else None,
        "toolchain_specific": toolchain_specific,
        "computation_consumption": api_util.price_to_float(float(computation_consumption)*-1.0),
        "storage_consumption": api_util.price_to_float(storage_consumption),
    }
    return resp(result)


@api_admin.route('/computations/disable_shutdown/', methods=['GET', 'POST'])
def computation_disable_shutdown():
    # Check params
    if not web_util.check_request_params(request, "job_id"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params["job_id"]):
        abort(400, "bad param 'job_id'")
    job_id = params["job_id"]
    job = models.jobs.get_job(job_id)
    if not job:
        abort(404)

    models.jobs.disable_shutdown(job_id)
    return resp()


@api_admin.route('/computations/show_logs/', methods=['GET', 'POST'])
def computation_show_logs():
    # Check params
    if not web_util.check_request_params(request, "job_id"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params["job_id"]):
        abort(400, "bad param 'job_id'")
    job_id = params["job_id"]
    job = models.jobs.get_job(job_id, True)
    if not job:
        abort(404)

    # Real work
    return resp(job['logs'])


@api_admin.route('/computations/kill/', methods=['GET', 'POST'])
def computation_kill():
    # Check params
    if not web_util.check_request_params(request, "job_id"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params["job_id"]):
        abort(400, "bad param 'job_id'")
    job_id = params["job_id"]
    job = models.jobs.get_job(job_id)
    if not job:
        abort(404)

    if job["status"] in [models.jobs.JOB_STATUS_KILLED,
                         models.jobs.JOB_STATUS_CANCELING,
                         models.jobs.JOB_STATUS_CANCELED,
                         models.jobs.JOB_STATUS_FINISHED]:
        return resp()

    # Real work
    log.info("Killing job "+str(job_id)+" from dashboard")
    models.jobs.cancel_job(job_id)
    return resp()


# ------------------------ Projects --------------------------------------------

@api_admin.route('/projects/list/', methods=['GET', 'POST'])
def projects_list():
    # Check params
    if not web_util.check_request_params(request, optional=["user_id", "date", 'offset', "limit", "order", "filter",
                                                            "storage", "status"]):
        abort(400)
    params = web_util.get_req_params(request)
    at = None
    if 'date' in params:
        if not type_util.ll_int(params['date']):
            abort(400, "bad 'date' param")
        at = min(datetime.datetime.utcnow(), datetime.datetime.utcfromtimestamp(int(params['date'])))
    user_id = None
    if "user_id" in params:
        if not type_util.ll_int(params['user_id']):
            abort(400, "Invalid parameter 'user_id'")
        user_id = int(params['user_id'])
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

    order = order_by.OrderBy(["project_uid", "storage", "status", "id", "email", "creation_date"])
    if 'order' in params.keys():
        order.parse(params['order'])
        if not order.is_valid():
            abort(400, "invalid value for order: " + order.issue)
    filter_str = None
    if "filter" in params.keys():
        filter_str = params['filter']
    status = None
    if "status" in params.keys():
        if not models.projects.is_status_str(params["status"]):
            abort(400, "invalid value for status")
        status = models.projects.str_to_project_status(params["status"])
    storage = None
    if "storage" in params.keys():
        storage = params["storage"]

    # Real job
    if user_id is not None:
        user = models.users.get_user(user_id, include_deleted=True)
        if user is None:
            abort(404)
    projects = models.projects.list_projects(user_id=user_id, at=at, offset=offset, limit=limit, order=order,
                                             filter=filter_str, status=status, storage=storage)
    results = []
    for project in projects:
        results.append({
            "project_uid": project['uid'],
            "storage": project['storage'],
            "login": project['login'],
            "email": project['email'],
            "user_id": project['user_id'],
            "status": models.projects.project_status_to_str(project['status']),
            "create_date": date_util.dt_to_timestamp(project['creation_date'])
        })
    return resp(results, projects.full_count)


@api_admin.route('/projects/show/', methods=['GET', 'POST'])
def projects_show():
    # Check params
    if not web_util.check_request_params(request, "project_uid", "user_id", optional=['include_deleted']):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    project_uid = params["project_uid"]
    include_deleted = False
    if 'include_deleted' in params.keys():
        if not type_util.ll_bool(params['include_deleted']):
            abort(400, "bad param 'include_deleted'")
        include_deleted = type_util.to_bool(params['include_deleted'])

    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)
    project = models.projects.get_project(user_id, project_uid)
    if not project:
        abort(404)

    # Real work
    files = models.projects.list_files(user_id, project_uid, include_deleted=True)
    total_size = 0
    raw_file_url = None
    analyzed_file_url = None
    for file_row in files:
        if file_row['id'] is not None:
            total_size += int(file_row['size'])
        if file_row['key'] == models.projects.PROJECT_FILE_RAW:
            raw_file_url = web_util.get_file_url(project['storage'], file_row['filename'], True)
        elif file_row['key'] == models.projects.PROJECT_FILE_ANALYSED:
            analyzed_file_url = web_util.get_file_url(project['storage'], file_row['filename'], True)

    calculations = models.calc.list_calculations(user_id, project_uid, include_deleted=include_deleted, with_logs=True)
    result_calculations = []
    for calc in calculations:
        result_calculations.append({
            "calc_id": calc["id"],
            "job_id": calc['job_id'],
            'name': calc['name'],
            "mesh_id": calc['mesh_id'],
            'status': models.calc.status_to_str(calc['status']),
            'status_file_id': calc['status_file_id'],
            'result_file_id': calc['result_file_id'],
            "iterations_file_id": calc['iterations_file_id'],
            "reduce_file_id": calc['reduce_file_id'],
            "internal_file_id": calc['internal_file_id'],
            "create_date": calc['create_date'],
            "delete_date": calc['delete_date'],
            "has_logs": calc['logs'] is not None and len(calc['logs'].strip()) > 0,
        })
    result_calculations.sort(key=lambda m:m["create_date"])

    meshes = models.meshes.list_meshes(user_id, project_uid, include_deleted=include_deleted)
    result_meshes = []
    for mesh in meshes:
        result_meshes.append({
            "mesh_id": mesh['id'],
            'name': mesh['name'],
            'status': models.meshes.status_to_str(mesh['status']),
            'preview_file_id': mesh['preview_file_id'],
            'result_file_id': mesh['result_file_id'],
            "create_date": mesh['create_date'],
            "delete_date": mesh['delete_date']
        })
    result_meshes.sort(key=lambda m:m["create_date"])

    return resp({
        "project_uid": project['uid'],
        "create_date": date_util.dt_to_timestamp(project['creation_date']),
        "storage": project['storage'],
        "login": user["login"],
        "email": user["email"],
        "amount": api_util.price_to_float(models.projects.get_already_spent(user_id, project_uid)),
        "user_id": user_id,
        "status": models.projects.project_status_to_str(project['status']),
        "total_size": total_size,
        "raw_file_url": raw_file_url,
        "analyzed_file_url": analyzed_file_url,
        "meshes": result_meshes,
        "calculations": result_calculations
    })


@api_admin.route('/projects/status/', methods=['POST'])
def project_set_status():
    # Check params
    if not web_util.check_request_params(request, 'project_uid', "user_id", "status"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not params["project_uid"].strip():
        abort(400, "bad param 'project_uid'")
    project_uid = params["project_uid"]
    status = params["status"].strip()
    if not status or not models.projects.is_status_str(status):
        abort(400, "bad param 'status'")
    status = models.projects.str_to_project_status(status)

    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)
    project = models.projects.get_project(user_id, project_uid, include_deleted=True)
    if not project:
        abort(404, "project doesn't exists")

    # Real work
    models.projects.set_project_status(user_id, project_uid, status)
    return resp()


@api_admin.route('/projects/remove/', methods=['POST'])
def delete_project():
    # Check params
    if not web_util.check_request_params(request, 'project_uid', "user_id", optional=['include_deleted']):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not params["project_uid"].strip():
        abort(400, "bad param 'project_uid'")
    project_uid = params["project_uid"]
    include_deleted = False
    if 'include_deleted' in params.keys():
        if type_util.ll_bool(params['include_deleted']):
            abort(400, "bad value for field 'include_deleted'")
        include_deleted = type_util.to_bool(params['include_deleted'])
    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)
    project = models.projects.get_project(user_id, project_uid, include_deleted=include_deleted)
    if not project:
        abort(404, "project doesn't exists")

    # Real work
    models.projects.delete_project(user_id, project_uid)
    return resp()


@api_admin.route('/projects/file_url/', methods=['GET', 'POST'])
def projects_file_url():
    # Check params
    if not web_util.check_request_params(request, "project_uid", "user_id", "file_id", optional=['include_deleted']):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not params["project_uid"].strip():
        abort(400, "bad param 'project_uid'")
    project_uid = params["project_uid"]
    include_deleted = False
    if 'include_deleted' in params.keys():
        if not type_util.ll_bool(params['include_deleted']):
            abort(400, "bad param 'include_deleted'")
        include_deleted = type_util.to_bool(params['include_deleted'])
    file_id = params["file_id"].strip()
    if not file_id or not type_util.ll_int(file_id):
        abort(400, "bad param 'file_id'")
    file_id = int(file_id)

    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)
    project = models.projects.get_project(user_id, project_uid)
    if not project:
        abort(404)
    file_row = models.projects.get_file_by_id(user_id, project_uid, file_id, include_deleted=include_deleted)
    if not file_row:
        abort(404)

    # Real work
    return resp(web_util.get_file_url(project['storage'], file_row['filename'], True))


# ------------------------ Models status --------------------------------------------

@api_admin.route('/meshes/status/', methods=['POST'])
def mesh_set_status():
    # Check params
    if not web_util.check_request_params(request, "project_uid", "user_id", "mesh_id", "status"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not params["project_uid"].strip():
        abort(400, "bad param 'project_uid'")
    project_uid = params["project_uid"]
    mesh_id = params["mesh_id"].strip()
    if not mesh_id or not type_util.ll_int(mesh_id):
        abort(400, "bad param 'mesh_id'")
    mesh_id = int(mesh_id)
    status = params["status"].strip()
    if not status or not models.meshes.is_status_str(status):
        abort(400, "bad param 'status'")
    status = models.meshes.str_to_status(status)

    # Real work
    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)
    project = models.projects.get_project(user_id, project_uid, include_deleted=True)
    if not project:
        abort(404)
    mesh = models.meshes.get_mesh_by_id(mesh_id)
    if not mesh:
        abort(404)
    if mesh["project_uid"] != project_uid:
        abort(404)
    models.meshes.set_mesh_status(user_id, project_uid, mesh["name"], status)
    return resp()



@api_admin.route('/calculations/status/', methods=['POST'])
def calc_set_status():
    # Check params
    if not web_util.check_request_params(request, "project_uid", "user_id", "calc_id", "status"):
        abort(400)
    params = web_util.get_req_params(request)
    if not type_util.ll_int(params['user_id']):
        abort(400, "Invalid parameter 'user_id'")
    user_id = int(params['user_id'])
    if not params["project_uid"].strip():
        abort(400, "bad param 'project_uid'")
    project_uid = params["project_uid"]
    calc_id = params["calc_id"].strip()
    if not calc_id or not type_util.ll_int(calc_id):
        abort(400, "bad param 'calc_id'")
    calc_id = int(calc_id)
    status = params["status"].strip()
    if not status or not models.calc.is_status_str(status):
        abort(400, "bad param 'status'")
    status = models.calc.str_to_status(status)

    # Real work
    user = models.users.get_user(user_id, include_deleted=True)
    if not user:
        abort(404)
    project = models.projects.get_project(user_id, project_uid, include_deleted=True)
    if not project:
        abort(404)
    calc = models.calc.get_calc(user_id, project_uid, calc_id, include_deleted=True)
    if not calc:
        abort(404)
    models.calc.set_calc_status(user_id, project_uid, calc["name"], status)
    return resp()


# ------------------------ Global reports --------------------------------------------

@api_admin.route('/reports/users/', methods=['GET', 'POST'])
def reports_all_users():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, optional=['from', "to", "order"]):
        abort(400)
    params = web_util.get_req_params(request)

    to_date = datetime.datetime.utcnow()
    if 'to' in params.keys():
        if not type_util.ll_float(params['to']):
            abort(400, "invalid value for to")
        to_date = min(to_date, datetime.datetime.utcfromtimestamp(float(params['to'])))

    if 'from' in params.keys():
        if not type_util.ll_float(params['from']):
            abort(400, "invalid value for from")
        from_date = datetime.datetime.utcfromtimestamp(float(params['from']))
    else:
        from_date = models.users.get_report_date(datetime.datetime.utcfromtimestamp(0))

    order = None
    if 'order' in params.keys():
        order = params['order'].strip().lower()
        if order not in ["description", "date", "project"]:
            abort(400, "invalid order param")

    # Real work
    report = models.users.get_report(from_date, to_date, order_by=order)
    return resp(pg_util.cast_for_json(report.values()))


@api_admin.route('/reports/benefits/', methods=['GET', "POST"])
def reports_benefits():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, optional=['from', "to", "currency", "user_id"]):
        abort(400)
    params = web_util.get_req_params(request)

    to_date = datetime.datetime.utcnow()
    if 'to' in params.keys():
        if not type_util.ll_float(params['to']):
            abort(400, "invalid value for to")
        to_date = min(to_date, datetime.datetime.utcfromtimestamp(float(params['to'])))

    if 'from' in params.keys():
        if not type_util.ll_float(params['from']):
            abort(400, "invalid value for from")
        from_date = datetime.datetime.utcfromtimestamp(float(params['from']))
    else:
        from_date = models.users.get_report_date(datetime.datetime.utcfromtimestamp(0))

    currency = None
    if 'currency' in params.keys():
        currency = params["currency"].lower()
        if currency not in (api_util.CURRENCY_EURO, api_util.CURRENCY_DOLLAR, api_util.CURRENCY_YUAN):
            abort(400, "invalid value for currency")

    user_id = None
    if 'user_id' in params.keys():
        if not type_util.ll_int(params['user_id']):
            abort(400, "Invalid parameter 'user_id'")
        user_id = int(params['user_id'])
        user = models.users.get_user(user_id)
        if user is None:
            abort(404, "User doesn't exists")

    # Real work
    report = models.users.get_benefits(from_date, to_date, currency, user_id)
    return resp(pg_util.cast_for_json(report))


@api_admin.route('/reports/get_date/', methods=['GET', "POST"])
def reports_get_date():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request):
        abort(400)
    return resp(pg_util.cast_for_json(models.users.get_report_date(None)))


@api_admin.route('/reports/set_date/', methods=["POST"])
def reports_set_date():
    """
    Get data for a user
    """
    # Check params
    if not web_util.check_request_params(request, "date"):
        abort(400)
    params = web_util.get_req_params(request)

    if not type_util.ll_float(params['date']):
        abort(400, "invalid value for date")
    new_date = datetime.datetime.utcfromtimestamp(float(params['date']))

    # Real work
    models.users.save_report_date(new_date)
    return resp()


@api_admin.route('/reports/pricing_constants/', methods=["GET", "POST"])
def reports_pricing_constants():
    # Check params
    if not web_util.check_request_params(request):
        abort(400)

    default_currency = g.conf.get("currency", "main_currency")
    if default_currency == api_util.CURRENCY_YUAN:
        default_provider_currency = api_util.CURRENCY_YUAN
        margins = {
            'root': 1,
            'gold': 2,
            'silver': 10,
            'bronze': 30
        }
    else:
        default_provider_currency = api_util.CURRENCY_DOLLAR
        margins = {
            'root': 1,
            'gold': 2,
            'silver': 4,
            'bronze': 10
        }

    # Real work
    result = {
        "default_currency": default_currency,
        "zephycoin_price": float(g.conf.get("currency", "zephycoin_price")),
        "currency_to_euro": models.currencies.get_currencies_ratio("euro"),
        "margins": margins,
        "security_margin": 0.05,
        "openfoam_donations": 0.05,
        "default_price_sec_granularity": 300,
        "default_price_min_sec_granularity": 300,
        "default_cost_sec_granularity": 1,
        "default_cost_min_sec_granularity": 60,
        "default_cost_currency": default_provider_currency
    }
    return resp(result)


@api_admin.route('/currencies/', methods=["GET", "POST"])
def list_currencies():
    # Check params
    if not web_util.check_request_params(request):
        abort(400)

    currencies = models.currencies.get_currencies_to_zc()
    return resp(currencies, len(currencies))
