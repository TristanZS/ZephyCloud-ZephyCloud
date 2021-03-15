#!/usr/bin/env python

import os
import sys
import argparse
import subprocess
import json

try:  # py3
    from configparser import ConfigParser
except ImportError:  # py2
    from ConfigParser import ConfigParser

try:  # py3
    from shlex import quote
except ImportError:  # py2
    from pipes import quote

# Project specific libs
script_path = os.path.dirname(os.path.abspath(__file__))


def aws_region_to_zone(region):
    return 'china' if region.startswith("cn-") else 'west'


def to_str(var):
    if isinstance(var, str):
        return var
    elif isinstance(var, bytes):
        return var.decode("UTF-8")
    else:
        return str(var)


def check_call_in_venv(cmd, venv_folder, cwd=None):
    bash_cmd = "source "+quote(venv_folder)+"/bin/activate"
    if cwd:
        bash_cmd += " && cd "+quote(cwd)
    bash_cmd += " && "+" ".join([quote(arg) for arg in cmd])
    return subprocess.check_call(["/usr/bin/env", "bash", "-c", bash_cmd])


def check_output_in_venv(cmd, venv_folder, cwd=None):
    bash_cmd = "source "+quote(venv_folder)+"/bin/activate"
    if cwd:
        bash_cmd += " && cd "+quote(cwd)
    bash_cmd += " && "+" ".join([quote(arg) for arg in cmd])
    return subprocess.check_output(["/usr/bin/env", "bash", "-c", bash_cmd])


def deploy():
    home_folder = os.path.join("/home", "zephycloud")

    # Setup config
    with open(os.path.join(script_path, "ami_versions.json"), "r") as fh:
        ami_versions = json.load(fh)
    conf = ConfigParser()
    conf.read(os.path.join(home_folder, "config.conf"))
    for section in conf.sections():
        if not section.startswith("provider_") or not conf.get(section, "type").startswith("aws"):
            continue
        zone = aws_region_to_zone(conf.get(section, "aws_region"))
        if zone in ami_versions.keys():
            conf.set(section, "ami", ami_versions[zone])
            conf.set(section, "cluster_ami", ami_versions[zone])
    with open(os.path.join(home_folder, "config.conf"), "w") as fh:
        conf.write(fh)

    # Database management
    subprocess.check_call(["rsync", "-a", "-O", "--no-perms", "--ignore-existing", "--exclude=.*", "--exclude=*.pyc",
                           os.path.join(script_path, "migrations"),
                           os.path.join(home_folder, 'database', 'migrations', 'versions')])
    subprocess.check_call(["cp", "-f", os.path.join(script_path, "current_version.txt"),
                           os.path.join(home_folder, 'database', 'current_version.txt')])
    subprocess.check_call('su -l postgres -c '+quote("pg_dump " + quote("zephycloud")) + \
                          " | gzip > " + quote(os.path.join(home_folder, "database", "backup.sql.gz")),
                          shell=True)
    migration_path = os.path.join(home_folder, "database", "migrations")
    with open(os.path.join(home_folder, 'database', 'current_version.txt'), "r") as fh:
        target_migration = fh.read().strip().lower()

    venv_folder = os.path.join(home_folder, "zephycloud_env")
    current_migration_raw = check_output_in_venv(["alembic", "-c", os.path.join(migration_path, "alembic_quiet.ini"),
                                                  "current"], venv_folder, cwd=migration_path)
    current_migration = to_str(current_migration_raw).strip().split(" ")[0].strip().lower()
    if current_migration != target_migration:
        migration_history_raw = subprocess.check_output(["alembic", "history"], cwd=migration_path)
        migration_lines = migration_history_raw.decode("UTF-8").strip().splitlines()
        migration_history = [l.split()[2].rstrip(",").strip().lower() for l in migration_lines]
        current_migration_pos = migration_history.index(current_migration)
        target_migration_pos = migration_history.index(target_migration)
        print("AAA 3")
        if current_migration_pos > target_migration_pos:
            check_call_in_venv(['alembic', "upgrade", target_migration], venv_folder, cwd=migration_path)
        else:
            check_call_in_venv(['alembic', "downgrade", target_migration], venv_folder, cwd=migration_path)

    # Sync source code folder
    subprocess.check_call(["rsync", "-zrS", "--delete",
                           os.path.join(script_path, "server").rstrip("/")+"/",
                           os.path.join(home_folder, "app").rstrip("/")+"/"])
    subprocess.check_call(["rsync", "-zrS",
                           '--exclude=.*',
                           '--exclude=plugins/*',
                           '--exclude=vendors/*',
                           '--exclude=app/Config/dashboard.conf',
                           "--delete",
                           os.path.join(script_path, "dashboard").rstrip("/")+"/",
                           os.path.join(home_folder, "dashboard").rstrip("/")+"/"])
    subprocess.check_call(["chown", "-R", "zephycloud:zephycloud", home_folder])

    # Restart services
    subprocess.check_call(["systemctl", "restart", "zephycloud.service"])
    subprocess.check_call(["systemctl", "restart", "zephycloud_webapi.service"])
    subprocess.check_call(["systemctl", "restart", "zephycloud_websocket.service"])


def main():
    try:
        parser = argparse.ArgumentParser(description="Deploy zephycloud source code on current machine")
        parser.parse_args()
        deploy()
    except (KeyboardInterrupt, SystemExit):
        sys.stderr.write(os.linesep + "Aborted..." + os.linesep)
        sys.stderr.flush()
        return 0
    except Exception as e:
        sys.stderr.write("Unknown error: " + os.linesep + str(e) + os.linesep)
        sys.stderr.flush()
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

