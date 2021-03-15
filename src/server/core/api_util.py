# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core 
import os
import json
import logging
import contextlib
import datetime
import time
import math
import smtplib
import email.mime.text
import threading
import collections
import re

# Third party 
import redis
import psycopg2

# Project specific
from lib import util
from lib import meta_util
from lib import error_util
from lib import pg_util
from lib import redis_util
from lib import type_util
import provider
import storages


API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRICE_PRECISION = 100000000  # 10^8 (could be a problem after 92 billions dollar/zephycoins)

CURRENCY_DOLLAR = "dollar"
CURRENCY_YUAN = "yuan"
CURRENCY_EURO = "euro"

OPENFOAM_DONATION_RATIO = 0.05

# Worker path definitions
WORKER_HOME = "/home/aziugo"
WORKER_SCRIPTS_PATH = util.path_join(WORKER_HOME, "worker_scripts")
WORKER_INPUT_PATH = util.path_join(WORKER_SCRIPTS_PATH, "inputs")
WORKER_OUTPUT_PATH = util.path_join(WORKER_SCRIPTS_PATH, "outputs")
WORKER_RUNNER_PATH = util.path_join(WORKER_SCRIPTS_PATH, "aziugo_start.py")
WORKER_LAUNCHER_PATH = util.path_join(WORKER_SCRIPTS_PATH, "python_venv.sh")
WORKER_WORK_PATH = util.path_join(WORKER_SCRIPTS_PATH, "workdir")

log = logging.getLogger("aziugo")


class NoMoreCredits(RuntimeError):
    pass


class ToolchainError(RuntimeError):
    pass


class ToolchainCanceled(RuntimeError):
    pass


abort_errors = tuple([ToolchainCanceled] + list(error_util.abort_errors))


def price_to_float(price):

    """
    Transform our internal price representation into a price per second in float format

    :param price:   The price per second
    :type price:    int|float
    :return:        The price per second in float format
    :rtype:         float
    """
    return float(price)/PRICE_PRECISION


def price_from_float(price):
    """
    Transform a price per second in float format to our internal price representation

    :param price:   The price per second
    :type price:    float
    :return:        The internal price, in fixed point format
    :rtype:         int
    """
    return int(math.floor(price*PRICE_PRECISION))


def bytes_to_gbytes(size):
    """
    Convert a binary size from byte count to gigabytes

    :param size:    The number of byte
    :type size:     int
    :return:        The number of gigabytes
    :rtype:         float
    """
    return float(size)/1073741824


def gbytes_to_bytes(size):
    """
    Convert a gigabytes count to an number of bytes

    :param size:    The number of gigabytes
    :type size:     float
    :return:        The number of bytes
    :rtype:         int
    """
    return int(round(size*1073741824))


def addr(obj):
    return hex(id(obj))


class DatabaseContext(object):
    _thread_local = threading.local()
    _dsn = None

    @staticmethod
    def set_dsn(dsn):
        DatabaseContext._dsn = dsn

    @staticmethod
    def get_dsn():
        if not DatabaseContext._dsn:
            raise RuntimeError("Database context dsn is not defined")
        return DatabaseContext._dsn

    @staticmethod
    def load_conf():
        conf = get_conf()
        database = conf.get("database", "db_name")
        user = conf.get("database", "user", "postgres")
        password = conf.get("database", "password", "")
        host = conf.get("database", "host", "localhost")
        port = conf.getint("database", "port") if conf.has_option("database", "port") else 5432

        dsn = "dbname='"+database+"' "
        dsn += "host='" + host + "' "
        dsn += "port='" + str(port) + "' "
        dsn += "user='" + user + "' "
        dsn += "password='" + password + "' "
        DatabaseContext._dsn = dsn

    @staticmethod
    def get_conn():
        if not hasattr(DatabaseContext._thread_local, "conn"):
            dsn = DatabaseContext.get_dsn()
            DatabaseContext._thread_local.conn = pg_util.ConnectionWrapper(dsn=dsn)
        return DatabaseContext._thread_local.conn

    @staticmethod
    def set_conn(conn):
        DatabaseContext.clean()
        DatabaseContext._thread_local.conn = conn

    @staticmethod
    def clean():
        if not hasattr(DatabaseContext._thread_local, "conn"):
            return
        try:
            DatabaseContext._thread_local.conn.close()
        except StandardError as e:
            log.warning(str(e))
        delattr(DatabaseContext._thread_local, "conn")

    @staticmethod
    @contextlib.contextmanager
    def using_conn():
        database_created = False
        if not hasattr(DatabaseContext._thread_local, "conn"):
            database_created = True
        conn = DatabaseContext.get_conn()
        try:
            yield conn
        finally:
            if database_created:
                DatabaseContext.clean()


class RedisContext(object):
    _api_name = None
    _server_name = None
    _host = None
    _port = None
    _data_db = None
    _pubsub_db = None

    _thread_local = threading.local()

    @staticmethod
    def set_params(api_name, server_name, host, port, data_db, pubsub_db):
        RedisContext._api_name = api_name
        RedisContext._server_name = server_name
        RedisContext._host = host
        RedisContext._port = port
        RedisContext._data_db = data_db
        RedisContext._pubsub_db = pubsub_db

    @staticmethod
    def get_host():
        if not RedisContext._host:
            raise RuntimeError("Redis context params are not defined")
        return RedisContext._host

    @staticmethod
    def get_port():
        if not RedisContext._port:
            raise RuntimeError("Redis context params are is not defined")
        return RedisContext._port

    @staticmethod
    def get_data_db():
        if RedisContext._data_db is None:
            raise RuntimeError("Redis context params are not defined")
        return RedisContext._data_db

    @staticmethod
    def get_pubsub_db():
        if RedisContext._pubsub_db is None:
            raise RuntimeError("Redis context params are not defined")
        return RedisContext._pubsub_db

    @staticmethod
    def get_channel(name):
        if any(v is None for v in (RedisContext._host, RedisContext._port, RedisContext._pubsub_db,
                                   RedisContext._data_db, RedisContext._api_name, RedisContext._server_name)):
            raise RuntimeError("Redis context is not defined")
        return RedisContext._api_name+":"+RedisContext._server_name+":"+name

    @staticmethod
    def load_conf():
        conf = get_conf()
        RedisContext._api_name = conf.get('general', 'api_name')
        RedisContext._server_name = conf.get('general', "server")

        RedisContext._host = "localhost"
        RedisContext._port = 6379
        RedisContext._data_db = 0
        RedisContext._pubsub_db = 1

    @staticmethod
    def get_data_conn():
        if not hasattr(RedisContext._thread_local, "data_conn"):
            if any(v is None for v in (RedisContext._host, RedisContext._port, RedisContext._pubsub_db,
                                       RedisContext._data_db, RedisContext._api_name, RedisContext._server_name)):
                raise RuntimeError("Redis context is not defined")

            RedisContext._thread_local.data_conn = redis_util.RedisWrapper(host=RedisContext._host,
                                                                           port=RedisContext._port,
                                                                           database=RedisContext._data_db)
        return RedisContext._thread_local.data_conn

    @staticmethod
    def get_pubsub_conn():
        if not hasattr(RedisContext._thread_local, "pubsub_conn"):
            if any(v is None for v in (RedisContext._host, RedisContext._port, RedisContext._pubsub_db,
                                       RedisContext._data_db, RedisContext._api_name, RedisContext._server_name)):
                raise RuntimeError("Redis context is not defined")

            RedisContext._thread_local.pubsub_conn = redis_util.RedisWrapper(host=RedisContext._host,
                                                                             port=RedisContext._port,
                                                                             database=RedisContext._pubsub_db)
        return RedisContext._thread_local.pubsub_conn

    @staticmethod
    def clean_data():
        if not hasattr(RedisContext._thread_local, "data_conn"):
            return
        try:
            RedisContext._thread_local.data_conn.close()
        except StandardError as e:
            log.warning(str(e))
        delattr(RedisContext._thread_local, "data_conn")

    @staticmethod
    def clean_pubsub():
        if not hasattr(RedisContext._thread_local, "pubsub_conn"):
            return
        try:
            RedisContext._thread_local.pubsub_conn.close()
        except StandardError as e:
            log.warning(str(e))
        delattr(RedisContext._thread_local, "pubsub_conn")

    @staticmethod
    def clean():
        RedisContext.clean_data()
        RedisContext.clean_pubsub()

    @staticmethod
    @contextlib.contextmanager
    def using_data_conn():
        created_data = False
        if not hasattr(RedisContext._thread_local, "data_conn"):
            created_data = True
        try:
            yield RedisContext.get_data_conn()
        finally:
            if created_data:
                RedisContext.clean_data()

    @staticmethod
    @contextlib.contextmanager
    def using_pubsub_conn():
        created_pubsub = False
        if not hasattr(RedisContext._thread_local, "pubsub_conn"):
            created_pubsub = True
        try:
            yield RedisContext.get_pubsub_conn()
        finally:
            if created_pubsub:
                RedisContext.clean_pubsub()

    @staticmethod
    @contextlib.contextmanager
    def using_conn():
        with RedisContext.get_data_conn() as data_conn:
            with RedisContext.get_pubsub_conn() as pubsub_conn:
                yield data_conn, pubsub_conn


@meta_util.func_decorator
def need_redis_context(func, func_args, func_kwargs):
    with RedisContext.using_conn():
        return func(*func_args, **func_kwargs)


def wait_for_postgres(timeout=30):
    """
    Try to connect to postgres for X seconds.
    Raise an Error if it doesn't succeed after the timeout
    If the timeout id None or 0, it never raise timeout error

    :param timeout:         The timeout, in seconds. Optional default 30 s
    :type timeout:          int|float|datetime.timedelta|None
    """

    with util.using_timeout(timeout):
        try_pg_conn()


def try_pg_conn():
    while True:
        conn = None
        try:
            conn = psycopg2.connect(dsn=DatabaseContext.get_dsn())
            return
        except psycopg2.OperationalError:
            pass
        finally:
            try:
                if conn:
                    conn.close()
            except StandardError:
                pass


class ConfMemory(object):
    memory = None


def get_conf():
    if ConfMemory.memory is None:
        ConfMemory.memory = util.load_ini_file(os.path.join(API_PATH, 'config.conf'))
    return ConfMemory.memory


@meta_util.func_decorator
def need_db_context(func, func_args=None, func_kwargs=None):
    with DatabaseContext.using_conn():
        return func(*func_args, **func_kwargs)


@need_db_context
def now():
    g_db = DatabaseContext.get_conn()
    return pg_util.get_now(g_db)


class QuotaLimiter(object):
    """ This class define a quota for a limited period of time """
    def __init__(self, time_period, max_events):
        """
        :param time_period:         The time slice for limiting events
        :type time_period:          datetime.timedelta
        :param max_events:          The number of events
        :type max_events:           int
        """
        super(QuotaLimiter, self).__init__()
        self._queue = collections.deque(maxlen=max_events+1)
        self._period = time_period
        self._max_events = max_events

    def try_event(self):
        """
        Count the event and tell if the event is under the quota

        :return:        True if the event match the quota, False otherwise
        :rtype:         bool
        """
        dt_now = datetime.datetime.utcnow()
        self._queue.append(dt_now)
        if len(self._queue) <= self._max_events:
            return True
        return self._queue[0] < (dt_now - self._period)


class EmailQuotaLimiter(object):
    _instance = None

    @staticmethod
    def get():
        if EmailQuotaLimiter._instance is None:
            conf = get_conf()
            quota_period = datetime.timedelta(milliseconds=int(conf.get('email', 'quota_period')))
            quota_limit = int(conf.get('email', "quota_limit"))
            EmailQuotaLimiter._instance = QuotaLimiter(quota_period, quota_limit)
        return EmailQuotaLimiter._instance


def send_email(destination, subject, content, skip_quota=False):
    if not skip_quota:
        limiter = EmailQuotaLimiter.get()
        if not limiter.try_event():
            log.warning("Email quotas exhausted, didn't sent the email")
            return

    conf = get_conf()
    api_name = conf.get('general', 'api_name')
    server_name = conf.get('general', "server")
    smtp_user = conf.get('email', 'smtp_user')
    smtp_pwd = conf.get('email', 'smtp_pwd')
    smtp_server = conf.get('email', 'smtp_server')
    smtp_port = conf.getint('email', 'smtp_port')

    if server_name.endswith(".local") or server_name.endswith(".dev"):
        user_from = api_name + "@aziugo.com"
        sender_server = "aziugo.com"
    else:
        user_from = api_name + "@" + server_name
        sender_server = server_name

    msg = email.mime.text.MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = user_from
    msg['To'] = destination

    if smtp_port == 25:
        smtp_conn = smtplib.SMTP(smtp_server, smtp_port, sender_server)
    else:
        smtp_conn = smtplib.SMTP_SSL(smtp_server, smtp_port, sender_server)
    try:
        smtp_conn.login(smtp_user, smtp_pwd)
        smtp_conn.sendmail(user_from, [destination], msg.as_string())
    except error_util.abort_errors: raise
    except error_util.all_errors as e:
        log.warning(e)
    finally:
        smtp_conn.quit()


def send_admin_email(subject, content, dest_email=None, skip_quota=False):
    conf = get_conf()
    if dest_email is None:
        dest_email = conf.get('email', 'admin_email')
    api_name = conf.get('general', 'api_name')
    server_name = conf.get('general', "server")
    full_subject = "[%s][%s] %s" % (api_name, server_name, subject)
    thread = threading.Thread(target=send_email, args=(dest_email, full_subject, content, skip_quota))
    thread.daemon = True
    thread.start()


def get_provider(provider_name):
    """

    :param provider_name:
    :type provider_name:
    :return:
    :rtype:
    """
    conf = get_conf()
    api_name = conf.get('general', 'api_name')
    tmp_folder = os.path.abspath(conf.get('general', 'tmp_folder'))
    allowed_providers = json.loads(conf.get("general", "allowed_providers"))
    if provider_name not in allowed_providers:
        raise ToolchainError("Unknown provider " + str(provider_name))
    provider_type = conf.get("provider_" + provider_name, "type")
    if provider_type == "aws":
        return provider.AwsProvider(conf, provider_name)
    elif provider_type == "aws_spot":
        return provider.AwsSpotProvider(conf, provider_name)
    elif provider_type == "docker":
        docker_tmp_folder = os.path.join(tmp_folder, api_name)
        return provider.DockerProvider(conf, provider_name, docker_tmp_folder)
    else:
        raise ToolchainError("Unknown provider type " + str(provider_type))


def get_all_providers():
    conf = get_conf()
    conf.read(os.path.join(API_PATH, 'config.conf'))
    allowed_providers = json.loads(conf.get("general", "allowed_providers"))
    cloud_providers = []
    for provider_name in allowed_providers:
        cloud_providers.append(get_provider(provider_name))
    return cloud_providers


def wait_for_redis(timeout=2):
    """
    Wait for redis connection, raising error on timeout
    If timeout is 0 or None, it never stop waiting for redis

    :param timeout:         The amount of seconds before we rise an error. Optional, default 2 seconds
    :type timeout:          int|float|datetime.timedelta|None
    :return:
    """
    if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
        time_limit = None
    else:
        if not isinstance(timeout, datetime.timedelta):
            timeout = datetime.timedelta(milliseconds=int(float(timeout)*1000))
        time_limit = datetime.datetime.utcnow() + timeout

    while True:
        try:
            conn = redis.StrictRedis(host=RedisContext.get_host(),
                                     port=RedisContext.get_port(),
                                     db=RedisContext.get_data_db())
            del conn
            return
        except redis.ConnectionError:
            with error_util.saved_stack() as err:
                if time_limit is not None and datetime.datetime.utcnow() > time_limit:
                    err.reraise()
                time.sleep(0.1)


def get_storage(storage_name):
    conf = get_conf()
    return storages.Storage.load(conf, storage_name)


def clean_login(input_login):
    return re.sub(r"\.+", ".", re.sub(r"[^a-z.]+", ".", input_login.strip().lower())).strip(".")


def is_email_valid(input_email):
    if len(input_email) <= 7:
        return False
    return re.match(r"^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", input_email) is not None
