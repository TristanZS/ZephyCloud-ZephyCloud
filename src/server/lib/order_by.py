# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import re


class OrderBy(object):
    FIELD_FORMAT = re.compile(r"^([a-z_0-9]+)(?: *(asc|desc))?$")

    def __init__(self, valid_fields):
        self._valid = True
        self._issue = None
        self._fields = []
        self._reverse = []
        self._valid_fields = valid_fields

    def is_empty(self):
        return len(self._fields) <= 0

    def is_valid(self):
        return self._valid

    def to_sql(self, fields_mapping=None):
        if not self.is_valid():
            raise RuntimeError("Unable to generate sql order clause from invalid OrderBy object")
        if fields_mapping is None:
            fields_mapping = {}
        if self.is_empty():
            return ""
        results = []
        for i in range(len(self._fields)):
            field = self._fields[i]
            if field in fields_mapping.keys():
                field = fields_mapping[field]
            field += " DESC" if self._reverse[i] else " ASC"
            results.append(field)
        return " ORDER BY "+", ".join(results)

    def sort_list(self, list_to_sort, fields_mapping=None):
        """

        :param list_to_sort:
        :type list_to_sort:                 list[any]
        :param fields_mapping:
        :type fields_mapping:
        :return:
        :rtype:
        """
        if not self.is_valid():
            raise RuntimeError("Unable to sort list from invalid OrderBy object")
        if fields_mapping is None:
            fields_mapping = {}
        result = copy.deepcopy(list_to_sort)
        if self.is_empty():
            return result
        for i in range(len(self._fields)):
            index = (i+1)*-1
            field = self._fields[index]
            if field in fields_mapping.keys():
                field = fields_mapping[field]
            if callable(field):
                result.sort(key=field, reverse=self._reverse[index])
            else:
                result.sort(key=lambda x: x[field], reverse=self._reverse[index])
        return result

    def sort_list_in_place(self, list_to_sort, fields_mapping=None):
        if not self.is_valid():
            raise RuntimeError("Unable to sort list from invalid OrderBy object")
        if fields_mapping is None:
            fields_mapping = {}
        if self.is_empty():
            return
        for i in range(len(self._fields)):
            index = (i+1)*-1
            field = self._fields[index]
            if field in fields_mapping.keys():
                field = fields_mapping[field]
            if callable(field):
                list_to_sort.sort(key=field, reverse=self._reverse[index])
            else:
                list_to_sort.sort(key=lambda x: x[field], reverse=self._reverse[index])

    @property
    def issue(self):
        return str(self._issue)

    def reset(self):
        self._valid = True
        self._issue = None
        self._fields = []
        self._reverse = []

    def parse(self, order):
        order = order.strip()
        if not order:
            self._set_error("empty order")
            return
        results = []
        order_sections = order.split(",")
        for section in order_sections:
            section = section.strip()
            if not section:
                self._set_error("empty part in order")
                return
            match = re.match(OrderBy.FIELD_FORMAT, section.lower())
            if not match:
                self._set_error("invalid part in order")
                return
            field = match.group(1)
            if field not in self._valid_fields:
                self._set_error("unknown order field "+repr(field))
                return
            direction = match.group(2)
            results.append((field, direction == "desc"))
        self.reset()
        for field, reverse in results:
            self._fields.append(field)
            self._reverse.append(reverse)

    def _set_error(self, issue):
        if self._issue:
            return
        self._issue = issue
        self._valid = False
