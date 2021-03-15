# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This file define a simple and interruptable thread
"""

# Python core libs
import threading
import sys
import abc
import datetime
import multiprocessing
import time
import os
import signal

# Project specific lib
import error_util
import proc_util

# FIXME LATER: add usage example


def create_thread_queue(maxsize=0):
    if sys.version_info[0] >= 3:
        import queue
        return queue.Queue(maxsize)
    else:
        import Queue
        return Queue.Queue(maxsize)


if sys.version_info[0] >= 3:
    import queue
    QueueEmpty = queue.Empty
else:
    import Queue
    QueueEmpty = Queue.Empty


class AbstractThread(threading.Thread):
    """
    Simple thread which can be interrupted, with some basic error management
    You should override this class and implement `work` function to use this class
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, group=None, name=None, verbose=None):
        super(AbstractThread, self).__init__(group=group, name=name, verbose=verbose)
        self.daemon = True
        self._stop_queue = create_thread_queue()
        self._should_stop = False
        self._exc_info = None
        self._succeed = False

    def run(self, *args, **kargs):
        try:
            self.work(*args, **kargs)
            self._succeed = True
        except error_util.all_errors:
            self._exc_info = error_util.Stack()

    @abc.abstractmethod
    def work(self, *args, **kargs):
        """
        You should override this method. It will be run in the separated thread
        For long task, you should call self.is_stopped() regularly to
        check if you should quit.
        """
        pass

    def stop(self):
        """ Tell the thread to stop """
        self._should_stop = True
        self._stop_queue.put(True)

    def should_stop(self):
        """
        Check is the thread have been asked to stop

        :return:        True if the thread have been canceled
        :rtype:         bool
        """
        return self._should_stop

    def succeed(self):
        """
        Check if the thread have finish correctly.
        Note that a canceled thread is considered as successful if not exception happened

        :return:        True if the thread have succeed
        :rtype:         bool
        """
        return self._succeed

    def get_exception(self):
        """
        Get the thread exception, if any

        :return:        The exception that happened during the thread function, or None
        :rtype:         Exception|None
        """
        return self._exc_info.exception if self._exc_info else None

    def reraise(self):
        """
        Raise in the current (main) thread the exception that happened in this class thread.
        Do nothing if no exception happened.
        """
        if self._exc_info:
            self._exc_info.reraise()

    def wait_for_stop(self):
        self._stop_queue.get(block=True)


class RecurringThread(AbstractThread):
    __metaclass__ = abc.ABCMeta

    @property
    def delay(self):
        """
        Get the loop delay. This method should be overridden in child class

        :return:    The duration of a loop
        :rtype:     datetime.timedelta
        """
        return datetime.timedelta(days=1)

    def run(self, *args, **kargs):
        try:
            next_run = datetime.datetime.utcnow()
            while True:
                self.work(*args, **kargs)

                next_run = next_run + self.delay
                try:
                    to_wait = next_run - datetime.datetime.utcnow()
                    self._stop_queue.get(True, max(1, to_wait.seconds - 1))
                    self._succeed = True
                    return
                except Queue.Empty:
                    pass  # This is normal, it means the main loop didn't ask us to stop
        except error_util.all_errors:
            self._exc_info = error_util.Stack()


class AbstractProc(multiprocessing.Process):
    """
    Simple thread which can be interrupted, with some basic error management
    You should override this class and implement `work` function to use this class
    """

    __metaclass__ = abc.ABCMeta

    IGNORE_SIGNAL_DELAY = datetime.timedelta(milliseconds=100)
    _last_signal_received_per_pid = {}
    _should_stop_per_pid = {}

    def __init__(self, group=None, name=None):
        super(AbstractProc, self).__init__(group=group, name=name)
        error_util.MultiprocessingExceptions.init()
        self.daemon = True
        self._comm_queue = multiprocessing.Queue()
        self._exc_info = None
        self._succeed = False

    def run(self, *args, **kargs):
        try:
            pid = int(self.pid)
            AbstractProc._should_stop_per_pid[pid] = False
            AbstractProc._last_signal_received_per_pid[pid] = datetime.datetime.utcfromtimestamp(0)
            signal.signal(signal.SIGTERM, AbstractProc._raise_keyboard_interrupt)
            signal.signal(signal.SIGINT, AbstractProc._raise_keyboard_interrupt)
            self.work(*args, **kargs)
            self._comm_queue.put(True)
        except error_util.abort_errors:
            self._comm_queue.put(True)
        except error_util.all_errors:
            self._comm_queue.put(error_util.Stack())

    @abc.abstractmethod
    def work(self, *args, **kargs):
        """
        You should override this method. It will be run in the separated thread
        For long task, you should call self.should_stopped() regularly to
        check if you should quit.
        """
        pass

    def stop(self):
        """ Tell the thread to stop """
        pid = int(self.pid)
        try:
            os.kill(pid, signal.SIGINT)
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return  # The process should have stopped

    def should_stop(self):
        pid = int(self.pid)
        return AbstractProc._should_stop_per_pid[pid]

    def succeed(self):
        """
        Check if the thread have finish correctly.
        Note that a canceled thread is considered as successful if not exception happened

        :return:        True if the thread have succeed
        :rtype:         bool
        """
        self._fetch_result()
        return self._succeed

    def get_exception(self):
        """
        Get the thread exception, if any

        :return:        The exception that happened during the thread function, or None
        :rtype:         Exception|None
        """
        self._fetch_result()
        return self._exc_info.exception if self._exc_info else None

    def reraise(self):
        """
        Raise in the current (main) thread the exception that happened in this class thread.
        Do nothing if no exception happened.
        """
        self._fetch_result()
        if self._exc_info:
            self._exc_info.reraise()

    def wait_for_stop(self):
        try:
            while True:
                time.sleep(3600)
        except error_util.abort_errors:
            return

    def _fetch_result(self):
        if self._comm_queue.empty():
            return
        data = self._comm_queue.get()
        while not self._comm_queue.empty():
            data = self._comm_queue.get()
        if isinstance(data, bool):
            self._succeed = True
        else:
            self._exc_info = data

    @staticmethod
    def _raise_keyboard_interrupt(*_):
        """ Callback called when SIGINT or SIGTERM are received """
        pid = int(os.getpid())
        last_signal_received = AbstractProc._last_signal_received_per_pid[pid]
        AbstractProc._should_stop_per_pid[pid] = True
        received = datetime.datetime.utcnow()
        if (received - last_signal_received) > AbstractProc.IGNORE_SIGNAL_DELAY:
            AbstractProc._last_signal_received_per_pid[pid] = received
            raise KeyboardInterrupt()


class RecurringProc(AbstractProc):
    __metaclass__ = abc.ABCMeta

    @property
    def delay(self):
        return datetime.timedelta(days=1)

    def run(self, *args, **kargs):
        try:
            pid = int(self.pid)
            AbstractProc._should_stop_per_pid[pid] = False
            AbstractProc._last_signal_received_per_pid[pid] = datetime.datetime.utcfromtimestamp(0)
            signal.signal(signal.SIGTERM, AbstractProc._raise_keyboard_interrupt)
            signal.signal(signal.SIGINT, AbstractProc._raise_keyboard_interrupt)
            next_run = datetime.datetime.utcnow()
            while True:
                self.work(*args, **kargs)
                next_run = next_run + self.delay
                to_wait = (next_run - datetime.datetime.utcnow())
                time.sleep(to_wait.seconds)
        except error_util.abort_errors:
            self._comm_queue.put(True)
        except error_util.all_errors:
            self._comm_queue.put(error_util.Stack())


def run_proc(target, *args):
    queue = multiprocessing.Queue()

    def _start_proc(*args):
        queue.put(target(*args))

    p = multiprocessing.Process(target=_start_proc, args=args)
    p.start()
    result = queue.get()
    p.join()
    return result
