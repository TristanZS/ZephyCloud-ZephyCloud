# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import json
import copy

# Project specific libs
from lib import type_util


class Worker(object):
    """
    A Worker represent a cloud worker machine instance for a specific cloud service
    """

    class Status(object):
        UNDEFINED = 0
        PENDING = 1
        RUNNING = 2
        SHUTTING_DOWN = 3
        TERMINATED = 4

    @staticmethod
    def unserialize(conf):
        """
        Create a specific Worker instance from the serialized data passed as parameter

        :param conf:        The serialized worker. It should be generated by calling worker.serialize()
        :type conf:         str|dict[str, str]
        :return:            A new worker instance
        :rtype:             Worker
        """
        if type_util.is_json(conf):
            conf = json.loads(conf)
        for param in ('worker_id', 'public_ip', 'private_ip'):
            if param not in conf:
                raise RuntimeError("invalid worker serialization: no " + param + " parameter")
        return Worker(conf['worker_id'], conf['public_ip'], conf['private_ip'])

    def __init__(self, worker_id, public_ip, private_ip):
        """
        :param worker_id:           The unique worker id (unique by cloud provider)
        :type worker_id:            str
        :param public_ip:           The public ip of the worker
        :type public_ip:            str|None
        :param private_ip:          The private ip of the worker
        :type private_ip:           str
        """
        self._worker_id = worker_id
        self._public_ip = public_ip
        self._private_ip = private_ip
        self._status = Worker.Status.UNDEFINED
        self._creation_date = None
        self._tags = {}
        self._specific_cost = 0
        self._specific_cost_currency = None

    def set_specific_cost(self, cost, currency):
        """
        Set specific cost in case of spot instance

        :param cost:        The specific cost, in dollar
        :type cost:         float
        :param currency:    The specific currency
        :type currency:     str
        :return:
        """
        self._specific_cost = cost
        self._specific_cost_currency = currency

    @property
    def worker_id(self):
        return self._worker_id

    @property
    def public_ip(self):
        return self._public_ip

    @property
    def private_ip(self):
        return self._private_ip

    @property
    def status(self):
        return self._status

    @property
    def creation_date(self):
        return self._creation_date

    @property
    def specific_cost(self):
        return self._specific_cost

    @property
    def specific_cost_currency(self):
        return self._specific_cost_currency

    def get_tag(self, value):
        """
        read a tag value
        :param value:   The tag name you want
        :type value:    String
        :return:        The tag value
        :rtype:         String
        """
        if value not in self._tags.keys():
            return None
        return self._tags[value]

    @property
    def tags(self):
        """
        Get all tags

        :return:        all the worker tags
        :rtype:         dict[str, str]
        """
        return copy.deepcopy(self._tags)

    def set_tags(self, tags):
        self._tags.update(tags)

    def set_status(self, status):
        self._status = status

    def set_creation_date(self, date):
        self._creation_date = date.replace(tzinfo=None)

    def serialize(self):
        """
        Dump a worker configuration string
        :return:        A String used to recreate the worker (see Worker.unserialize)
        :rtype:         String
        """
        return json.dumps({'worker_id': self.worker_id, 'public_ip': self.public_ip, 'private_ip': self.private_ip})

    def __eq__(self, other):
        if not isinstance(other, Worker):
            return False
        if self.worker_id != other.worker_id:
            return False
        return self.public_ip == other.public_ip and self.private_ip == other.private_ip