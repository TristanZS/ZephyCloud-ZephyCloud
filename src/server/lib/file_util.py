# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core libraries
import contextlib
import tempfile
import os
import shutil
import hashlib


@contextlib.contextmanager
def temp_file(content, suffix="", prefix="tmp", dir=None):
    """
    Generate a temporary file, and put the content inside it
    It yield the file path, and ensure file destruction

    :param content:     The content to put inside the temp file
    :type content:      str
    :param suffix:      The end of the name of the generated temp file. Optional, default empty string
    :type suffix:       str
    :param prefix:      The beginning of the name of the generated temp file. Optional, default "tmp"
    :type prefix:       str
    :param dir:         The place where we will create the temporary file. Optional, default None
    :type dir:          str|None
    :return:            The temporary file path
    :rtype:             str
    """
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    tmp_filename = None
    fd = None
    try:
        fd, tmp_filename = tempfile.mkstemp(suffix, prefix, dir)
        with open(tmp_filename, "w") as fh:
            fh.write(content)
            fh.flush()
        yield tmp_filename
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_filename is not None and os.path.exists(tmp_filename):
            os.remove(tmp_filename)


@contextlib.contextmanager
def temp_filename(suffix="", prefix="tmp", dir=None):
    """
    Generate a temporary file
    It yield the file path, and ensure file destruction

    :param suffix:      The end of the name of the generated temp file. Optional, default empty string
    :type suffix:       str
    :param prefix:      The beginning of the name of the generated temp file. Optional, default "tmp"
    :type prefix:       str
    :param dir:         The place where we will create the temporary file. Optional, default None
    :type dir:          str|None
    :return:            The temporary file path
    :rtype:             str
    """
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    tmp_filename = None
    fd = None
    try:
        fd, tmp_filename = tempfile.mkstemp(suffix, prefix, dir)
        yield tmp_filename
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_filename is not None and os.path.exists(tmp_filename):
            os.remove(tmp_filename)


def unique_filename(suffix="", prefix="tmp", dir=None):
    """
    Generate a unique filename
    It yield the file path, and ensure file destruction

    :param suffix:      The end of the name of the generated temp file. Optional, default empty string
    :type suffix:       str
    :param prefix:      The beginning of the name of the generated temp file. Optional, default "tmp"
    :type prefix:       str
    :param dir:         The place where we will create the temporary file. Optional, default None
    :type dir:          str|None
    :return:            The temporary file path
    :rtype:             str
    """
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    fd, tmp_filename = tempfile.mkstemp(suffix, prefix, dir)
    if fd is not None:
        os.close(fd)
    return tmp_filename


@contextlib.contextmanager
def temp_folder(dir=None):
    """
    Create a temporary folder, yield it and then remove it

    :param dir:   The place where we will create the temporary folder. Optional, default None
    :type dir:    str|None
    :return:      The created temporary folder path
    :rtype:       str
    """
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    output_path = tempfile.mkdtemp(dir=dir)
    try:
        yield output_path
    finally:
        if os.path.exists(output_path):
            shutil.rmtree(output_path)


def touch(path):
    """
    Create file if it doesn't exists and set modification date to now
    Equivalent of posix `touch` command

    :param path:    File to touch
    :type path:     str
    """
    parent_folder = os.path.dirname(os.path.abspath(path))
    if parent_folder and not os.path.exists(parent_folder):
        os.makedirs(parent_folder)
    with open(path, 'a'):
        os.utime(path, None)


def md5sum(filename, block_size=65536):
    """
    Cimpoute the md5 sum of an existing file

    :param filename:        The file to hash
    :type filename:         str
    :param block_size:      The size of the buffer, optional, default 65536
    :type block_size:       int
    :return:                The md5 hash of given file
    :rtype:                 str
    """
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
