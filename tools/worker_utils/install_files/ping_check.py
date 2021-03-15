#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""
This file wait for
"""

# Python core libs
import sys
import os
import argparse
import json
import datetime
import time
import multiprocessing
import subprocess
import string


class Ec2InstanceId(object):
    __cache = None

    @staticmethod
    def get(silent=False):
        if Ec2InstanceId.__cache is None:
            try:
                result = subprocess.check_output(["curl", "--silent",
                                                  "--connect-timeout", "1",
                                                  "http://169.254.169.254/latest/meta-data/instance-id/"])
                Ec2InstanceId.__cache = result.strip()
            except (StandardError, subprocess.CalledProcessError) as e:
                Ec2InstanceId.__cache = False
                if not silent:
                    sys.stderr.write(os.linesep + str(e) + os.linesep)
                    sys.stderr.flush()
        return Ec2InstanceId.__cache


def is_ec2():
    instance_id = Ec2InstanceId.get(True)
    sys.stderr.write("ec2 instance_id: "+repr(instance_id)+os.linesep)
    sys.stderr.flush()
    if not instance_id:
        return False
    return True


def should_shutdown(input_folder):
    try:
        task_params_file = os.path.join(input_folder, "task_params.json")
        if not os.path.exists(task_params_file):
            return True
        with open(task_params_file, "r") as fh:
            task_params = json.load(fh)
        if "shutdown" in task_params.keys():
            if str(task_params["shutdown"]) == "0":
                return False
        disable_shutdown_flag_file = os.path.join(input_folder, "disable_shutdown")
        if os.path.exists(disable_shutdown_flag_file):
            return False
        return True
    except StandardError:
        return True


def is_docker():
    path = "/proc/" + str(os.getpid()) + "/cgroup"
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        return "docker" in f.read()


def is_systemd():
    return subprocess.call("pidof systemd > /dev/null 2>&1", shell=True) == 0


def shutdown():
    try:
        if is_ec2():
            print("Terminating the current instance")
            zone = subprocess.check_output(["curl", "--silent",
                                            "--connect-timeout", "1",
                                            "http://169.254.169.254/latest/meta-data/placement/availability-zone"])
            zone = zone.strip()
            region = zone.strip().rstrip(string.ascii_lowercase)

            subprocess.call(["aws", "ec2", "terminate-instances",
                             "--region", region,
                             "--instance-ids",  Ec2InstanceId.get()])
            time.sleep(5)
    except (StandardError, subprocess.CalledProcessError) as e:
        sys.stderr.write(os.linesep+"warning: "+str(e)+os.linesep)
        sys.stderr.flush()
    print("Shutdown of the instance requested")
    if is_docker:
        os.system("kill -KILL -1")
    elif is_systemd():
        os.system("halt")
    else:  # Old sysV:
        os.system("shutdown -h now")


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


def wait_for_time_sync():
    time.sleep(60)


def utc_from_timestamp(ts):
    offset = datetime.datetime.now() - datetime.datetime.utcnow()
    return (datetime.datetime.fromtimestamp(ts) - offset).replace(tzinfo=None)


def wait_until_kill(ping_file, input_folder):
    last_ping = datetime.datetime.utcnow()
    while True:
        if os.path.exists(ping_file):
            last_ping = utc_from_timestamp(os.path.getmtime(ping_file))
        elapsed = datetime.datetime.utcnow() - last_ping
        if os.path.exists(os.path.join(input_folder, "start_task")):
            if elapsed > datetime.timedelta(minutes=10):
                print("The file "+ping_file+" is old (after start): "+str(last_ping)+os.linesep)
                return
        elif elapsed > datetime.timedelta(minutes=60):
            print("The file " + ping_file + " is old (it never starts): " + str(last_ping) + os.linesep)
            return
        time.sleep(60)


def main():
    """
    Main process: wait for input, run task and wait for output to be fetched

    :return:    0 In case of success, other values in case of failure
    :rtype:     int
    """
    default_input_folder = "/home/aziugo/worker_scripts/inputs"
    default_ping_file = os.path.join(default_input_folder, "worker_ping")

    parser = argparse.ArgumentParser(description="Shutdown the current instance  if it hasn't been pinged recently.")
    parser.add_argument("--file", "-f", default=default_ping_file, help="The file to check for time update")
    parser.add_argument("--directory", "-d", default=default_input_folder, help="The toolchain input folder")
    parser.add_argument("--fork", action="store_true", help="Run in a double forked process")
    args = parser.parse_args()
    ping_file = args.file
    input_folder = args.directory

    if args.fork:
        try:
            in_child, parent_pid, child_pid = double_fork()
        except OSError as e:
            sys.stderr.write(os.linesep+"Unable to run command, fork failed, cause:" +str(e) + os.linesep)
            sys.stderr.flush()
            return 1

        if not in_child:
            return 0  # Nothing to do in parent, we continue the main loop

    skip_kill = False
    try:
        wait_for_time_sync()
        wait_until_kill(ping_file, input_folder)
    except (KeyboardInterrupt, SystemExit):
        sys.stderr.write(os.linesep+"Quit..."+os.linesep)
        skip_kill = True
    except Exception as e:
        sys.stderr.write(os.linesep+str(e)+os.linesep)
    finally:
        sys.stderr.flush()
        if skip_kill or not should_shutdown(input_folder):
            return 0
        for i in range(0, 5):
            try:
                shutdown()
            except (KeyboardInterrupt, SystemExit):
                pass
            except Exception as e:
                sys.stderr.write(os.linesep+"Exception while trying to shutdown ami from within: "+str(e)+os.linesep)
            finally:
                sys.stderr.flush()


if __name__ == '__main__':
    sys.exit(main())
