#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120


"""
This script create an AMI image on one or several aws regions.
It also propose to update the config.yml file accordingly
"""

# Core libs
import os
import argparse
import sys
import contextlib
import datetime
import time
import json
import threading
import platform
import uuid

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

# Third party libs
import boto3

# Project specific libs
script_path = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.abspath(os.path.join(script_path, "..", ".."))
sys.path.append(os.path.join(project_path, 'tools', 'common'))

import project_util
import interactive_ssh


# Some constants:
AMI_CREATION_DISK_SIZE = 10  # GigaBytes. Could be more if needed
AMI_CREATOR_KEY_NAME = "ami_creator_key"
AMI_CREATION_INSTANCE_TYPE = "t2.medium"
AMI_BASE_IMAGE_NAME = "base_ubuntu_1804"
AMI_BASE_IMAGE_SSH_USER = "ubuntu"
AWS_SECURITY_GROUPS = ["SSH"]
DEFAULT_AWS_REGION = 'eu-west-1'
WORKER_FILES_PATH = "/root/install_files"
API_NAME = "zephycloud"


def get_and_check_aws_credentials(region):
    access_file = os.path.join(project_path, "local_secrets", "aws_credentials")

    try:
        ec2_rsc = boto3.resource("ec2", region_name=region, aws_access_key_id=None,
                                 aws_secret_access_key=None)
        if not ec2_rsc:
            raise RuntimeError("Unable to connect to AWS EC2 in region " + repr(region))
        ec2_rsc.meta.client.describe_images(Owners=['self'])
        return None, None
    except Exception as e:
        if not os.path.exists(access_file):
            raise e

    cfg = ConfigParser()
    cfg.read(access_file)
    if "default" not in cfg.sections():
        raise RuntimeError("Unable to get AWS credentials from file "+access_file)
    key_id = cfg.get("default", 'aws_access_key_id')
    key_secret = cfg.get("default", 'aws_secret_access_key')
    ec2_rsc = boto3.resource("ec2", region_name=region, aws_access_key_id=key_id,
                             aws_secret_access_key=key_secret)
    if not ec2_rsc:
        raise RuntimeError("Unable to connect to AWS EC2 in region " + repr(region))
    ec2_rsc.meta.client.describe_images(Owners=['self'])
    return key_id, key_secret


def aws_region_to_zone(region):
    """
    Get the aws zone of a specific location (ex: 'west', 'china' or 'gov')

    :param region:      The aws region name
    :type region:       str
    :return:            The location of a region
    :rtype:             str
    """
    return 'china' if region.startswith("cn-") else 'west'


def update_ami_versions(region, final_ami_id):
    json_file = os.path.join(project_path, "tools", "worker_utils", "ami_versions.json")
    if os.path.exists(json_file):
        try:
            with open(json_file, "r") as fh:
                json_content = json.load(fh)
        except Exception:
            json_content = {}
    else:
        json_content = {}

    zone = aws_region_to_zone(region)
    json_content[zone] = final_ami_id
    with open(json_file, "w+") as fh:
        json.dump(json_content, fh, indent=4, sort_keys=True)


@contextlib.contextmanager
def ec2_instance(ec2_rsc, api_name, base_ami, sec_groups):
    """
    Create an ec2 instance and yield it.
    It terminate the instance at the end of the function

    :param ec2_rsc:    An established EC2 connection
    :type ec2_rsc:     boto3.resources.factory.ec2.ServiceResource
    :param api_name:    Name of this API project
    :type api_name:     str
    :param base_ami:    The base image used to create AMI
    :type base_ami:     str
    :param sec_groups:  List of security groups of the AMI
    :type sec_groups:   list[str]
    :return:            The created instance identifier
    :rtype:             str
    """
    instance_list = ec2_rsc.create_instances(ImageId=base_ami,
                                             KeyName=AMI_CREATOR_KEY_NAME,
                                             InstanceType=AMI_CREATION_INSTANCE_TYPE,
                                             MinCount=1,
                                             MaxCount=1,
                                             SecurityGroups=sec_groups,
                                             Monitoring={'Enabled': False},
                                             InstanceInitiatedShutdownBehavior="terminate",
                                             EbsOptimized=False,
                                             BlockDeviceMappings=[{
                                                 'DeviceName': '/dev/sda1',
                                                 'Ebs': {
                                                     'VolumeSize': AMI_CREATION_DISK_SIZE,
                                                     'DeleteOnTermination': True,
                                                 }
                                             }])
    instance_id = instance_list[0].id
    try:
        instance_list[0].create_tags(Tags=[{"Key": "Custom", "Value": "True"},
                                           {"Key": "Name", "Value": api_name + "_worker_ami_creation"}])
        yield instance_id
    finally:
        try:
            for instance in instance_list:
                instance.terminate()
            print("  Ec2 instance terminated")
        except Exception as e:
            sys.stderr.write(os.linesep+os.linesep+"/!\\ -----------------------------"+os.linesep)
            sys.stderr.write("Unable to terminate instance " + str(instance_id) + os.linesep)
            sys.stderr.write("Please do it manually"+os.linesep+os.linesep)
            sys.stderr.write("Error details: " + str(e) + os.linesep)
            sys.stderr.flush()


__using_ec2_cache = {}


@contextlib.contextmanager
def using_ec2(region, key_id=None, key_secret=None):
    """
    Connect to AWS EC2 service for a specific region
    You should use this function via the "with" keyword

    :param region:      The AWS region you want to connect to
    :type region:       str
    :param key_id:      The AWS Token id, ex: 'AKIA...'
    :type key_id:       str|None
    :param key_secret:  The AWS Token secret
    :type key_secret:   str|None
    :return:            The established connection
    :rtype:             boto3.resources.factory.ec2.ServiceResource
    """
    global __using_ec2_cache

    cache_key = str(threading.currentThread().ident)+"_"+region+"_"+(key_id if key_id else "--no-key--")
    if cache_key in __using_ec2_cache.keys():
        yield __using_ec2_cache[cache_key]
    else:
        ec2_rsc = boto3.resource("ec2", region_name=region, aws_access_key_id=key_id,
                                 aws_secret_access_key=key_secret)
        if not ec2_rsc:
            raise RuntimeError("Unable to connect to AWS EC2 in region "+repr(region))
        __using_ec2_cache[cache_key] = ec2_rsc
        try:
            yield ec2_rsc
        finally:
            try:
                del __using_ec2_cache[cache_key]
            except (KeyboardInterrupt, KeyError):
                raise
            except Exception:
                pass


def get_ami_id(ec2_rsc, name, **tags):
    """
    Get the id of an existing AMI image
    Raise an error if more than one image if found

    :param ec2_rsc:         An established connection to AWS EC2 services
    :type ec2_rsc:          boto3.resources.factory.ec2.ServiceResource
    :param name:            Name of the image
    :type name:             str
    :param tags:            Tags values of the images, used as filter
    :type tags:             dict[str, str]
    :return:                The id of the AMI
    :rtype:                 str
    """
    filters = [{'Name': "tag:Name", "Values": [name]}]
    for key in tags.keys():
        filters.append({"Name": 'tag:'+key, "Values": str(tags[key])})
    results = ec2_rsc.meta.client.describe_images(Owners=['self'], Filters=filters)
    if len(results['Images']) > 1:
        raise RuntimeError("More than one AMI with name '"+str(name)+"'")
    elif len(results['Images']) < 1:
        raise RuntimeError("No AMI with name '" + str(name) + "'")
    return results['Images'][0]['ImageId']


def get_instance_public_ip(ec2_rsc, instance_id, timeout=300):
    """
    Get the public ip of an instance, waiting for timeout before raising issue

    :param ec2_rsc:         An EC2 connection
    :type ec2_rsc:          boto3.resources.factory.ec2.ServiceResource
    :param instance_id:     EC2 Instance identifier
    :type instance_id:      str
    :param timeout:         Time we try before failing, in seconds. 0 or None means not timeout. Optional, default 5min
    :type timeout:          int|float|datetime.timedelta|None
    :return:                The public ip of the instance
    :rtype:                 str
    """

    if timeout is None or (project_util.ll_float(timeout) and float(timeout) <= 0):
        time_limit = None
    else:
        if not isinstance(timeout, datetime.timedelta):
            timeout = datetime.timedelta(milliseconds=int(float(timeout)*1000))
        time_limit = datetime.datetime.utcnow() + timeout

    instance = ec2_rsc.Instance(instance_id)
    while time_limit is None or datetime.datetime.utcnow() < time_limit:
        instance.reload()
        instance_info = instance.network_interfaces_attribute
        if len(instance_info) == 0 or 'Association' not in instance_info[0].keys():
            time.sleep(2)
            continue
        details = instance_info[0]['Association']
        if 'PublicIp' not in details.keys() or not details['PublicIp']:
            time.sleep(2)
            continue
        return details['PublicIp']
    raise RuntimeError("Unable to get the public ip of instance " + str(instance_id))


def get_admin_default_password():
    folder = os.path.join(project_path, "local_secrets")
    admin_pwd_file = os.path.join(folder, "default_password.txt")
    if not os.path.exists(admin_pwd_file):
        raise RuntimeError("Missing admin default password file "+admin_pwd_file)
    with open(admin_pwd_file, "r") as fh:
        admin_pwd = fh.read().strip()
    if not admin_pwd or len(admin_pwd) > 40 or " " in admin_pwd or "\n" in admin_pwd:
        raise RuntimeError("Invalid admin default password inside file " + admin_pwd_file)
    return admin_pwd


def get_local_secret_ssh_keys(key_name, description):
    """
    Get public and private key content of secret ssh key

    :return:            The public and the private ssh key content
    :rtype:             Tuple[str, str]
    """
    folder = os.path.join(project_path, "local_secrets")
    priv_key_file = os.path.join(folder, key_name)
    if not os.path.exists(priv_key_file):
        raise RuntimeError("Missing private "+description+" "+priv_key_file)
    with open(priv_key_file, "r") as fh:
        priv_key_content = fh.read().strip()

    pub_key_file = os.path.join(folder, key_name+".pub")
    if not os.path.exists(pub_key_file):
        raise RuntimeError("Missing public "+description+" " + pub_key_file)
    with open(pub_key_file, "r") as fh:
        pub_key_content = fh.read().strip()

    return pub_key_content, priv_key_content


def get_ami_creator_ssh_keys():
    """
    Get the public and private key content of the AMI-creator ssh key

    :return:            The public and the private AMI creator ssh key
    :rtype:             Tuple[str, str]
    """
    return get_local_secret_ssh_keys("id_rsa_ami_creator", "AMI creator")


def get_worker_user_ssh_keys():
    return get_local_secret_ssh_keys("id_rsa_worker_user", "Worker main user")


def get_worker_root_ssh_keys():
    return get_local_secret_ssh_keys("id_rsa_worker_root", "Worker root user")


def get_aziugo_admin_pub_keys():
    """
    Get ths list of administrator ssh public keys from the dashboard

    :return:            The list of admin public keys
    :rtype:             dict[str, str]
    """

    folder = os.path.join(project_path, "local_secrets", "admin_keys")
    if not os.path.exists(folder):
        raise RuntimeError("Missing admin ssh public key folder "+folder)

    admin_keys = {}
    files = os.listdir(folder)
    for file in files:
        if not file.endswith(".pub"):
            continue
        username = os.path.basename(file)[0:-4]
        with open(os.path.join(folder, file), "r") as fh:
            content = fh.read().strip()
        admin_keys[username] = content
    if not admin_keys:
        raise RuntimeError("No public key inside " + folder)
    return admin_keys


def generate_ami(region, key_id, key_secret, base_ami_id, ssh_user, verbose=True):
    """
    Create an AMI image in EC2

    :param region:          The aws region where we want to create the AMI (ex: "eu-west-1")
    :type region:           str
    :param key_id:          The AWS Token id, ex: 'AKIA...'
    :type key_id:           str|None
    :param key_secret:      The AWS Token secret
    :type key_secret:       str|None
    :param base_ami_id:     The base image used to create AMI
    :type base_ami_id:      str
    :param ssh_user:        The user used to connect to the base AMI image
    :type ssh_user:         str
    :param verbose:         Do we want to show the install commands, Optional, default True
    :type verbose:          bool
    :return:                The new image id
    :rtype:                 str
    """
    quiet = not verbose

    if platform.system().lower() == "windows":
        project_util.dos2unix_folder(project_path)

    # Fetching required conf variables
    ssh_user_keys = [get_worker_user_ssh_keys()]
    ssh_root_keys = [get_worker_root_ssh_keys()]
    ami_name = API_NAME+"_worker/" + str(uuid.uuid4())
    admin_keys = get_aziugo_admin_pub_keys()
    pub_key, priv_key = get_ami_creator_ssh_keys()
    default_admin_pwd = get_admin_default_password()

    with using_ec2(region, key_id, key_secret) as conn:
        print("  Launching new EC2 worker instance...")

        install_files = os.path.join(project_path, "tools", "worker_utils", "install_files")
        with ec2_instance(conn, API_NAME, base_ami_id, AWS_SECURITY_GROUPS) as instance_id:
            with project_util.temp_file(priv_key) as key_path:
                public_ip = get_instance_public_ip(conn, instance_id)
                ssh_params = interactive_ssh.SshParams(public_ip, login=ssh_user, key=key_path)
                print("  Establishing ssh connection to worker at "+str(public_ip)+" ...")
                with interactive_ssh.using_interactive_ssh(ssh_params, wait_for_connection=True) as ssh_conn:
                    print("  Disable auto-update...")
                    ssh_conn.run(["systemctl", "stop", "apt-daily.timer"], as_user="root", quiet=True)
                    ssh_conn.run(["systemctl", "disable", "apt-daily.timer"], as_user="root", quiet=True)

                    print("  Transferring toolchain and install scripts...")
                    ssh_conn.run(["mkdir", "-p", WORKER_FILES_PATH], as_user="root", quiet=quiet)
                    ssh_conn.run(["mkdir", "-p", WORKER_FILES_PATH + "/admin_keys"], as_user="root", quiet=quiet)
                    ssh_conn.send_folder(os.path.join(project_path, "src", "worker"),
                                         WORKER_FILES_PATH+"/worker_scripts", as_user="root")
                    ssh_conn.send_file(os.path.join(project_path, "tools", "worker_utils", "setup_ami.sh"),
                                       WORKER_FILES_PATH, as_user="root")
                    ssh_conn.send_file(os.path.join(project_path, "tools", "worker_utils", "install_deps.sh"),
                                       WORKER_FILES_PATH, as_user="root")
                    ssh_conn.send_file(os.path.join(project_path, "tools", "worker_utils", "requirements.txt"),
                                       WORKER_FILES_PATH, as_user="root")
                    ssh_conn.send_file(os.path.join(install_files, "toolchain_compiler.py"),
                                       WORKER_FILES_PATH, as_user="root")
                    ssh_conn.send_file(os.path.join(install_files, "ping_check.py"),
                                       WORKER_FILES_PATH, as_user="root")
                    ssh_conn.send_file(os.path.join(install_files, "ping_check.service"),
                                       WORKER_FILES_PATH, as_user="root")
                    ssh_conn.run(["chmod", "+x", WORKER_FILES_PATH + "/setup_ami.sh"], as_user="root", quiet=quiet)
                    ssh_conn.run(["chmod", "+x", WORKER_FILES_PATH + "/install_deps.sh"], as_user="root", quiet=quiet)
                    ssh_conn.run(["chmod", "+x", WORKER_FILES_PATH + "/toolchain_compiler.py"], as_user="root",
                                 quiet=quiet)
                    ssh_conn.run(["chmod", "+x", WORKER_FILES_PATH + "/ping_check.py"], as_user="root", quiet=quiet)

                    print("  Copying worker access keys...")
                    with project_util.temp_file(default_admin_pwd) as dev_pwd_file:
                        ssh_conn.send_file(dev_pwd_file, WORKER_FILES_PATH + "/default_password.txt", as_user="root")

                    for admin in admin_keys.keys():
                        with project_util.temp_file(admin_keys[admin]) as admin_key_path:
                            ssh_conn.send_file(admin_key_path, WORKER_FILES_PATH+"/admin_keys/"+admin+".pub",
                                               as_user="root")

                    pubkeys = "\n".join([p[0] for p in ssh_user_keys])
                    with project_util.temp_file(pubkeys) as pubkeys_file:
                        ssh_conn.send_file(pubkeys_file, WORKER_FILES_PATH + "/api_keys", as_user="root")

                    root_pubkeys = "\n".join([p[0] for p in ssh_root_keys])
                    with project_util.temp_file(root_pubkeys) as root_pubkeys_file:
                        ssh_conn.send_file(root_pubkeys_file, WORKER_FILES_PATH + "/root_api_keys", as_user="root")

                print("  Running worker install script (this may take a while) ...")
                with interactive_ssh.using_interactive_ssh(ssh_params, wait_for_connection=True) as ssh_conn:
                    ssh_conn.run([WORKER_FILES_PATH + "/setup_ami.sh", API_NAME], as_user="root", quiet=quiet)
                ssh_conn.run(["sync"], as_user="root", quiet=quiet)

                print("  Cleaning installation files...")
                with interactive_ssh.using_interactive_ssh(ssh_params, wait_for_connection=True) as ssh_conn:
                    ssh_conn.run(["rm", "-rf", WORKER_FILES_PATH], as_user="root", quiet=quiet)
                    # cmd = "rm -rf '/home/" + ssh_user + "/.ssh'; "
                    # cmd += "rm -rf '/etc/sudoers.d/90-cloud-init-users'; "
                    # cmd += "userdel -rf '"+ssh_user+"'"
                    # ssh_conn.run(["bash", "-c", cmd], as_user="root", quiet=quiet)

            ami_id = conn.meta.client.create_image(InstanceId=instance_id, NoReboot=True, Name=ami_name)['ImageId']
            print("  Saving the AMI...")
            ami_object = conn.Image(ami_id)
            while True:
                time.sleep(1)
                ami_object.reload()
                image_status = ami_object.state
                if image_status == "pending":
                    continue
                elif image_status == "available":
                    break
                elif image_status == "failed":
                    raise RuntimeError("Image creation failed. See the AMI "+str(ami_id)+" in AWS console for details")
                else:
                    raise RuntimeError("Unknown AMI status "+repr(image_status))
            tags = [{"Key": "Api", "Value": API_NAME}, {"Key": "Name", "Value": API_NAME+"_worker"}]
            commit = project_util.get_current_git_commit()
            if commit:
                tags.append({"Key": "Version", "Value": commit})
            ami_object.create_tags(Tags=tags)
            return ami_id


def main():
    """
    Create an EC2 AMI image, and optionally save the id in the config.yml file

    :return:        0 in case of success, a positive int in case of error
    :rtype:         int
    """
    parser = argparse.ArgumentParser(description='Generate AWS EC2 AMI image')
    parser.add_argument("--region", '-r', help='An AWS region. Default region is '+DEFAULT_AWS_REGION,
                        default=DEFAULT_AWS_REGION)
    parser.add_argument('--quiet', '-q', action='store_true', help="Display more information during installation")
    args = parser.parse_args()

    region = args.region

    print("Generating new AMI for region "+str(region)+" ...")
    try:
        print("  Checking AWS Credentials...")
        aws_key_id, aws_key_secret = get_and_check_aws_credentials(region)
    except Exception:
        sys.stdout.write("Bad AWS credential. Please configure ~/.aws/credentials or "
                         "local_secrets/aws_credentials"+os.linesep)
        sys.stdout.flush()
        return 1

    try:
        with using_ec2(region, aws_key_id, aws_key_secret) as conn:
            try:
                base_ami_id = get_ami_id(conn, AMI_BASE_IMAGE_NAME)
            except RuntimeError as e:
                raise RuntimeError("Unable to get ami with name " + AMI_BASE_IMAGE_NAME + ":" + os.linesep +
                                   "\t" + str(e) + os.linesep +
                                   "Please create one in the region " + region)
        final_ami_id = generate_ami(args.region, aws_key_id, aws_key_secret, base_ami_id, AMI_BASE_IMAGE_SSH_USER,
                                    verbose=not args.quiet)

        print(os.linesep+os.linesep+"==========================================")
        print("AMI generated: " + str(final_ami_id))
        print("=========================================="+os.linesep)
    except (KeyboardInterrupt, SystemExit):
        sys.stderr.write(os.linesep+"Aborted..."+os.linesep)
        sys.stderr.flush()
        return 0
    except Exception as e:
        sys.stderr.write("Unknown error: " + os.linesep + str(e) + os.linesep)
        sys.stderr.flush()
        return 1

    if final_ami_id:
        update_ami_versions(region, final_ami_id)
    return 0


if __name__ == '__main__':
    sys.exit(main())

