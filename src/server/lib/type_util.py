# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libraries
import sys
import json
import collections

# Project specific libraries
import error_util


def ll_float(var):
    """
    Check parameter can be cast as a valid float

    :param var:     The variable to check
    :type var:      any
    :return:        True if the value can be cast to float
    :rtype:         bool
    """
    try:
        float(var)
        return True
    except (ValueError, TypeError):
        return False


def ll_int(var):
    """
    Check parameter looks like a valid int

    :param var:     The variable to check
    :type var:      any
    :return:        True if the value can be cast to float
    :rtype:         bool
    """
    try:
        int(var)
        return True
    except (ValueError, TypeError):
        return False


def is_string(var):
    """
    Check if parameter is a string

    :param var:     The variable to test
    :type var:      any
    :return:        True is the variable is a string or unicode
    :rtype:         bool
    """
    if sys.version_info[0] > 2:
        return isinstance(var, str)
    else:
        return isinstance(var, basestring)


def is_int(var):
    """
    Check if parameter is an int

    :param var:     The variable to test
    :type var:      any
    :return:        True is the variable is a int
    :rtype:         bool
    """
    if sys.version_info[0] > 2:
        return isinstance(var, int)
    else:
        return isinstance(var, (int, long))


def is_primitive(var):
    """
    Check if variable is primitive type, such as string or int

    :param var:     The variable to test
    :type var:      any
    :return:        True if given variable is primitive
    :rtype:         bool
    """
    return is_string(var) or is_int(var) or isinstance(var, (bool, float))


def is_array(var):
    if is_primitive(var):
        return False
    if isinstance(var, dict):
        return False
    return isinstance(var, collections.Iterable)


def is_dict(var):
    if is_primitive(var):
        return False
    return isinstance(var, dict)


def is_json(var):
    """
    Check if parameter is a valid json string

    :param var:     The variable to test
    :type var:      any
    :return:        True is the variable is a valid json string
    :rtype:         bool
    """
    if not is_string(var):
        return False
    try:
        _ = json.loads(var)
        return True
    except error_util.abort_errors: raise
    except error_util.all_errors:
        return False


def ll_bool(value):
    """
    Check if value looks like a bool

    :param value:       The value to check
    :type value:        any
    :return:            The boolean value
    :rtype:             bool
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if ll_float(value):
        return int(float(value)) in (0, 1)
    try:
        value = str(value)
    except error_util.abort_errors: raise
    except StandardError:
        return False
    if value.lower() in ('yes', 'true', 't', 'y', '1', 'o', 'oui', 'on'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0', 'non', 'off'):
        return True
    else:
        return False


def to_bool(value):
    """
    Convert a string to bool
    Raise error if not a valid bool

    :param value:       The value to cast
    :type value:        any
    :return:            The boolean value
    :rtype:             bool
    """
    if value is None:
        raise TypeError("Not a boolean")
    if isinstance(value, bool):
        return value
    if ll_float(value):
        if not int(float(value)) in (0, 1):
            raise TypeError("Not a boolean")
        return int(float(value)) == 1
    try:
        value = str(value)
    except error_util.abort_errors: raise
    except StandardError:
        raise TypeError("Not a boolean")
    if value.lower() in ('yes', 'true', 't', 'y', '1', 'o', 'oui', 'on'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0', 'non', 'off'):
        return False
    else:
        raise TypeError("Not a boolean")


def to_unicode(value):
    if sys.version_info[0] > 2:
        return str(value)
    else:
        return unicode(value)
