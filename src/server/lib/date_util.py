# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
Provide some utilities for date manipulation
"""

# Python core libraries
import time
import datetime

# Third party libs
import dateutil.parser

# Project specific libs
import util
import type_util


def to_dt(var):
    if var is None:
        return None
    if isinstance(var, datetime.datetime):
        if var.tzinfo is None or var.tzinfo.utcoffset(var) is None:
            return var.replace(tzinfo=None)
        return var
    if type_util.ll_int(var) or type_util.ll_float(var):
        return dt_to_timestamp(var)
    return dateutil.parser.parse(str(var))


def add_years(d, years):
    """Return a date that's `years` years after the date (or datetime)
    object `d`. Return the same calendar date (month and day) in the
    destination year, if it exists, otherwise use the following day
    (thus changing February 29 to March 1).

    """
    try:
        return d.replace(year = d.year + years)
    except ValueError:
        return d + (datetime.date(d.year + years, 1, 1) - datetime.date(d.year, 1, 1))

def dt_to_timestamp(dt, default=None):
    """
    Convert a datetime object to a timestamp

    :param dt:          The input datetime
    :type dt:           datetime.datetime|None
    :param default:     What to return if the input is invalid. Optional, default None
    :type default:      int|None
    :return:            The timestamp
    :rtype:             int|None
    """
    if dt is None:
        return default
    epoch = datetime.datetime.utcfromtimestamp(0)
    return(dt - epoch).total_seconds()


def format_date(timestamp, date_format='%Y/%m/%d-%H:%M', default=None):
    """
    Format a timestamp to human readable format

    :param timestamp:       The timestamp, expecting UTC zone, in seconds
    :type timestamp:        int|datetime|None
    :param date_format:     The format of the output, in datetime.strftime format. Optional, default YYYY/MM/DD-hh:mm
    :type date_format:      str
    :param default:         What to return if the input is invalid. Optional, default None
    :type default:          str|None
    :return:                The formatted date
    :rtype:                 str|None
    """
    if timestamp is None:
        return default
    if type_util.is_int(timestamp):
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    return timestamp.strftime(date_format)


def date_iso8601_to_timestamp(date_str):
    """
    Convert a date string in ISO8601 to unix timestamp

    :param date_str:    A date in the ISO8601 format
    :type date_str:     str
    :return:            Unix timestamp
    :rtype:             str
    """
    timestamp = time.mktime(datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
    return str(timestamp)


def dt_to_iso8601(date):
    """
    Convert a datetime object to string in ISO8601 format

    :param date:    The date to convert
    :type date:     datetime.datetime
    :return:        A ISO8601 formatted string
    :rtype:         str
    """
    return date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def duration_to_hr(duration):
    """
    Return a string representing the given duration in a human readable format (like "5 hours, 2 minutes")

    :param duration:    The duration you want to format to string
    :type duration:     datetime.timedelta
    :return:            The formatted duration string (ex: "5 hours, 2 minutes")
    :rtype:             str
    """
    days = duration.days
    hours = duration.seconds / 3600
    minutes = (duration.seconds % 3600) / 60
    seconds = duration.seconds % 60

    parts = []
    if days > 0:
        unit_str = "day" if days == 1 else "days"
        parts.append("%s %s" % (str(days), unit_str))
    if hours > 0:
        unit_str = "hour" if hours == 1 else "hours"
        parts.append("%s %s" % (str(hours), unit_str))
    if minutes > 0:
        unit_str = "min" if minutes == 1 else "mins"
        parts.append("%s %s" % (str(minutes), unit_str))
    if seconds > 0:
        unit_str = "sec" if seconds == 1 else "secs"
        parts.append("%s %s" % (str(seconds), unit_str))
    return ", ".join(parts) if parts else "now"


def round_duration(duration, round_to=None):
    """
    Round a duration (to skip seconds for example)

    :param duration:    The duration you want to round
    :type duration:     datetime.timedelta
    :param round_to:    what final precision do you want (the higher the less precise),
                        or None for auto rounding
    :type round_to:     int|None
    :return:            the rounded duration
    :rtype:             datetime.timedelta
    """

    if round_to is None:    # Arbitrary rounding computation
        hours = duration.seconds / 3600
        minutes = (duration.seconds % 3600) / 60
        if duration.days > 10 or (duration.days > 5 and hours < 4):
            round_to = 3600*24
        elif duration.days > 1:
            round_to = 3600
        elif hours > 20:
            round_to = 600
        elif hours > 0 or minutes > 20:
            round_to = 60
        else:
            round_to = 0

    if round_to == 0:   # no rounding, so nothing to do
        return duration

    seconds = duration.days*(3600*24) + duration.seconds
    rounded_seconds = util.round_int(seconds, round_to)
    return datetime.timedelta(seconds=rounded_seconds)

