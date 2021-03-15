#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import sys
import os
import logging
import logging.handlers
import argparse
import threading
import time

# Third party libraries
import colorlog
import redis
import tornado.ioloop
import tornado.websocket
import tornado.httpserver
import tornado.web
import watchdog.events
import watchdog.observers

# Project specific libs
from lib import util
from lib import type_util
from lib import async_util
from lib import error_util
from core import api_util

DEFAULT_BIND = "localhost"
DEFAULT_PORT = 5000
API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class WebsocketClient(tornado.websocket.WebSocketHandler):
    """
    Represent a client websocket connection
    """

    _connected_clients = set([])  # List of connected clients, :type: set[WebsocketClient]

    @staticmethod
    def get_all():
        """
        Get all connected clients
        :return:    All opened client connections
        :rtype:     set[WebsocketClient]
        """
        return WebsocketClient._connected_clients

    def __init__(self, *args, **kwargs):
        super(WebsocketClient, self).__init__(*args, **kwargs)

    def open(self, *args, **kwargs):
        if self not in WebsocketClient._connected_clients:
            WebsocketClient._connected_clients.add(self)

    def on_close(self):
        if self in WebsocketClient._connected_clients:
            WebsocketClient._connected_clients.remove(self)

    def check_origin(self, origin):
        return True

    def data_received(self, chunk):
        """
        Callback when a client send a binary chunk of data to the server
        :param chunk:       The content the client sent to the server
        :type chunk:        str
        """

    def on_message(self, message):
        """
        Callback when a client send a message to the server
        :param message:     The content the client sent to the server
        :type message:      str
        """
        # FIXME ZOPEN: what to do on message received from client
        # example: logging.debug("message received from client:"+repr(message))
        pass


def redis_listener(io_loop, redis_channel):
    """
    Listen to redis message, and forward event to tornado clients
    Note: this should be called in a separated thread

    :param io_loop:         The tornado loop
    :type io_loop:          tornado.ioloop.IOLoop
    :param redis_channel:   The name of the redis pubsub channel
    :type redis_channel:    str
    """
    api_util.wait_for_redis()
    with api_util.RedisContext.using_pubsub_conn() as r:
        subscription = r.pubsub()
        subscription.subscribe(redis_channel)
        try:
            while True:
                for message in subscription.listen():
                    io_loop.add_callback(on_redis_message, message['data'])
        except error_util.abort_errors:
            return


class SrcCodeEventHandler(watchdog.events.PatternMatchingEventHandler):
    def __init__(self, queue):
        super(SrcCodeEventHandler, self).__init__(ignore_patterns=["*.pyc"])
        self._queue = queue

    def on_any_event(self, event):
        self._queue.put("changes")


def change_notifier():
    """
    Listen to source code changes and restart application.
    This function never end, you should call it in a thread
    """

    queue = async_util.create_thread_queue()
    evt_handler = SrcCodeEventHandler(queue)
    observer = watchdog.observers.Observer()
    observer.schedule(evt_handler, os.path.join(API_PATH, "app"), recursive=True)
    observer.start()
    queue.get(block=True)
    observer.stop()
    logging.getLogger("aziugo").info("Code change detected, restarting websocket server")
    time.sleep(1)
    os.execv(__file__, sys.argv)


def on_redis_message(message):
    """
    What to do when a message is received from server
    :param message:     message received from redis
    :type message:      str
    """

    # Example:
    # for listener in WebsocketClient.get_all():
    #     listener.write_message(message['data'])


def run_server(api_name, server_name, bind, port, redis_host="localhost", redis_port=6379, data_db=0, pubsub_db=1,
               reload=False):
    logging.getLogger("aziugo").info("Starting " + api_name + " websocket server")

    api_util.DatabaseContext.load_conf()
    api_util.wait_for_postgres()

    io_loop = tornado.ioloop.IOLoop.instance()

    api_util.RedisContext.set_params(api_name, server_name, redis_host, redis_port, data_db, pubsub_db)
    redis_thread = threading.Thread(target=redis_listener, args=(io_loop, api_name+":"+server_name+":notifications"))
    redis_thread.daemon = True
    redis_thread.start()

    if reload:
        reload_thread = threading.Thread(target=change_notifier)
        reload_thread.daemon = True
        reload_thread.start()

    application = tornado.web.Application([(r'/websocket(/.*)?', WebsocketClient)])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port, bind)
    io_loop.start()


def main():
    parser = argparse.ArgumentParser(description='Websocket server')
    parser.add_argument('--bind', '-b', help="Address to bind, default "+DEFAULT_BIND)
    parser.add_argument('--port', '-p', help="Main port to listen, default "+str(DEFAULT_PORT))
    parser.add_argument('--redis-host', '-H', help="Redis-server host")
    parser.add_argument('--redis-port', '-P', help='Redis-server connection port')
    parser.add_argument('--redis-data-db', '-i', help="Redis-server database index for data")
    parser.add_argument('--redis-pubsub-db', '-j', help="Redis-server database index for events")
    parser.add_argument('--log-level', '-l', help="log level (ex: info)")
    parser.add_argument('--log-output', help="log out, file path, 'syslog', 'stderr' or 'stdout'")
    parser.add_argument('--reload', '-r', action='store_true', help="Auto restart execution on code change")

    args = parser.parse_args()

    conf = api_util.get_conf()
    conf.read(os.path.join(API_PATH, 'config.conf'))
    api_name = conf.get('general', 'api_name')
    server_name = conf.get('general', 'server')

    # Initialise logging
    if args.log_level:
        log_level = args.log_level.strip().upper()
    elif conf.has_section("log") and conf.has_option("log", "websocket_level"):
        log_level = conf.get("log", "websocket_level").strip().upper()
    else:
        log_level = "WARNING"
    log_level_int = logging.getLevelName(log_level)
    if not type_util.is_int(log_level_int):
        sys.stderr.write("Error: Invalid logging level "+repr(log_level)+"\n")
        sys.stderr.flush()
        return 1
    logging.getLogger().setLevel(logging.INFO if log_level_int < logging.INFO else log_level_int)
    log = logging.getLogger("aziugo")
    log.setLevel(log_level_int)

    if args.log_output:
        log_output = args.log_output.strip().lower()
    elif conf.has_section("log") and conf.has_option("log", "websocket_output"):
        log_output = conf.get("log", "websocket_output").strip().lower()
    else:
        log_output = "stderr"
    if log_output in ("stderr", "stdout"):
        log_file = sys.stderr if log_output == "stderr" else sys.stdout
        if log_file.isatty():
            use_color = not util.env_is_off("LOG_COLOR")
        else:
            use_color = util.env_is_on("LOG_COLOR")
        if use_color:
            log_format = "%(log_color)s%(levelname)-8s%(blue)s%(name)-16s%(reset)s %(white)s%(message)s"
            log_handler = colorlog.StreamHandler(stream=log_file)
            log_handler.setFormatter(colorlog.ColoredFormatter(log_format))
        else:
            log_handler = logging.StreamHandler(stream=log_file)
            log_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    elif log_output == "syslog":
        log_handler = logging.handlers.SysLogHandler(address='/dev/log')
        log_handler.setFormatter(logging.Formatter('%(levelname)s %(module)s P%(process)d T%(thread)d %(message)s'))
    else:
        log_handler = logging.FileHandler(log_output)
        log_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-7s: %(name)s - %(message)s'))
    logging.getLogger().addHandler(log_handler)
    log.addHandler(log_handler)
    log.propagate = False

    # Get Websocket
    if args.bind:
        bind = args.bind.strip()
    elif conf.has_section("websocket") and conf.has_option("websocket", "bind"):
        bind = conf.get("websocket", "bind").strip()
    elif util.has_filled_value(os.environ, "WEBSOCKET_BIND"):
        bind = os.environ["WEBSOCKET_BIND"].strip()
    else:
        bind = DEFAULT_BIND
    if args.port:
        port = int(args.port.strip())
    elif conf.has_section("websocket") and conf.has_option("websocket", "port"):
        port = int(conf.get("websocket", "port").strip())
    elif util.has_filled_value(os.environ, "WEBSOCKET_PORT"):
        port = int(os.environ["WEBSOCKET_PORT"].strip())
    else:
        port = DEFAULT_PORT

    # Get Redis config
    if args.redis_host:
        redis_host = args.redis_host.strip()
    elif conf.has_section("redis") and conf.has_option("redis", "host"):
        redis_host = conf.get("redis", "host").strip()
    else:
        redis_host = "localhost"
    if args.redis_port:
        redis_port = int(args.redis_port.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "port"):
        redis_port = int(conf.get("redis", "port").strip())
    else:
        redis_port = 6379
    if args.redis_data_db:
        redis_data_db = int(args.redis_data_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "data_db"):
        redis_data_db = int(conf.get("redis", "data_db").strip())
    else:
        redis_data_db = 0
    if args.redis_pubsub_db:
        redis_pubsub_db = int(args.redis_pubsub_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "pubsub_db"):
        redis_pubsub_db = int(conf.get("redis", "pubsub_db").strip())
    else:
        redis_pubsub_db = 1

    if args.reload:
        auto_reload = True
    elif util.env_is_on("AUTO_RELOAD_CODE"):
        auto_reload = True
    else:
        auto_reload = False

    try:
        run_server(api_name, server_name, bind, port,
                   redis_host, redis_port, redis_data_db, redis_pubsub_db,
                   reload=auto_reload)
    except error_util.abort_errors:
        logging.getLogger("aziugo").info("Signal received, exiting")
        return 0
    except error_util.all_errors as e:
        logging.getLogger("aziugo").exception(str(e))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
