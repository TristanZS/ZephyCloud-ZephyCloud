# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core api
import datetime

# Project specific libs
import core.api_util


class TimeMetric(object):
    def __init__(self, label, job_id=None, estimated=None, **additional_fields):
        if isinstance(estimated, datetime.timedelta):
            estimated = estimated.seconds
        elif isinstance(estimated, datetime.datetime):
            estimated = int(estimated.strftime("%s"))

        self._start_time = int(datetime.datetime.utcnow().strftime("%s"))
        self._label = label
        self._job_id = job_id
        self._estimated = estimated
        self._additional_fields = additional_fields
        self._saved = False

    @core.api_util.need_db_context
    def save(self):
        if self._saved:
            raise RuntimeError("Metric have already been saved")
        end_time = int(datetime.datetime.utcnow().strftime("%s"))
        g_db = core.api_util.DatabaseContext.get_conn()
        g_db.execute("""INSERT INTO time_metrics (label, start_time, end_time, job_id, estimated, fields)
                                        VALUES (%s, %s, %s, %s, %s)""",
                     [self._label, self._start_time, end_time, self._job_id, self._estimated, self._additional_fields])
        self._saved = True
