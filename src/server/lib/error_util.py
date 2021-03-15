# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libraries
import sys
import contextlib
import subprocess

# Third party libs
import tblib.pickling_support


all_errors = BaseException
not_abort_errors = Exception
abort_errors = (KeyboardInterrupt, SystemExit)
# Not managed exception: GeneratorExit

if sys.version_info[0] >= 3:
    from .error_util_p3 import *
else:
    from .error_util_p2 import *


@contextlib.contextmanager
def saved_stack():
    stack = Stack(1)
    yield stack


@contextlib.contextmanager
def before_raising():
    stack = Stack(1)
    try:
        yield stack
    finally:
        stack.reraise()


def is_abort(e):
    return python_is_abort(e)


class MultiprocessingExceptions(object):
    _is_initialized = False

    @staticmethod
    def init():
        if MultiprocessingExceptions._is_initialized:
            return
        tblib.pickling_support.install()
        MultiprocessingExceptions._is_initialized = True


def log_error(log, e):
    log.exception(e)
    if isinstance(e, subprocess.CalledProcessError) and e.output:
        log.error("Output:  \n"+str(e.output).strip())

