#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libs
import os
import sys
import py_compile
import subprocess
import shutil
import argparse
import json
import stat
import tempfile
import contextlib


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


def compile_fortran(infile, outfile):
    """
    Compile fortran file and copy output

    :param infile:      Fortran source file path
    :type infile:       str
    :param outfile:     Binary output file path
    :type outfile:      str
    """
    print("compiling fortran file " + infile)
    if not os.path.exists(infile):
        raise RuntimeError("Unable to compile fortran file, "+repr(infile)+" not found")
    out_folder = os.path.abspath(os.path.dirname(outfile))
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)
    with temp_folder() as tmp_folder:
        subprocess.check_call(['gfortran', '-w', infile, '-o', outfile], cwd=tmp_folder)
    file_mode = os.stat(outfile)
    os.chmod(outfile, file_mode.st_mode | stat.S_IEXEC)


def compile_python(infile, outfile=None):
    """
    Compile a python script

    :param infile:      The file to compile
    :type infile:       str
    :param outfile:     The output file. Optional, default None
                        If not provided, it's a pyc file at the same place than the input file.
    :type outfile:      str|None
    :return:            The output file path
    :rtype:             str
    """
    print("compiling python file " + infile)
    infile = os.path.abspath(infile)
    if not os.path.exists(infile):
        raise RuntimeError("Unable to compile python file, " + repr(infile) + " not found")

    if outfile is None:
        if infile.endswith('.py'):
            outfile = infile+"c"
        else:
            raise RuntimeError("Unable to compile python file, unable to guess destination name")

    out_folder = os.path.abspath(os.path.dirname(outfile))
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    compiled = infile+"c"
    if os.path.exists(compiled):
        os.remove(compiled)
    py_compile.compile(infile)
    if os.path.abspath(outfile) != compiled:
        if os.path.exists(outfile):
            os.remove(outfile)
        shutil.copy(compiled, outfile)
    file_mode = os.stat(outfile)
    os.chmod(outfile, file_mode.st_mode | stat.S_IEXEC)
    return outfile


def copy_file(infile, outfile):
    print("copying file " + infile)
    infile = os.path.abspath(infile)
    if not os.path.exists(infile):
        raise RuntimeError("Unable to compile python file, " + repr(infile) + " not found")

    out_folder = os.path.abspath(os.path.dirname(outfile))
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)
    shutil.copy(infile, outfile)
    file_mode = os.stat(outfile)
    os.chmod(outfile, file_mode.st_mode | stat.S_IEXEC)


def main():
    """
    Main process: wait for input, run task and wait for output to be fetched

    :return:    0 In case of success, other values in case of failure
    :rtype:     int
    """
    parser = argparse.ArgumentParser(description='Compile the toolchain')
    parser.add_argument("action_file", help='File where compilation list is located')
    parser.add_argument("dest_folder", help='Where we will put the compiled files')
    args = parser.parse_args()

    action_file = os.path.abspath(args.action_file)
    if not os.path.exists(action_file):
        sys.stderr.write("Unable to locate file "+action_file+os.linesep)
        sys.stderr.flush()
        return 1
    src_folder = os.path.join(os.path.dirname(action_file), "inputs")
    if not os.path.exists(src_folder):
        sys.stderr.write("Unable to locate folder " + src_folder + os.linesep)
        sys.stderr.flush()
        return 1

    dest_folder = os.path.abspath(args.dest_folder)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    with open(args.action_file, "r") as fh:
        actions = json.load(fh)
    for action, input_file, output_file in actions:
        output_file = os.path.join(dest_folder, output_file)
        if action == "compile_python":
            input_file = os.path.join(src_folder, input_file)
            compile_python(input_file, output_file)
        elif action == "compile_fortran":
            input_file = os.path.join(src_folder, input_file)
            compile_fortran(input_file, output_file)
        elif action == "copy":
            if os.path.exists(os.path.join(src_folder, input_file)):
                input_file = os.path.join(src_folder, input_file)
            elif os.path.exists(os.path.join(dest_folder, input_file)):
                input_file = os.path.join(dest_folder, input_file)
            else:
                sys.stderr.write("Unable to locate input file " + input_file + os.linesep)
                sys.stderr.flush()
                return 1
            copy_file(input_file, output_file)
        else:
            sys.stderr.write("unknown action " + repr(action) + os.linesep)
            sys.stderr.flush()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
