#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This script import scripts from zephytools project to current source file tree
"""

# Python core libs
import sys
import os
import argparse
import tempfile
import shutil
import stat
import json
import subprocess

# Project specific libs
script_path = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.abspath(os.path.join(script_path, "..", ".."))
sys.path.append(os.path.join(project_path, 'tools', 'common'))

import project_util


class WorkerCompilationInfo(object):
    def __init__(self, zt_path, toolchain_path, src_toolchain_path):
        super(WorkerCompilationInfo, self).__init__()
        self._zt_path = zt_path
        self._toolchain_path = toolchain_path
        self._src_toolchain_path = src_toolchain_path
        self._action_list = []  # list of tuple of action, input, output

    def has_dest(self, input_file):
        for _, _, output_file in self._action_list:
            if output_file == input_file:
                return True
        return False

    def compile_python(self, input_file, output_file):
        self._action_list.append(("compile_python", input_file, output_file))

    def compile_fortran(self, input_file, output_file):
        self._action_list.append(("compile_fortran", input_file, output_file))

    def copy(self, input_file, output_file):
        self._action_list.append(("copy", input_file, output_file))

    def save(self):
        if os.path.exists(self._src_toolchain_path):
            shutil.rmtree(self._src_toolchain_path)
        src_folder = os.path.join(self._src_toolchain_path, "inputs")
        os.makedirs(src_folder)

        actions = []
        for action, input_file, output_file in self._action_list:
            if input_file.startswith(self._zt_path):
                relative_input_file = input_file[len(self._zt_path):].lstrip("/").lstrip(os.linesep)
                folder = os.path.join(src_folder, os.path.dirname(relative_input_file))
                if not os.path.exists(folder):
                    os.makedirs(folder)
                shutil.copy(input_file, os.path.join(src_folder, relative_input_file))
                input_file = relative_input_file
            elif input_file.startswith(self._toolchain_path):
                input_file = input_file[len(self._toolchain_path):].lstrip("/").lstrip(os.linesep)

            if not output_file.startswith(self._toolchain_path):
                raise RuntimeError("this should not happen: output_file = "+str(output_file))
            output_file = output_file[len(self._toolchain_path):].lstrip("/").lstrip(os.linesep)
            actions.append((action, input_file, output_file))

        with open(os.path.join(self._src_toolchain_path, "to_compile.json"), "w") as fh:
            json.dump(actions, fh)


def copy_zt(input_file, output_file, worker_compile_info, set_executable=True):
    """
    Copy file, compiling python if required and creating parent folder if required

    :param input_file:      The file to copy
    :type input_file:       str
    :param output_file:     The destination
    :type output_file:      str
    :param set_executable:  Set the +x execution bit. Optional, default True
    :type set_executable:   bool
    """
    input_file = os.path.abspath(input_file)

    # Get real output filename
    if os.path.exists(output_file) and os.path.isdir(output_file):
        out_folder = os.path.abspath(output_file)
        output_file = os.path.join(out_folder, os.path.basename(input_file))
    else:
        out_folder = os.path.abspath(os.path.dirname(output_file))
        output_file = os.path.abspath(output_file)

    # Compile python if required
    if input_file.endswith(".pyc"):
        if os.path.exists(input_file[:-1]) or worker_compile_info.has_dest(input_file[:-1]):
            worker_compile_info.compile_python(input_file[:-1], output_file)
            return

    # We don't find the file, maybe it needs first to be compiled ?
    if not os.path.exists(input_file):
        if worker_compile_info.has_dest(input_file):
            worker_compile_info.copy(input_file, output_file)
            return
        raise RuntimeError("Unable to locate file " + input_file)

    # We create parent folder if required
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    # Copy and set executable
    shutil.copy(input_file, output_file)
    if set_executable:
        file_mode = os.stat(output_file)
        os.chmod(output_file, file_mode.st_mode | stat.S_IEXEC)


def import_zephytools_files(zt_path):
    """
    Fetch source code from a zephytools folder

    :param zt_path:     The zephytools folder
    :type zt_path:      str
    """

    # Constants: files to import
    MISC_FILES = ['zc_files.py', 'zc_variables.py']
    COMMON_FILES = ['ZS_VARIABLES.py', 'ZS_COMMON.py']
    FORTRAN_FILES = [
        ['UTILS_oromap_process.f90', 'OROMAP-PROCESS'],
        ['UTILS_oroxyz_process.f90', 'OROXYZ-PROCESS'],
        ['UTILS_rou_process.f90', 'ROU-PROCESS'],
        ['UTILS_oromapfast_process.f90', 'OROMAPFAST-PROCESS'],
        ['UTILS_roughness_process.f90', 'ROUGHNESS-PROCESS'],
        ['CFD_MESH_01_AnalyseMesh.f90', 'CFD_MESH_01_AnalyseMesh'],
        ['CFD_MESH_01_Propa.f90', 'CFD_MESH_01_Propa']
    ]

    ANAL_PROCESS_FILES = ['CFD_ANALYSE.py']
    ANAL_FILES_ORDER = ['OROMAP-PROCESS',
                        'OROXYZ-PROCESS',
                        'ROU-PROCESS',
                        'OROMAPFAST-PROCESS']

    MESH_PROCESS_FILES = ['CFD_MESH_01.py',
                          'CFD_MESH_01_PropaOro.pyc',
                          'CFD_MESH_01_PropaRou.pyc',
                          'CFD_MESH_01_InOut.pyc']

    MESH_FILES_ORDER = ['OROMAP-PROCESS',
                        'OROXYZ-PROCESS',
                        'ROUGHNESS-PROCESS',
                        'CFD_MESH_01_AnalyseMesh',
                        'CFD_MESH_01_PropaOro.pyc',
                        'CFD_MESH_01_PropaRou.pyc',
                        'CFD_MESH_01_InOut.pyc',
                        'CFD_MESH_01_Propa']

    CALC_PROCESS_FILES = ['CFD_CALC_01.py', 'CFD_CALC_RESTART.py', 'CFD_CALC_01_SURVEY.py']
    CALC_STATUS_FILES = ['CFD_CALC_ZIP_STATUS.py', 'CFD_CALC_STOP.py']

    if not os.path.exists(zt_path) or not os.path.isdir(zt_path):
        raise RuntimeError("Invalid ZephyTools path: "+repr(zt_path))

    # We only use the internal ZephyTOOLS folder
    zt_sub_path = os.path.join(zt_path, "ZephyTOOLS")
    if os.path.exists(zt_sub_path) and os.path.isdir(zt_sub_path):
        zt_path = zt_sub_path

    # Some source path definitions
    src_cloud = os.path.join(zt_path, "ZEPHYCLOUD")
    src_fortran = os.path.join(zt_path, "FORTRAN_SRC")
    src_common = os.path.join(zt_path, "PYTHON_COMMON")
    src_process = os.path.join(zt_path, "PYTHON_PROCESS")
    src_fs_common = os.path.join(zt_path, "FILE_SYSTEM", "COMMON")
    src_fs_common_foam = os.path.join(zt_path, "FILE_SYSTEM", "COMMON", "foam")

    # Some preliminary checks
    for folder in (src_cloud, src_fs_common, src_fortran, src_common, src_process, src_fs_common_foam):
        if not os.path.exists(folder) or not os.path.isdir(folder):
            raise RuntimeError("Not a valid zephytools path: folder "+repr(folder)+" doesn't exists")


    # Rebuild zephytools translations
    subprocess.check_call(["python", os.path.join(zt_path, "UPDATE", "UPDATE.py")],
                          cwd=os.path.abspath(os.path.join(zt_path, "..")))

    # Ensure the destination path exists
    dest_toolchain = os.path.join(project_path, "src", "worker", "toolchain")
    if not os.path.exists(dest_toolchain):
        os.makedirs(dest_toolchain)
        project_util.touch(os.path.join(dest_toolchain, ".keep"))

    dest_toolchain_src = os.path.join(project_path, "src", "worker", "toolchain_to_compile")
    if not os.path.exists(dest_toolchain_src):
        os.makedirs(dest_toolchain_src)

    # We backup the destination, in case of failure
    with project_util.temp_folder(tempfile.gettempdir()) as tmp_dir:
        shutil.move(dest_toolchain, tmp_dir)
        shutil.move(dest_toolchain_src, tmp_dir)
        try:
            # Common part
            dest_zt = os.path.join(dest_toolchain, "ZephyTOOLS")
            dest_bin = os.path.join(dest_zt, "APPLI", "BIN")
            dest_tmp = os.path.join(dest_zt, "APPLI", "TMP")
            os.makedirs(os.path.join(dest_zt, "COMMON"))
            shutil.copytree(src_fs_common_foam, os.path.join(dest_zt, "COMMON", "foam"))
            shutil.copy(os.path.join(zt_path, "UPDATE", "ZT_translations.db"),
                        os.path.join(dest_zt, "COMMON", "ZT_translations.db"))
            shutil.copy(os.path.join(src_fs_common, "version"), os.path.join(dest_zt, "COMMON", "version"))
            os.makedirs(dest_bin)
            os.makedirs(dest_tmp)

            worker_compile_info = WorkerCompilationInfo(zt_path, dest_toolchain, dest_toolchain_src)

            for file_path in MISC_FILES:
                copy_zt(os.path.join(src_cloud, file_path), dest_tmp, worker_compile_info)
                copy_zt(os.path.join(src_cloud, file_path), dest_toolchain, worker_compile_info)

            for src, dest in FORTRAN_FILES:
                worker_compile_info.compile_fortran(os.path.join(src_fortran, src), os.path.join(dest_bin, dest))

            for file_path in COMMON_FILES:
                copy_zt(os.path.join(src_common, file_path), dest_tmp, worker_compile_info)

            # Anal specific part
            for file_path in ANAL_PROCESS_FILES:
                copy_zt(os.path.join(src_process, file_path), dest_tmp, worker_compile_info)

            extra = ''
            for file in ANAL_FILES_ORDER:
                extra += '_'
                new_filename = extra + ANAL_PROCESS_FILES[0]
                copy_zt(os.path.join(dest_bin, file), os.path.join(dest_tmp, new_filename), worker_compile_info)

            # Mesh specific part
            copy_zt(os.path.join(src_process, MESH_PROCESS_FILES[0]), dest_tmp, worker_compile_info)
            for file_path in MESH_PROCESS_FILES:
                copy_zt(os.path.join(src_process, file_path), dest_bin, worker_compile_info)

            extra = ''
            for file in MESH_FILES_ORDER:
                extra += '_'
                new_filename = extra + MESH_PROCESS_FILES[0]
                copy_zt(os.path.join(dest_bin, file), os.path.join(dest_tmp, new_filename), worker_compile_info)

            # Calc specific part
            for file_path in CALC_PROCESS_FILES:
                copy_zt(os.path.join(src_process, file_path), dest_tmp, worker_compile_info)
            for file_path in CALC_PROCESS_FILES:
                copy_zt(os.path.join(src_process, file_path), dest_bin, worker_compile_info)
            for file_path in CALC_STATUS_FILES:
                copy_zt(os.path.join(src_process, file_path), dest_tmp, worker_compile_info)

            worker_compile_info.save()

            project_util.touch(os.path.join(dest_toolchain, ".keep"))
            project_util.touch(os.path.join(dest_toolchain, "__init__.py"))
        except:
            exc_info = sys.exc_info()
            # In case of failure, we restore the backup folder
            if os.path.exists(dest_toolchain):
                shutil.rmtree(dest_toolchain)
            shutil.move(os.path.join(tmp_dir, "toolchain"), dest_toolchain)
            shutil.move(os.path.join(tmp_dir, "toolchain_to_compile"), dest_toolchain_src)
            raise exc_info[0], exc_info[1], exc_info[2]


def main():
    """
    Fetch source code from a zephytools folder

    :return:        0 in case of success, a positive int in case of error
    :rtype:         int
    """
    parser = argparse.ArgumentParser(description='Fetch source code from a zephytools folder')
    parser.add_argument('--src-path', '-s', help='zephytools folder')
    args = parser.parse_args()

    if not project_util.has_exec_installed('gfortran'):
        sys.stderr.write("No 'gfortran' executable found, unable to import files"+os.linesep)
        sys.stderr.flush()
        return 1

    try:
        zephytools_path = args.src_path
        if not zephytools_path:
            zephytools_path = project_util.read_path("Zephytool source path: ", allow_files=False, allow_folders=True,
                                                     history_key="zephytools_path")

        while not os.path.exists(zephytools_path) or not os.path.isdir(zephytools_path):
            sys.stderr.write(os.linesep+"Invalid path"+os.linesep)
            sys.stderr.flush()
            zephytools_path = project_util.read_path("Zephytool source path: ", allow_files=False, allow_folders=True,
                                                     history_key="zephytools_path")

        import_zephytools_files(os.path.abspath(zephytools_path))
        print("Importation succeed")
        return 0
    except (SystemExit, KeyboardInterrupt):
        print(os.linesep+"Aborted")
        return 0
    except (Exception, subprocess.CalledProcessError) as e:
        sys.stdout.flush()
        sys.stderr.write(os.linesep+"Error detected:"+os.linesep)
        sys.stderr.write("  "+str(e) + os.linesep)
        sys.stderr.flush()
        return 1


if __name__ == '__main__':
    sys.exit(main())
