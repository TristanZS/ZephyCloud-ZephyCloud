# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120
"""
This file provide tools to manipulate redis with more ease
"""

# Python core libs
import datetime

# Third party lib
import redis

# Project specific lib
import type_util


def listen_pubsub(conn, channel, timeout=0):
    """
    Listen to messages from specific pubsub redis channel.
    This method work like an infinite iterator.
    On timeout, if defined, it return None

    :param conn:        A redis connection
    :type conn:         RedisWrapper|redis.StrictRedis
    :param channel:     The channel to subscribe
    :type channel:      str
    :param timeout:     The timeout, in seconds. Optional, default 0
    :type timeout:      int|float|datetime.timedelta|None
    :return:            yield the message received if any
    :rtype:             list[dict[str, any]|None]
    """
    if timeout is None or (type_util.ll_float(timeout) and float(timeout) <= 0):
        timeout_sec = 0
    elif isinstance(timeout, datetime.timedelta):
        timeout_sec = timeout.seconds
    else:
        timeout_sec = int(float(timeout))

    block = timeout_sec != 0
    subscription = conn.pubsub()
    subscription.subscribe(channel)
    try:
        while True:
            msg = subscription.parse_response(block=block, timeout=timeout_sec)
            if msg is not None:
                msg = subscription.handle_message(msg)
                if msg['type'] != "message":
                    continue
            yield msg
    finally:
        try:
            subscription.unsubscribe(channel)
        except StandardError as e:
            pass


class RedisWrapper(object):
    def __init__(self, host="localhost", port=6379, database=0):
        super(RedisWrapper, self).__init__()
        self._host = host
        self._port = port
        self._database = database
        self._conn = None

    def __getattr__(self, item):
        return getattr(self._raw_conn, item)

    @property
    def _raw_conn(self):
        if self._conn is None:
            self._conn = redis.StrictRedis(host=self._host, port=self._port, db=self._database)
        return self._conn

    def close(self):
        if not self._conn:
            return
        del self._conn
        self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __setitem__(self, name, value):
        self._raw_conn[name] = value

    def __getitem__(self, name):
        return self._raw_conn[name]

    def __contains__(self, item):
        return item in self._raw_conn

    def __delitem__(self, name):
        del self._raw_conn[name]

    def __del__(self):
        try:
            self.close()
        except StandardError:
            pass


class OpenConnectionWrapper(RedisWrapper):
    def __init__(self, conn):
        super(OpenConnectionWrapper, self).__init__()
        self._conn = conn

    @property
    def _raw_conn(self):
        return self._conn

    def close(self):
        pass
