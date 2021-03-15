# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libraries
import sys
import subprocess
import os
import signal
import time
import multiprocessing
import Queue
import cPickle
try:
    import readline  # For readline input support
except ImportError:
    pass

# Project specific libs
import util
import type_util


def double_fork():
    """
    Do a double fork and kill intermediate parent

    :return:        True on child, False for parent (and raise exception on error)
    :rtype:         Tuple[bool, int, int]
    """
    child_pid_val = multiprocessing.Value('i', 0)
    parent_ready_val = multiprocessing.Value('i', 0)
    parent_pid = os.getpid()
    newpid = os.fork()
    if newpid == 0:  # We are in the first child process
        newpid = os.fork()
        if newpid == 0:
            child_pid_val.value = os.getpid()
            while parent_ready_val.value != 0:
                time.sleep(0.0001)
            return True, parent_pid, os.getpid()
        else:
            os._exit(0)  # Ensure brutal kill of intermediate parent
    else:
        while child_pid_val.value == 0:
            time.sleep(0.0001)
        return False, parent_pid, int(child_pid_val.value)


def double_forked_run(func, *func_args, **func_kwargs):
    """
    Run a command in a sperated double forked process

    :param func:            The function to run
    :type func:             callable
    :param func_args:       The position arguments passed to the called function
    :type func_args:        any
    :param func_kwargs:     The named arguments passed to the called function
    :type func_kwargs:      any
    :return:                The pid of the double-forked function process
    :rtype:                 int
    """
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_forked_call, args=(queue, func, func_args, func_kwargs))
    proc.start()
    try:
        child_pid = queue.get(timeout=1)
    except Queue.Empty:
        raise RuntimeError("Unable to run a double fork cleanly")
    proc.join(timeout=1)
    if proc.is_alive():
        raise RuntimeError("Unable to run a double fork cleanly")
    return int(child_pid)


def shell_quote(arg):
    """
    Quote a parameter for shell usage
    Example:
        shell_quote("c'est cool aujourd'hui, il fait beau") => 'c'"'"'est cool aujourd'"'"'hui, il fait beau'

    :param arg:        String, the argument to quote, required
    :return:        String, the quoted argument
    """
    if sys.version_info[0] >= 3:  # Python 3
        import shlex
        return shlex.quote(arg)
    else:  # Python 2
        import pipes
        return pipes.quote(arg)


def is_process_running(proc):
    """
    Check for the existence of a unix process

    :param proc:        The process to stop, a pid or a subprocess
    :type proc:         subprocess.Popen|int
    :return:            True if the process is still running
    :rtype:             bool
    """
    if hasattr(proc, "is_running"):
        return proc.is_running()
    pid = int(proc) if type_util.ll_int(proc) else proc.pid
    try:
        os.kill(int(pid), 0)
        return not is_zombie(proc)
    except OSError as e:
        if e.errno == 3:  # process is dead
            return False
        else:
            raise


def is_zombie(proc):
    """
    Check a process if it's a zombie (and try to clean it

    :param proc:        The process to stop, a pid or a subprocess
    :type proc:         subprocess.Popen|int
    :return:            True if the process is a zombie
    :rtype:             bool
    """
    pid = int(proc) if type_util.ll_int(proc) else proc.pid
    try:
        dead = os.waitpid(pid, os.WNOHANG)[0]
    except OSError:
        return False
    return bool(dead)


def ensure_stop_proc(proc, timeout=30):
    """
    Ask gracefully a process to stop. If it doesn't we kill it and all it's children (vengeance !!!!)
    If timeout is 0 or None, we wait forever

    :param proc:        The process to stop, a pid or a subprocess
    :type proc:         subprocess.Popen|int
    :param timeout:     The amount of time (in second) we wait before killing the process. Optional, default 30
    :type timeout:      int|float|datetime.timedelta|None
    :return:            True if the process stopped gracefully, False if we had to kill it
    :rtype:             bool
    """
    if type_util.ll_int(proc):
        try:
            os.kill(int(proc), signal.SIGINT)
            os.kill(int(proc), signal.SIGTERM)
        except OSError:
            return True  # The process should have stopped
    else:
        proc.terminate()

    try:
        wait_for_proc(proc, timeout)
        return True
    except OSError:
        return True
    except util.TimeoutError:
        ensure_kill_proc(proc)
        return False


def ensure_kill_proc(proc):
    """
    Kill a processus and all it's children

    :param proc:        The process to stop, a pid or a subprocess
    :type proc:         subprocess.Popen|int
    """
    if type_util.ll_int(proc):
        proc_pid = int(proc)
    else:
        proc_pid = proc.pid
        if proc.poll() is None:
            proc.kill()

    if is_process_running(proc):
        try:
            if hasattr(proc, "is_distant") and proc.is_distant():
                proc.kill()
            else:
                os.killpg(proc_pid, signal.SIGKILL)
        except OSError:
            pass  # The process may stopped between the two calls


def wait_for_proc(proc, timeout):
    """
    Wait for a process to finish with a timeout.
    If timeout is reached before the process stopped, it raise a TimeoutError
    If timeout is 0 or None, we wait forever

    :param proc:        The process we are waiting for, a pid or a subprocess
    :type proc:         subprocess.Popen|int
    :param timeout:     The number of seconds we wait before throwing the exception
    :type timeout:      float|int|datetime.timedelta|None
    """
    with util.using_timeout(timeout):
        if type_util.ll_int(proc):
            try:
                os.waitpid(int(proc), 0)
            except OSError:
                return
        else:
            proc.wait()
    if is_process_running(proc):
        raise util.TimeoutError()


def wait_for_proc_and_streams(proc, timeout):
    """
    Wait for a process to finish with a timeout.
    If timeout is reached before the process stopped, it raise a TimeoutError
    If Timeout is 0 or None, wait forever

    :param proc:        The process we are waiting for
    :type proc:         subprocess.Popen
    :param timeout:     The number of seconds we wait before throwing the exception
    :type timeout:      int|float|datetime.timedelta|None
    :return:            Return code, stdout, and stderr
                        If the return code is greater than 256, it means we can't get the return code
                        If the return code is negative, it's the number of the signal
    :rtype:             Tuple[int, str, str]
    """
    with util.using_timeout(timeout):
        stdout, stderr = proc.communicate()
        return_code = proc.poll()
        if return_code is None:
            proc.wait()
            return_code = proc.poll()
            if return_code is None:
                return_code = 258
        return return_code, stdout, stderr


def run_cmd(cmd, shell=False, cwd=None):
    child_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, shell=shell)
    std_out, std_err = child_proc.communicate()
    if child_proc.poll() is None:
        child_proc.wait()
        if child_proc.poll() is None:
            raise RuntimeError("Unexpected behaviour: process failed without exit code")
    if int(child_proc.returncode) == 0:
        return int(child_proc.returncode), std_out, std_err
    raise RuntimeError("process failed with exit code "+str(child_proc.returncode))


class NamedPipe(object):
    def __init__(self, name, end=0, mode=0666):
        """Open a pair of pipes, name.in and name.out for communication
        with another process.  One process should pass 1 for end, and the
        other 0.  Data is marshalled with pickle."""
        self.inp = None
        self.out = None
        self.in_name, self.out_name = name + '.in', name + '.out',
        try:
            os.mkfifo(self.in_name, mode)
        except OSError:
            pass
        try:
            os.mkfifo(self.out_name, mode)
        except OSError:
            pass

        # NOTE: The order the ends are opened in is important - both ends
        # of pipe 1 must be opened before the second pipe can be opened.
        if end:
            self.inp = open(self.out_name, 'r')
            self.out = open(self.in_name, 'w')
        else:
            self.out = open(self.out_name, 'w')
            self.inp = open(self.in_name, 'r')
        self._open = True

    def is_open(self):
        return not (self.inp is None or self.out is None or self.inp.closed or self.out.closed)

    def put(self, msg):
        if self.is_open():
            data = cPickle.dumps(msg, 1)
            self.out.write("%d\n" % len(data))
            self.out.write(data)
            self.out.flush()
        else:
            raise Exception("Pipe closed")

    def get(self):
        txt = self.inp.readline()
        if not txt:
            self.inp.close()
        else:
            length = int(txt)
            data = self.inp.read(length)
            if len(data) < length:
                self.inp.close()
            return cPickle.loads(data)  # Convert back to python object.

    def close(self):
        if self.inp is not None:
            self.inp.close()
        if self.out is not None:
            self.out.close()
        try:
            os.remove(self.in_name)
        except OSError:
            pass
        try:
            os.remove(self.out_name)
        except OSError:
            pass

    def __del__(self):
        self.close()


def _forked_call(queue, func, func_args, func_kwargs):
    in_child, parent_pid, child_pid = double_fork()
    if not in_child:
        queue.put(child_pid)
        return child_pid
    func(*func_args, **func_kwargs)
    sys.exit(0)
