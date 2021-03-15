# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

import sys


class Stack(object):
    def __init__(self, skip=0):
        super(Stack, self).__init__()
        _, err, err_tb = sys.exc_info()
        err_tb = trim_traceback(err_tb, skip)
        self._err = err.with_traceback(err_tb)

    @property
    def is_abort(self):
        return python_is_abort(self._err)

    @property
    def exception(self):
        return self._err

    def reraise(self):
        raise self._err


_ABORT_ERROR_CLASSES = (KeyboardInterrupt, SystemExit)


def python_is_abort(e):
    return isinstance(e, _ABORT_ERROR_CLASSES)


def trim_traceback(tb, skip):
    for i in range(skip):
        if not tb or not tb.tb_next:
            break
        tb = tb.tb_next
    return tb
