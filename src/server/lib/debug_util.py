# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
Provide some utilities for debugging a running process
"""

# Python core libraries
import sys
import os
import traceback
import signal
import codeop
import cStringIO
import tempfile

try:
    import readline  # For readline input support
except ImportError:
    pass

# Project specific libs
import proc_util


def pipename(pid):
    """Return name of pipe to use"""
    return os.path.join(tempfile.gettempdir(), 'debug-%d' % pid)


def remote_debug(sig, frame):
    """Handler to allow process to be remotely debugged."""

    def _raiseEx(ex):
        """Raise specified exception in the remote process"""
        _raiseEx.ex = ex

    _raiseEx.ex = None

    try:
        # Provide some useful functions.
        locs = {'_raiseEx': _raiseEx}
        locs.update(frame.f_locals)  # Unless shadowed.
        globs = frame.f_globals

        pid = os.getpid()  # Use pipe name based on pid
        pipe = proc_util.NamedPipe(pipename(pid))

        old_stdout, old_stderr = sys.stdout, sys.stderr
        txt = ''
        pipe.put("Interrupting process at following point:\n" +
                 ''.join(traceback.format_stack(frame)) + ">>> ")

        try:
            while pipe.is_open() and _raiseEx.ex is None:
                line = pipe.get()
                if line is None: continue  # EOF
                txt += line
                try:
                    code = codeop.compile_command(txt)
                    if code:
                        sys.stdout = cStringIO.StringIO()
                        sys.stderr = sys.stdout
                        exec code in globs, locs
                        txt = ''
                        pipe.put(sys.stdout.getvalue() + '>>> ')
                    else:
                        pipe.put('... ')
                except StandardError:
                    txt = ''  # May be syntax err.
                    sys.stdout = cStringIO.StringIO()
                    sys.stderr = sys.stdout
                    traceback.print_exc()
                    pipe.put(sys.stdout.getvalue() + '>>> ')
        finally:
            sys.stdout = old_stdout  # Restore redirected output.
            sys.stderr = old_stderr
            pipe.close()
    except StandardError:  # Don't allow debug exceptions to propogate to real program.
        traceback.print_exc()

    if _raiseEx.ex is not None:
        raise _raiseEx.ex


def debug_process(pid, signal_type=signal.SIGUSR2):
    """Interrupt a running process and debug it."""
    os.kill(pid, signal_type)  # Signal process.
    pipe = proc_util.NamedPipe(pipename(pid), 1)
    try:
        while pipe.is_open():
            txt = raw_input(pipe.get()) + '\n'
            pipe.put(txt)
    except EOFError:
        pass  # Exit.
    pipe.close()


def register_for_debug(signal_type=signal.SIGUSR2):
    signal.signal(signal_type, remote_debug)  # Register for remote debugging.
