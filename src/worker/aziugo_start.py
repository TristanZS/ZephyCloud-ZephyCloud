#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This file run a command on the worker.
It need several things to work:

- A file called task_params.json in the input folder (/home/aziugo/worker_scripts/inputs)
  This file should contains several keys:
   - 'command': The command to run
   - 'cwd': The working directory. Optional, default  /home/aziugo/worker_scripts/toolchain
   - 'env': An key-value dictionary to add values in the environment

- A file called /home/aziugo/worker_scripts/inputs/start_task
  The configured task will start as soon as this file is created

The task will run, and then a file called /home/aziugo/worker_scripts/outputs/finished will be created
The script finished when the file /home/aziugo/worker_scripts/inputs/output_flushed is
created by the corker controller

Everything should be logged both on /home/aziugo/worker_scripts/outputs/worker.log and stdout

"""

# Python core libs
import sys
import os
import logging
import time
import datetime
import json
import subprocess
import shutil
import threading
import platform
import contextlib
import tempfile

# Project specific files
import toolchain.zc_files
import toolchain.zc_variables


try:
    import codecs
except ImportError:
    codecs = None

try:
    unicode
    _unicode = True
except NameError:
    _unicode = False


TASK_FOLDER = os.path.abspath(os.path.dirname(__file__))
WORK_DIR = "/home/aziugo/worker_scripts/workdir"
DOCKER_LOG_FILE = "/home/aziugo/docker_stdout.log"
log = logging.getLogger("aziugo")


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

class LogPipe(threading.Thread):
    """
    A Pipe like object. Every stream writen to this file will be logged line by line

    Usage:
        out_pipe = LogPipe(logging.INFO)
        try:
            subprocess.check_call(cmd, stdout=out_pipe)
        finally:
            out_pipe.close()
    """

    def __init__(self, level, logger=None):
        """
        :param level:       The log level of the message sent to this pipe. Ex: logging.INFO
        :type level:        int
        :param logger:      A logger instance. If not provided, log into root logger. Optional, default None
        :type logger:       logging.Logger|None
        """
        threading.Thread.__init__(self)
        self.daemon = False
        self.level = level
        self.fdRead, self.fdWrite = os.pipe()
        self.pipeReader = os.fdopen(self.fdRead)
        self.process = None
        self.logger = logger if logger is not None else logging.getLogger()
        self.start()

    def fileno(self):
        """
        Return the write file descriptor of the pipe

        :return:    The write file descriptor of the pipe
        :rtype:     int
        """
        return self.fdWrite

    def run(self):
        """ Main thread loop. Log every received data line by line """
        for line in iter(self.pipeReader.readline, ''):
            self.logger.log(self.level, line.strip('\n'))

        remaining = self.pipeReader.read().strip()
        if remaining:
            self.logger.log(self.level, remaining)
        self.pipeReader.close()

    def close(self):
        """ Close the write end of the pipe. """
        os.close(self.fdWrite)

    def stop(self):
        """ Stop the logging """
        self.close()

    def __del__(self):
        try:
            self.stop()
        except:  # Ignore errors, we are in the destructor
            pass
        try:
            del self.fdRead
        except:  # Ignore errors, we are in the destructor
            pass
        try:
            del self.fdWrite
        except:  # Ignore errors, we are in the destructor
            pass


class CircularList(object):
    def __init__(self, size):
        """Initialization"""
        self.index = 0
        self.size = size
        self._data = []

    def append(self, value):
        """Append an element"""
        if len(self._data) == self.size:
            self._data[self.index] = value
        else:
            self._data.append(value)
        self.index = (self.index + 1) % self.size

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        """Get element by index, relative to the current index"""
        if len(self._data) == self.size:
            return self._data[(key + self.index) % self.size]
        else:
            return self._data[key]

    def __repr__(self):
        """Return string representation"""
        return self._data.__repr__() + ' (' + str(len(self._data))+' items)'

    def __iter__(self):
        size = len(self._data)
        for i in range(self.index, size):
            yield self._data[i]
        for i in range(0, self.index):
            yield self._data[i]


class SmallFileHandler(logging.Handler):
    """
    A handler class which writes formatted logging records to disk files.
    """
    def __init__(self, filename, limit, encoding=None):
        """
        Open the specified file and use it as the stream for logging.
        """
        super(SmallFileHandler, self).__init__()
        if codecs is None:
            encoding = None
        limit = int(limit)
        self._baseFilename = os.path.abspath(filename)
        self._encoding = encoding
        self._limit = limit
        self._fh = None
        self._buffer = CircularList(limit-1)
        self._line_count = 0
        self._pos_begin = 0

    def flush(self):
        """
        Flushes the stream.
        """
        self.acquire()
        try:
            if self._fh and hasattr(self._fh, "flush"):
                self._fh.flush()
        except Exception as e:
            print(str(e))
        finally:
            self.release()

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            stream = self._get_fh()
            fs = "%s\n"
            if not _unicode:  # if no unicode support...
                self._write_msg(fs % msg)
            else:
                try:
                    if isinstance(msg, unicode) and getattr(stream, 'encoding', None):
                        ufs = u'%s\n'
                        try:
                            self._write_msg(ufs % msg)
                        except UnicodeEncodeError as e:
                            # Printing to terminals sometimes fails. For example,
                            # with an encoding of 'cp1251', the above write will
                            # work if written to a stream opened or wrapped by
                            # the codecs module, but fail when writing to a
                            # terminal even when the codepage is set to cp1251.
                            # An extra encoding step seems to be needed.
                            print(str(e))
                            self._write_msg((ufs % msg).encode(stream.encoding))
                    else:
                        self._write_msg(fs % msg)
                except UnicodeError as e:
                    print(str(e))
                    self._write_msg(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print(str(e))
        except:
            self.handleError(record)

    def close(self):
        """
        Closes the stream.
        """
        self.acquire()
        try:
            try:
                try:
                    self.flush()
                except Exception as e:
                    print(str(e))
                finally:
                    if self._fh:
                        fh = self._fh
                        self._fh = None
                        if hasattr(fh, "close"):
                            fh.close()
            except Exception as e: print(str(e))
            finally:
                # Issue #19523: call unconditionally to prevent a handler leak when delay is set
                super(SmallFileHandler, self).close()
        except Exception as e:
            print(str(e))
        finally:
            self.release()

    def _get_fh(self):
        """
        Open the current base file with the (original) mode and encoding.
        Return the resulting stream.
        """
        if not self._fh:
            if self._encoding is None:
                self._fh = open(self._baseFilename, "w")
            else:
                self._fh = codecs.open(self._baseFilename, "w", self._encoding)
        return self._fh

    def _write_msg(self, msg):
        stream = self._get_fh()
        if self._line_count == self._limit:
            self._pos_begin = stream.tell()
        elif self._line_count == self._limit * 3:
            stream.seek(self._pos_begin)
            stream.write("[truncated job log... ]\n")
            self._pos_begin = stream.tell()
            for line in self._buffer:
                stream.write(line)
            stream.truncate()
        if self._line_count > self._limit * 3 and self._line_count % self._limit == 0:
            stream.seek(self._pos_begin)
            for line in self._buffer:
                stream.write(line)
            stream.truncate()
        stream.write(msg)
        self._line_count += 1
        if self._line_count > self._limit*2:
            self._buffer.append(msg)


class AbortError(RuntimeError):
    """ Those error are somehow excepted. We wil not show those stacktrace """
    pass


def init_logging():
    """ Initialise logging to output everything into stdout and a file in /home/aziugo/worker_scripts/outputs """
    # Initialise logging
    if "LOG_LEVEL" in os.environ and os.environ["LOG_LEVEL"] and os.environ["LOG_LEVEL"].strip():
        log_level = os.environ["LOG_LEVEL"].strip().upper()
    else:
        log_level = "DEBUG"
    log_level_int = logging.getLevelName(log_level)
    if not isinstance(log_level_int, (int, long)):
        log_level_int = logging.INFO
    logging.getLogger().setLevel(logging.INFO if log_level_int < logging.INFO else log_level_int)
    log.setLevel(log_level_int)
    log.propagate = False

    input_folder = os.path.join(TASK_FOLDER, "inputs")

    jobid = None
    log_info_file = os.path.join(input_folder, "log_info.json")
    if os.path.exists(log_info_file):
        try:
            with open(log_info_file, "r") as fh:
                log_info = json.load(fh)
            jobid = log_info['jobid']
        except StandardError as e:
            print("Error reading the log info file: "+str(e))

    if jobid:
        log.name = "Job "+str(jobid).rjust(6)

    small_file_handle = SmallFileHandler(os.path.join(TASK_FOLDER, "outputs", "worker.log"), 300)
    small_file_handle.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-7s: %(name)s - %(message)s'))
    logging.getLogger().addHandler(small_file_handle)
    log.addHandler(small_file_handle)

    file_handler = logging.FileHandler(os.path.join(TASK_FOLDER, "outputs", "worker_full.log"))
    file_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-7s: %(name)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    log.addHandler(file_handler)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logging.getLogger().addHandler(console_handler)
    log.addHandler(console_handler)

    if os.path.exists(DOCKER_LOG_FILE):
        docker_file_handler = logging.FileHandler(DOCKER_LOG_FILE)
        docker_file_handler.setFormatter(logging.Formatter('[ %(name)s ] - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(docker_file_handler)
        log.addHandler(docker_file_handler)


def wait_for_file(file_path, timeout=0):
    """
    Wait for a file to exists before exiting

    :param file_path:   The file path we will wait for
    :type file_path:    str
    :param timeout:     Number of seconds before aborting. None or 0 means not timeout. Optional, default 0
    :type timeout:      int|float|datetime.timedelta|None
    :return:            True when the data are here, False if timeout happened
    :rtype:             bool
    """

    if timeout is None or (ll_float(timeout) and float(timeout) <= 0):
        time_limit = None
    else:
        if not isinstance(timeout, datetime.timedelta):
            timeout = datetime.timedelta(milliseconds=int(float(timeout)*1000))
        time_limit = datetime.datetime.utcnow() + timeout

    while not os.path.exists(file_path):
        if time_limit is not None and datetime.datetime.utcnow() > time_limit:
            return False
        time.sleep(0.1)
    return True


@contextlib.contextmanager
def temp_folder(parent_folder=None):
    """
    Create a temporary folder, yield it and then remove it

    :param parent_folder:   The place where we will create the temporary folder. Optional, default None
    :type parent_folder:    str|None
    :return:                The created temporary folder path
    :rtype:                 str
    """
    if parent_folder and not os.path.exists(parent_folder):
        os.makedirs(parent_folder)
    output_path = tempfile.mkdtemp(dir=parent_folder)
    try:
        yield output_path
    finally:
        shutil.rmtree(output_path)


def which(exec_name):
    """
    Get path of an executable
    Raise error if not found

    :param exec_name:       The binary name
    :type exec_name:        str
    :return:                The path to the executable file
    :rtype:                 str
    """
    path = os.getenv('PATH')
    available_exts = ['']
    if platform.system() == "Windows":
        additional_exts = [ext.strip() for ext in os.getenv('PATHEXT').split(";")]
        available_exts += ["."+ext if ext[0] != "." else ext for ext in additional_exts]
    for folder in path.split(os.path.pathsep):
        for ext in available_exts:
            exec_path = os.path.join(folder, exec_name+ext)
            if os.path.exists(exec_path) and os.access(exec_path, os.X_OK):
                return exec_path
    raise RuntimeError("Unable to find path for executable "+str(exec_name))


def get_main_folder_of(target):
    """
    Get the folder inside target directory if it's not hidden and is the only one

    :param target:  The folder to look inside
    :type target:   str
    :return:        The only non-hidden folder inside target
    :rtype:         str
    """
    main_folder_name = None
    for filename in os.listdir(target):
        if os.path.isdir(os.path.join(target, filename)):
            if not filename or filename.startswith("."):
                continue
            if not main_folder_name:
                main_folder_name = filename
            else:
                raise RuntimeError("More than one main folder in " + str(target))
    if not main_folder_name:
        raise RuntimeError("No folder found in folder " + str(target))
    return os.path.abspath(os.path.join(target, main_folder_name))


def merge_folders(root_src_dir, root_dst_dir):
    """
    Copy directory tree. Overwrites also read only files.
    :param root_src_dir: source directory
    :param root_dst_dir:  destination directory
    """
    for src_dir, dirs, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                os.remove(dst_file)

            shutil.copy(src_file, dst_dir)


def is_docker():
    path = "/proc/" + str(os.getpid()) + "/cgroup"
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        return "docker" in f.read()


def is_systemd():
    return subprocess.call("pidof systemd > /dev/null 2>&1", shell=True) == 0


def shutdown():
    if is_docker:
        os.system("sudo kill -KILL -1")
    elif is_systemd():
        os.system("sudo systemctl poweroff")
    else:  # Old sysV:
        os.system("sudo shutdown -h now")


def run_task():
    """ Look for run parameters and run the task accordingly """
    input_folder = os.path.join(TASK_FOLDER, "inputs")
    task_params_file = os.path.join(input_folder, "task_params.json")
    if not os.path.exists(task_params_file):
        raise AbortError("Unable to load task file "+task_params_file)

    with open(task_params_file, "r") as fh:
        task_params = json.load(fh)
    if "project_uid" not in task_params.keys():
        raise AbortError("No project uid in task file " + task_params_file)
    if "jobid" not in task_params.keys():
        raise AbortError("No job id in task file " + task_params_file)
    jobid = int(task_params["jobid"])
    project_uid = str(task_params["project_uid"])

    new_env = os.environ.copy()
    new_env["CLOUD_WORKER"] = "1"
    if "env" in task_params.keys():
        for key in task_params["env"].keys():
            new_env[key] = str(task_params["env"][key])

    cwd = os.path.join(TASK_FOLDER, "ZephyTOOLS")
    if "working_dir" in task_params.keys():
        cwd = str(task_params["working_dir"])

    params = []
    if "params" in task_params.keys():
        params = json.loads(task_params["params"])

    if "command" in task_params.keys():
        cmd = task_params["command"]
        if params:
            cmd = [cmd]+params
        out_pipe = LogPipe(logging.INFO, log)
        err_pipe = LogPipe(logging.WARNING, log)
        try:
            subprocess.check_call(cmd, cwd=cwd, env=new_env, stdout=out_pipe, stderr=err_pipe)
        finally:
            out_pipe.close()
            err_pipe.close()
    elif "toolchain" in task_params.keys():
        if task_params["toolchain"] == "anal":
            run_anal_toolchain(jobid, project_uid, new_env)
        elif task_params["toolchain"] == "mesh":
            run_mesh_toolchain(jobid, project_uid, new_env)
        elif task_params["toolchain"] == "calc":
            run_calc_toolchain(jobid, project_uid, new_env, params[0])
        elif task_params["toolchain"] == "restart_calc":
            run_recalc_toolchain(jobid, project_uid, new_env, params[0], params[1])
        else:
            raise AbortError("Unknown toolchain "+repr(task_params["toolchain"])+" in task file "+task_params_file)
    else:
        raise AbortError("No 'command' nor 'toolchain' defined in task file "+task_params_file)


def run_anal_toolchain(jobid, project_uid, env):
    """
    Run the analyse toolchain

    :param jobid:           The id of the job
    :type jobid:            int
    :param project_uid:     The project codename
    :type project_uid:      str
    :param env:             The environment variables to pass to the toolchain
    :type env:              dict[str, str]
    """

    input_folder = os.path.join(TASK_FOLDER, "inputs")
    output_folder = os.path.join(TASK_FOLDER, "outputs")
    toolchain_folder = os.path.join(TASK_FOLDER, "toolchain")

    for item in os.listdir(toolchain_folder):
        if os.path.isdir(os.path.join(toolchain_folder, item)):
            shutil.copytree(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))
        else:
            shutil.copy(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))

    shutil.move(os.path.join(input_folder, "project_file.zip"),
                os.path.join(WORK_DIR, project_uid + ".zip"))
    os.chdir(WORK_DIR)

    chain = "anal"
    toolchain_file = toolchain.zc_variables.ddprog[chain]
    result_file = 'ok_' + toolchain_file.split('.')[0]

    out_pipe = LogPipe(logging.INFO, log)
    err_pipe = LogPipe(logging.WARNING, log)
    try:
        toolchain.zc_files.InitFiles(0, project_uid, "anal", project_uid, log)
        exec_file = os.path.join(WORK_DIR, 'ZephyTOOLS', 'APPLI', 'TMP', toolchain_file)

        log.info("Starting toolchain")
        exit_code = subprocess.call(['python', exec_file], cwd=WORK_DIR, env=env, stdout=out_pipe, stderr=err_pipe)

        log.info("Toolchain finished with exit code " + repr(exit_code))
        toolchain_succeed = os.path.isfile(os.path.join(WORK_DIR, result_file))

        if not toolchain_succeed:
            raise AbortError("Job failed: no " + str(result_file) + " file generated")
        log.info("Packaging results")
        toolchain.zc_files.StoreFiles(project_uid, chain, str(jobid),
                                      call_args={"stdout": out_pipe, "stderr": err_pipe})
    finally:
        out_pipe.close()
        err_pipe.close()

    out_filename = '%s-%s-%s' % (project_uid, chain, str(jobid))
    shutil.move(os.path.join(WORK_DIR, out_filename + ".zip"), os.path.join(output_folder, out_filename + ".zip"))
    log.info("Results are ready to fetch")


def run_mesh_toolchain(jobid, project_uid, env):
    """
    Run the mesh generation toolchain

    :param jobid:           The id of the job
    :type jobid:            int
    :param project_uid:     The project codename
    :type project_uid:      str
    :param env:             The environment variables to pass to the toolchain
    :type env:              dict[str, str]
    """

    input_folder = os.path.join(TASK_FOLDER, "inputs")
    output_folder = os.path.join(TASK_FOLDER, "outputs")
    toolchain_folder = os.path.join(TASK_FOLDER, "toolchain")

    for item in os.listdir(toolchain_folder):
        if os.path.isdir(os.path.join(toolchain_folder, item)):
            shutil.copytree(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))
        else:
            shutil.copy(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))
    gmsh_dest = os.path.join(WORK_DIR, "ZephyTOOLS", "APPLI", "TMP", "CFD_MESH_01.py_g")
    gmsh_src = which("gmsh")
    if os.path.exists(gmsh_dest):
        os.remove(gmsh_dest)
    shutil.copy(gmsh_src, gmsh_dest)
    shutil.move(os.path.join(input_folder, "project_file.zip"), os.path.join(WORK_DIR, "project_file.zip"))
    shutil.move(os.path.join(input_folder, "anal.zip"), os.path.join(WORK_DIR, "anal.zip"))
    shutil.move(os.path.join(input_folder, "mesh_params.zip"), os.path.join(WORK_DIR, "mesh_params.zip"))
    os.chdir(WORK_DIR)

    chain = "mesh"
    toolchain_file = toolchain.zc_variables.ddprog[chain]
    result_file = 'ok_' + toolchain_file.split('.')[0]

    out_pipe = LogPipe(logging.INFO, log)
    err_pipe = LogPipe(logging.WARNING, log)
    try:
        toolchain.zc_files.InitFiles(0, "project_file", "mesh", project_uid, log)
        toolchain.zc_files.InitFiles(1, "anal", "mesh", project_uid, log)
        toolchain.zc_files.InitFiles(2, "mesh_params", "mesh", project_uid, log)
        exec_file = os.path.join(WORK_DIR, 'ZephyTOOLS', 'APPLI', 'TMP', toolchain_file)

        log.info("Starting toolchain")
        exit_code = subprocess.call(['python', exec_file], cwd=WORK_DIR, env=env, stdout=out_pipe, stderr=err_pipe)

        log.info("Toolchain finished with exit code " + repr(exit_code))
        toolchain_succeed = os.path.isfile(os.path.join(WORK_DIR, result_file))

        if not toolchain_succeed:
            raise AbortError("Job failed: no " + str(result_file) + " file generated")
        log.info("Packaging results")
        toolchain.zc_files.StoreFiles(project_uid, chain, str(jobid),
                                      call_args={"stdout": out_pipe, "stderr": err_pipe})
    finally:
        out_pipe.close()
        err_pipe.close()

    # Save the preview file
    with temp_folder() as folder:
        outfolder = os.path.join(folder, '%s-%s-%s' % (project_uid, chain, str(jobid)))
        os.makedirs(outfolder)
        mesh_workdir = os.path.join(WORK_DIR, "ZephyTOOLS", 'PROJECTS_CFD', project_uid, "MESH")
        main_folder_name = None
        for filename in os.listdir(mesh_workdir):
            if os.path.isdir(os.path.join(mesh_workdir, filename)):
                if not filename or filename.startswith("."):
                    continue
                if not main_folder_name:
                    main_folder_name = filename
                else:
                    raise RuntimeError("To many folders in folder " + str(mesh_workdir))
        if not main_folder_name:
            raise RuntimeError("No main folder found in zip file " + str(mesh_workdir))
        mesh_workdir = os.path.join(mesh_workdir, main_folder_name)
        shutil.copytree(os.path.join(mesh_workdir, "FILES"), os.path.join(outfolder, "FILES"))
        shutil.copy(os.path.join(mesh_workdir, "param.xml"), os.path.join(outfolder, "param.xml"))
        toolchain.zc_files.ZipDir(outfolder, os.path.join(output_folder, "preview.zip"))

    out_filename = '%s-%s-%s' % (project_uid, chain, str(jobid))
    shutil.move(os.path.join(WORK_DIR, out_filename + ".zip"), os.path.join(output_folder, out_filename + ".zip"))
    log.info("Results are ready to fetch")


def store_calc_files(codename, jobid, split_results, call_args=None):
    ch = "calc"
    ztfold = os.path.abspath('ZephyTOOLS').rstrip("/")+"/"

    if not call_args:
        call_args = {}
    outfolder = '%s-%s-%s' % (codename, ch, jobid)
    subprocess.call(['mkdir', '-p', outfolder], **call_args)
    for elem in toolchain.zc_files.ddout[ch]['tree']:
        subprocess.call(['mkdir', '-p', outfolder+elem], **call_args)
    for elem in toolchain.zc_files.ddout[ch]['folders']:
        subprocess.call(['cp', '-r', ztfold+'PROJECTS_CFD/'+codename+elem, outfolder], **call_args)
    for elem in toolchain.zc_files.ddout[ch]['files']:
        subprocess.call(['cp', '-r', ztfold+'PROJECTS_CFD/'+codename+'/'+elem, outfolder], **call_args)
    for elem in toolchain.zc_files.ddout[ch]['remove']:
        subprocess.call(['rm', '-f', outfolder+elem], **call_args)
    res_folder = get_main_folder_of(os.path.join(outfolder, "CALC"))
    comp_folder = os.path.basename(res_folder)

    if split_results:
        with temp_folder() as reduce_tmp_folder:
            reduce_folder = os.path.join(reduce_tmp_folder, outfolder, "CALC", comp_folder)
            os.makedirs(reduce_folder)
            subprocess.call(['mv', os.path.join(res_folder, "REDUCED"),
                             os.path.join(reduce_folder, "REDUCED")], **call_args)
            os.chdir(reduce_tmp_folder)
            toolchain.zc_files.ZipDir('./%s' % outfolder, 'reduced.zip')
            shutil.move(os.path.join(reduce_tmp_folder, 'reduced.zip'), os.path.join(WORK_DIR, 'reduced.zip'))
        with temp_folder() as iterations_tmp_folder:
            iterations_folder = os.path.join(iterations_tmp_folder, outfolder, "CALC", comp_folder)
            for calc_type in ("COARSE", "FINE"):
                if not os.path.exists(os.path.join(res_folder, calc_type)):
                    continue
                os.makedirs(os.path.join(iterations_folder, calc_type))
                targets=["constant", "system"]
                for o in os.listdir(os.path.join(res_folder, calc_type)):
                    if not os.path.isdir(os.path.join(res_folder, calc_type, o)): continue
                    try:
                        int(o)
                        targets.append(o)
                    except ValueError:
                        continue
                for target in targets:
                    to_move = os.path.join(res_folder, calc_type, target)
                    if not os.path.exists(os.path.join(to_move)):
                        continue
                    try:
                        dest = os.path.join(iterations_folder, calc_type, target)
                        subprocess.call(['mv', to_move, dest], **call_args)
                    except StandardError as e:
                        log.warning(str(e))
            os.chdir(iterations_tmp_folder)
            toolchain.zc_files.ZipDir('./%s' % outfolder, 'iterations.zip')
            shutil.move(os.path.join(iterations_tmp_folder, 'iterations.zip'), os.path.join(WORK_DIR, 'iterations.zip'))
    os.chdir(WORK_DIR)
    toolchain.zc_files.ZipDir('./%s' % outfolder, "results.zip")


def run_calc_toolchain(jobid, project_uid, env, split_results):
    """
    Run the cfd calculation toolchain

    :param jobid:           The id of the job
    :type jobid:            int
    :param project_uid:     The project codename
    :type project_uid:      str
    :param env:             The environment variables to pass to the toolchain
    :type env:              dict[str, str]
    :param split_results:   Do we want  to split results ?
    :type split_results:    bool
    """

    input_folder = os.path.join(TASK_FOLDER, "inputs")
    output_folder = os.path.join(TASK_FOLDER, "outputs")
    toolchain_folder = os.path.join(TASK_FOLDER, "toolchain")

    for item in os.listdir(toolchain_folder):
        if os.path.isdir(os.path.join(toolchain_folder, item)):
            shutil.copytree(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))
        else:
            shutil.copy(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))

    shutil.move(os.path.join(input_folder, "project_file.zip"), os.path.join(WORK_DIR, "project_file.zip"))
    shutil.move(os.path.join(input_folder, "anal.zip"), os.path.join(WORK_DIR, "anal.zip"))
    shutil.move(os.path.join(input_folder, "mesh.zip"), os.path.join(WORK_DIR, "mesh.zip"))
    shutil.move(os.path.join(input_folder, "calc_params.zip"), os.path.join(WORK_DIR, "calc_params.zip"))
    os.chdir(WORK_DIR)

    chain = "calc"
    toolchain_file = toolchain.zc_variables.ddprog[chain]
    result_file = 'ok_' + toolchain_file.split('.')[0]

    out_pipe = LogPipe(logging.INFO, log)
    err_pipe = LogPipe(logging.WARNING, log)
    try:
        toolchain.zc_files.InitFiles(0, "project_file", "calc", project_uid, log)
        toolchain.zc_files.InitFiles(1, "anal", "calc", project_uid, log)
        toolchain.zc_files.InitFiles(2, "mesh", "calc", project_uid, log)
        toolchain.zc_files.InitFiles(3, "calc_params", "calc", project_uid, log)
        exec_file = os.path.join(WORK_DIR, 'ZephyTOOLS', 'APPLI', 'TMP', toolchain_file)

        log.info("Starting toolchain")
        exit_code = subprocess.call(['python', exec_file], cwd=WORK_DIR, env=env, stdout=out_pipe, stderr=err_pipe)

        log.info("Toolchain finished with exit code " + repr(exit_code))
        toolchain_succeed = os.path.isfile(os.path.join(WORK_DIR, result_file))

        if not toolchain_succeed:
            raise AbortError("Job failed: no " + str(result_file) + " file generated")
        log.info("Packaging results")
        store_calc_files(project_uid, str(jobid), split_results, call_args={"stdout": out_pipe, "stderr": err_pipe})
        with temp_folder() as tmp_folder:
            out_folder = '%s-%s-%s' % (project_uid, chain, str(jobid))
            out_path = os.path.join(tmp_folder, out_folder)
            os.makedirs(out_path)
            work_files = os.path.join('ZephyTOOLS', 'PROJECTS_CFD', project_uid)
            shutil.copytree(work_files, os.path.join(out_path, project_uid))
            toolchain.zc_files.ZipDir(out_path, "workfiles.zip")
    finally:
        out_pipe.close()
        err_pipe.close()

    out_filename = '%s-%s-%s' % (project_uid, chain, str(jobid))
    shutil.move(os.path.join(WORK_DIR, "results.zip"), os.path.join(output_folder, out_filename + ".zip"))
    shutil.move(os.path.join(WORK_DIR, "workfiles.zip"), os.path.join(output_folder, out_filename + "_workfiles.zip"))
    if split_results:
        shutil.move(os.path.join(WORK_DIR, "iterations.zip"), os.path.join(output_folder, out_filename + "_iterations.zip"))
        shutil.move(os.path.join(WORK_DIR, "reduced.zip"), os.path.join(output_folder, out_filename + "_reduce.zip"))
    log.info("Results are ready to fetch")


def run_recalc_toolchain(jobid, project_uid, env, nbr_iterations, split_results):
    """
    Run the cfd calculation toolchain once again

    :param jobid:           The id of the job
    :type jobid:            int
    :param project_uid:     The project codename
    :type project_uid:      str
    :param env:             The environment variables to pass to the toolchain
    :type env:              dict[str, str]
    :param nbr_iterations:  How much CFD computation iteration do we ned to run ?
    :type nbr_iterations:   int
    :param split_results:   Do we want  to split results ?
    :type split_results:    bool
    """

    input_folder = os.path.join(TASK_FOLDER, "inputs")
    output_folder = os.path.join(TASK_FOLDER, "outputs")
    toolchain_folder = os.path.join(TASK_FOLDER, "toolchain")

    for item in os.listdir(toolchain_folder):
        if os.path.isdir(os.path.join(toolchain_folder, item)):
            shutil.copytree(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))
        else:
            shutil.copy(os.path.join(toolchain_folder, item), os.path.join(WORK_DIR, item))
    os.chdir(WORK_DIR)

    chain = "calc"
    restart_file = "CFD_CALC_RESTART.py"
    toolchain_file = toolchain.zc_variables.ddprog[chain]
    result_file = 'ok_' + toolchain_file.split('.')[0]

    out_pipe = LogPipe(logging.INFO, log)
    err_pipe = LogPipe(logging.WARNING, log)
    try:
        log.info("Extract files")
        project_path = os.path.join('ZephyTOOLS', 'PROJECTS_CFD', project_uid)

        log.info("Extracting file " + os.path.join(input_folder, "internal.zip"))
        with temp_folder() as tmp_folder:
            toolchain.zc_files.Extract(os.path.join(input_folder, "internal.zip"), tmp_folder)
            main_folder = get_main_folder_of(get_main_folder_of(tmp_folder))
            merge_folders(main_folder, project_path)
        log.info("Extracting file " + os.path.join(input_folder, "calc_params.zip"))
        with temp_folder() as tmp_folder:
            toolchain.zc_files.Extract(os.path.join(input_folder, "calc_params.zip"), tmp_folder)
            main_folder = get_main_folder_of(tmp_folder)
            shutil.copy(os.path.join(main_folder, "APPLI", "TMP", "CFD_CALC_01.py.xml"),
                        os.path.join(WORK_DIR, "ZephyTOOLS", "APPLI", "TMP", "CFD_CALC_01.py.xml"))
        calc_folder = get_main_folder_of(os.path.join(project_path, "CALC"))

        log.info("Starting restart script")
        exec_file = os.path.join(WORK_DIR, 'ZephyTOOLS', 'APPLI', 'TMP', restart_file)
        exit_code = subprocess.call(['python', exec_file, calc_folder, str(nbr_iterations)],
                                    cwd=WORK_DIR, env=env, stdout=out_pipe, stderr=err_pipe)
        log.info("Restart script finished with exit code " + repr(exit_code))

        log.info("Starting toolchain")
        exec_file = os.path.join(WORK_DIR, 'ZephyTOOLS', 'APPLI', 'TMP', toolchain_file)
        exit_code = subprocess.call(['python', exec_file],
                                    cwd=WORK_DIR, env=env, stdout=out_pipe, stderr=err_pipe)

        log.info("Toolchain finished with exit code " + repr(exit_code))
        toolchain_succeed = os.path.isfile(os.path.join(WORK_DIR, result_file))

        if not toolchain_succeed:
            raise AbortError("Job failed: no " + str(result_file) + " file generated")
        log.info("Packaging results")
        store_calc_files(project_uid, str(jobid), split_results, call_args={"stdout": out_pipe, "stderr": err_pipe})
        with temp_folder() as tmp_folder:
            out_folder = '%s-%s-%s' % (project_uid, chain, str(jobid))
            out_path = os.path.join(tmp_folder, out_folder)
            os.makedirs(out_path)
            work_files = os.path.join('ZephyTOOLS', 'PROJECTS_CFD', project_uid)
            shutil.copytree(work_files, os.path.join(out_path, project_uid))
            toolchain.zc_files.ZipDir(out_path, "workfiles.zip")
    finally:
        out_pipe.close()
        err_pipe.close()

    out_filename = '%s-%s-%s' % (project_uid, chain, str(jobid))
    shutil.move(os.path.join(WORK_DIR, "results.zip"), os.path.join(output_folder, out_filename + ".zip"))
    shutil.move(os.path.join(WORK_DIR, "workfiles.zip"), os.path.join(output_folder, out_filename + "_workfiles.zip"))
    if split_results:
        shutil.move(os.path.join(WORK_DIR, "iterations.zip"), os.path.join(output_folder, out_filename + "_iterations.zip"))
        shutil.move(os.path.join(WORK_DIR, "reduced.zip"), os.path.join(output_folder, out_filename + "_reduce.zip"))
    log.info("Results are ready to fetch")


def save_state(status):
    output_folder = os.path.join(TASK_FOLDER, "outputs")
    for i in range(3):
        try:
            with open(os.path.join(output_folder, "task_end.txt"), "wt") as fh:
                fh.write(str(status)+"\n")
            return
        except OSError as e:
            if i > 0:
                log.warning(str(e))
    log.error("Unable to save status")


def should_shutdown(input_folder, default=True):
    task_params_file = os.path.join(input_folder, "task_params.json")
    if not os.path.exists(task_params_file):
        raise AbortError("Unable to load task file " + task_params_file)
    with open(task_params_file, "r") as fh:
        task_params = json.load(fh)
    if "shutdown" in task_params.keys():
        if str(task_params["shutdown"]) == "0":
            return False
    disable_shutdown_flag_file = os.path.join(input_folder, "disable_shutdown")
    if os.path.exists(disable_shutdown_flag_file):
        return False
    return default


def main():
    """
    Main process: wait for input, run task and wait for output to be fetched

    :return:    0 In case of success, other values in case of failure
    :rtype:     int
    """
    input_folder = os.path.join(TASK_FOLDER, "inputs")
    output_folder = os.path.join(TASK_FOLDER, "outputs")
    try:
        try:
            init_logging()
            log.info("Waiting for input file")
            if not wait_for_file(os.path.join(input_folder, "start_task"), 0):
                log.warning("Timeout for input expired, exiting...")
                return 1
            log.info("Running task")
            run_task()
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            save_state("success")
            log.info("Task finished")
        except (KeyboardInterrupt, SystemExit):
            save_state("cancel")
            log.info("The task has been interrupted by a signal, exiting...")
            return 0
        except AbortError as e:
            save_state("error")
            log.error(str(e))
            return 1
        except subprocess.CalledProcessError as e:
            save_state("error")
            log.exception(str(e)+":\nOutput:\n"+str(e.output))
            return 1
        except Exception as e:
            save_state("error")
            log.exception(e)
            return 1

        try:
            log.info("Waiting for output fetch to complete")
            if not wait_for_file(os.path.join(input_folder, "output_fetched"), 0):
                log.warning("Timeout for fetching output expired, exiting...")
                return 1
            log.info("Output fetched, exiting")
            return 0
        except (KeyboardInterrupt, SystemExit):
            log.info("The task has been interrupted by a signal before output fetching, exiting...")
            return 0
        except AbortError as e:
            log.error("Exception during output fetching: "+str(e))
            return 1
        except subprocess.CalledProcessError as e:
            log.error("Exception during output fetching")
            log.exception(str(e)+":\nOutput:\n"+str(e.output))
            return 1
        except Exception as e:
            log.error("Exception during output fetching")
            log.exception(e)
            return 1
    finally:
        if should_shutdown(input_folder):
            try:
                log.info("Shutting down")
                shutdown()
            except (KeyboardInterrupt, SystemExit):
                log.info("Shutdown canceled")
            except subprocess.CalledProcessError as e:
                log.error("Exception while trying to shutdown ami from within")
                log.exception(str(e) + ":\nOutput:\n" + str(e.output))
            except Exception as e:
                log.error("Exception while trying to shutdown ami from within")
                log.exception(e)


if __name__ == '__main__':
    sys.exit(main())
