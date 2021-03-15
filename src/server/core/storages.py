# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python libs
import abc
import json
import re
import os
import datetime
import shutil
import logging
import tempfile
import contextlib

# Third party libs
# import boto3      # this is imported at runtime
# import botocore   # this is imported at runtime

# Project specific libs
from lib import type_util
from lib import error_util
from lib import file_util
# import lib.ssh    # this is imported at runtime


log = logging.getLogger("aziugo")


class FileMissingError(RuntimeError):
    pass


class Storage(object):
    """
    Main Storage class. This is an abstraction of any way to store a file on cloud
    Note: You may not need to create one, you should retrieve it from a cloud instance
    """
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def unserialize(conf):
        """
        Recreate a Storage instance form it's serialized representation

        :param conf:        A description of the storage, should be generated from storage.serialize
        :type conf:         dict|str
        :return:            A new Storage instance equal to the serialized one
        :rtype:             Storage
        """
        if type_util.is_json(conf):
            conf = json.loads(conf)

        if 'type' not in conf:
            raise RuntimeError("invalid storage config: no type")

        storage_type = conf['type']
        if storage_type == "s3":
            return S3Storage.unserialize(conf)
        elif storage_type == "local_filesystem":
            return LocalFsStorage.unserialize(conf)
        elif storage_type == "ssh":
            return SshStorage.unserialize(conf)
        raise RuntimeError('invalid storage config: unknown storage type '+repr(storage_type))

    @staticmethod
    def load(conf, name):
        """
        Recreate a Storage instance form config file

        :param conf:    A description of the storage
        :type conf:     ConfigParser.ConfigParser
        :param name:    The name of the storage
        :type name:     str
        :return:        A new Storage instance
        :rtype:         Storage
        """
        section = "storage_"+name
        storage_type = conf.get(section, 'type', None)
        if not storage_type:
            raise RuntimeError("invalid storage config: no type")
        if storage_type == "s3":
            return S3Storage.load(conf, name)
        elif storage_type == "local_filesystem":
            return LocalFsStorage.load(conf, name)
        elif storage_type == "ssh":
            raise RuntimeError("Unable to load Ssh storage type from configuration")
        raise RuntimeError('invalid storage config: unknown storage type '+repr(storage_type))

    def __init__(self, name, location):
        """
        :param name:        The name of the storage instance. for example it will be the bucket name of s3
        :type name:         str
        :param location:    The location (example: eu, cn) where the Storage is located
        :type location:     str
        """
        super(Storage, self).__init__()
        self._name = name
        self._location = location

    @property
    def name(self):
        """
        :return:        The name of the storage
        :rtype:         str
        """
        return self._name

    @property
    def location(self):
        """
        :return:        The zone of the storage
        :rtype:         str
        """
        return self._location

    @property
    def type(self):
        """
        :return:        The type of the storage
        :rtype:         str
        """
        raise NotImplementedError("You should implement Storage.type")

    @abc.abstractmethod
    def download_file(self, src_filename, local_dest):
        """
        Download a stored file to local file system

        :param src_filename:        The name of the stored file
        :type src_filename:         str
        :param local_dest:          The destination path where the file will be downloaded
        :type local_dest:           str
        """
        pass

    @abc.abstractmethod
    def get_file_size(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The size, in bytes, of the file. Throw error if it doesn't exists
        :rtype:             int
        """
        pass

    def get_file_creation_date(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The creation date of the file. Throw error if it doesn't exists
        :rtype:             datetime.datetime
        """
        pass

    @abc.abstractmethod
    def get_file_md5(self, filename):
        """
        Get the md5 of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The md5 of the file. Throw error if it doesn't exists
        :rtype:             str
        """
        pass

    @abc.abstractmethod
    def upload_file(self, local_src, dest_filename):
        """
        Upload a local based file to this cloud storage

        :param local_src:           The local path of the file to send to this storage
        :type local_src:            str
        :param dest_filename:       The name of the file on the cloud storage
        :type dest_filename:        str
        :return:                    The url of the file on the cloud storage, if any
        :rtype:                     str|None
        """
        pass

    @abc.abstractmethod
    def file_exists(self, filename):
        """
        Check if a file exists on distant storage

        :param filename:        The name of the file on the cloud storage
        :type filename:         str
        :return:                True if the file exists, False otherwise
        :rtype:                 bool
        """
        pass

    @abc.abstractmethod
    def get_file_url(self, filename):
        """
        Return the url of the file if it can be downloaded, or None otherwise

        :param filename:        The url of the file on the cloud storage, if any
        :type filename:         str|None
        """
        pass

    @abc.abstractmethod
    def delete_file(self, filename):
        """
        Remove a file from distant storage

        :param filename:        The name of the file on the cloud storage
        :type filename:         str
        """
        pass

    @abc.abstractmethod
    def list_files(self):
        """
        List all files on the distant storage

        :return:                A list oof filenames
        :rtype:                 list[str]
        """
        pass

    @abc.abstractmethod
    def serialize(self):
        """
        Generate a string representation so you can recreate the storage using storage_factory.unserialize

        :return:        The configuration of this storage
        :rtype:         str
        """
        return ""

    @contextlib.contextmanager
    def uploading_file(self, local_src, dest_filename):
        """
        Upload the file, yield for whatever you want and remove the file if something went wrong

        :param local_src:           The local path of the file to send to this storage
        :type local_src:            str
        :param dest_filename:       The name of the file on the cloud storage
        :type dest_filename:        str
        :return:                    The url of the file on the cloud storage, if any
        :rtype:                     str|None
        """
        result = self.upload_file(local_src, dest_filename)
        try:
            yield result
        except error_util.all_errors:
            with error_util.before_raising():
                self.delete_file(dest_filename)

    def __eq__(self, other):
        """
        Check Storage equality

        :param other:       Check if it's the same storage
        :type other:        Storage
        :return:            True if the two objects represents the same storage
        :rtype:             bool
        """
        return False

    def __hash__(self):
        """
        Generate a hash for the object

        :return:            The hash of the storage
        :rtype:             int
        """
        return hash(self.serialize())

    def copy_to_storage(self, other_storage, src_filename, dest_filename=None, tmp_folder=None):
        """
        Copy file to another cloud storage.

        :param other_storage:       A cloud storage instance were the file is already present
        :type other_storage:        Storage
        :param src_filename:        The name of the file on the other_storage storage
        :type src_filename          str
        :param dest_filename:       The name of the file will have on current storage. Optional
                                    If not provided, it will be the same has in the source storage
        :type dest_filename:        str|None
        :param tmp_folder:          A folder to use on local machine to work as swap folder
        :type tmp_folder:           str|None
        :return:                    The url of the file on the destination storage, if any
        :rtype:                     str|None
        """
        if dest_filename is None:
            dest_filename = src_filename
        return copy_storage_to_storage(self, src_filename, other_storage, dest_filename, tmp_folder)

    def copy_from_storage(self, other_storage, src_filename, dest_filename=None, tmp_folder=None):
        """
        Copy file from another cloud storage to current storage.

        :param other_storage:       A cloud storage instance were the file is already present
        :type other_storage:        Storage
        :param src_filename:        The name of the file on the other_storage storage
        :type src_filename          str
        :param dest_filename:       The name of the file will have on current storage. Optional
                                    If not provided, it will be the same has in the source storage
        :type dest_filename:        str|None
        :param tmp_folder:          A folder to use on local machine to work as swap folder
        :type tmp_folder:           str|None
        :return:                    The url of the file on the destination storage, if any
        :rtype:                     str|None
        """
        if dest_filename is None:
            dest_filename = src_filename
        return copy_storage_to_storage(other_storage, src_filename, self, dest_filename, tmp_folder)


class LocalFsStorage(Storage):
    """
    Represent an local folder
    """

    @staticmethod
    def unserialize(conf):
        """
        Recreate an S3Storage instance form it's serialized representation
        :param conf:        A description of the storage, should be generated from storage.serialize
        :type conf:         str|dict[str, str]
        :return:            A new FilesystemStorage instance equal to the serialized one
        :rtype:             LocalFsStorage
        """
        if type_util.is_json(conf):
            conf = json.loads(conf)

        for param in ('name', 'path', 'location'):
            if param not in conf:
                raise RuntimeError("invalid storage config: no "+param+" parameter")
        if conf['type'] != 'local_filesystem':
            msg = "invalid filesystem config: type should be 'local_filesystem', but is actually "+repr(conf['type'])
            raise RuntimeError(msg)
        return LocalFsStorage(conf['name'], conf['path'], conf['location'])

    @staticmethod
    def load(conf, name):
        """
        Recreate a Storage instance form config file

        :param conf:    A description of the storage
        :type conf:     ConfigParser.ConfigParser
        :param name:    The name of the storage
        :type name:     str
        :return:        A new Storage instance
        :rtype:         LocalFsStorage
        """
        section = "storage_" + name
        path = conf.get(section, 'path')
        location = conf.get(section, 'location')
        return LocalFsStorage(name, path, location)

    def __init__(self, name, path, location):
        """
        :param name:                    The storage name
        :type name:                     str
        :param path:                    The folder path where to store data
        :type path:                     str
        :param location:                The location (example: eu, cn) where the Storage is located
        :type location                  str
        """
        super(LocalFsStorage, self).__init__(name, location)
        self._path = path
        if not os.path.exists(path):
            os.makedirs(path)

    @property
    def type(self):
        """
        :return:        The type of the storage
        :rtype:         str
        """
        return "local_filesystem"

    @property
    def path(self):
        """
        :return:        The storage folder path
        :rtype:         str
        """
        return self._path

    def download_file(self, src_filename, local_dest):
        """
        Download a stored file to local file system

        :param src_filename:        The name of the stored file
        :type src_filename:         str
        :param local_dest:          The destination path where the file will be downloaded
        :type local_dest:           str
        """
        src_filename = src_filename.lstrip("/")
        shutil.copy(os.path.join(self._path, src_filename), local_dest)

    def upload_file(self, local_src, dest_filename):
        """
        Upload a local based file to this cloud storage

        :param local_src:           The local path of the file to send to this storage
        :type local_src:            str
        :param dest_filename:       The name of the file on the cloud storage
        :type dest_filename:        str
        :return:                    Always None for local files
        :rtype:                     str|None
        """
        dest_filename = dest_filename.lstrip("/")
        full_dest_dir = os.path.join(self._path, os.path.dirname(dest_filename))
        if not os.path.exists(full_dest_dir):
            os.makedirs(full_dest_dir)
        shutil.copy(local_src, os.path.join(self._path, dest_filename))

    def file_exists(self, filename):
        """
        Check if a file exists on distant storage

        :param filename:        The name of the file on the cloud storage
        :type filename:         str
        :return:                True if the file exists, False otherwise
        :rtype:                 bool
        """
        return os.path.exists(os.path.join(self.path, filename.lstrip("/")))

    def get_file_url(self, filename):
        """
        Return the url of the file if it can be downloaded, or None otherwise

        :param filename:        The file name
        :type filename:         str
        :return:                Always None for local files
        :rtype:                 str|None
        """
        return None

    def delete_file(self, filename):
        """
        Remove a file from distant storage

        :param filename:        The name of the file on the cloud storage
        :type filename:         str
        """
        file_path = os.path.join(self.path, filename.lstrip("/"))
        if os.path.exists(file_path):
            os.remove(file_path)

    def get_file_size(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The size, in bytes, of the file. Throw error if it doesn't exists
        :rtype:             int
        """
        if not os.path.exists(os.path.join(self.path, filename.lstrip("/"))):
            raise FileMissingError("file "+str(filename)+" doesn't exists")
        return int(os.stat(os.path.join(self.path, filename.lstrip("/"))).st_size)

    def get_file_creation_date(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The creation date of the file. Throw error if it doesn't exists
        :rtype:             datetime.datetime
        """
        if not os.path.exists(os.path.join(self.path, filename.lstrip("/"))):
            raise FileMissingError("file "+str(filename)+" doesn't exists")
        stats = os.stat(os.path.join(self.path, filename.lstrip("/")))
        creation_time = stats.st_ctime
        modification_time = stats.st_mtime
        if modification_time > 0 and (creation_time == 0 or modification_time < creation_time):
            return datetime.datetime.utcfromtimestamp(modification_time)
        return datetime.datetime.utcfromtimestamp(creation_time)

    def get_file_md5(self, filename):
        """
        Get the md5 of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The md5 of the file. Throw error if it doesn't exists
        :rtype:             str
        """
        if not os.path.exists(os.path.join(self.path, filename.lstrip("/"))):
            raise FileMissingError("file "+str(filename)+" doesn't exists")
        return file_util.md5sum(os.path.join(self.path, filename.lstrip("/")))

    def list_files(self):
        """
        List all files on the distant storage

        :return:                A list oof filenames
        :rtype:                 list[str]
        """
        return [f for f in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, f))]

    def serialize(self):
        """
        Generate a string representation so you can recreate the storage using storage_factory.unserialize

        :return:        The configuration of this storage
        :rtype:         str
        """
        return json.dumps({'type': self.type, 'name': self.name, 'location': self.location, 'path': self.path})

    def __eq__(self, other):
        """
        Check Storage equality

        :param other:       Check if it's the same storage
        :type other:        Storage
        :return:            True if the two objects represents the same storage
        :rtype:             bool
        """
        if not isinstance(other, LocalFsStorage):
            return False
        if self.location != other.location:
            return False
        if self.path != other.path:
            return False
        return True


class S3Storage(Storage):
    """
    Represent an S3 Bucket
    """

    MULTIPART_LIMIT = 104857600
    __bucket_cache = {}

    @staticmethod
    def unserialize(conf):
        """
        Recreate an S3Storage instance form it's serialized representation
        :param conf:        A description of the storage, should be generated from storage.serialize
        :type conf:         str|dict[str]
        :return:            A new S3Storage instance equal to the serialized one
        :rtype:             S3Storage
        """
        if type_util.is_json(conf):
            conf = json.loads(conf)

        for param in ('type', 'bucket', 'path', 'location', 'region', 'access_key_id', 'access_key_secret', 'expire'):
            if param not in conf:
                raise RuntimeError("invalid storage config: no "+param+" parameter")
        if conf['type'] != 's3':
            raise RuntimeError("invalid s3storage config: type should be 's3', but is actually '"+str(conf['type'])+"'")
        return S3Storage(conf['bucket'], conf['path'], conf['location'], conf['region'], conf['access_key_id'],
                         conf['access_key_secret'], conf['expire'])

    @staticmethod
    def load(conf, name):
        """
        Recreate a Storage instance form config file
        :param conf:        A description of the storage
        :type conf:         ConfigParser.ConfigParser
        :param name:        The name of the storage
        :type name:         str
        :return:            A new Storage instance
        :rtype:             S3Storage
        """
        matches = re.match(r'^s3_(.*)$', name)
        if not matches:
            raise RuntimeError("Invalid s3 storage name "+name)

        section = "storage_" + name
        location = matches.group(1)

        api_name = conf.get('general', 'api_name')
        server_name = conf.get('general', 'server')
        path = api_name+"/"+server_name

        region = conf.get(section, 'aws_region')
        if not region:
            region = conf.get("asw_default", 'aws_region', None)
        bucket = conf.get(section, 'bucket', None)
        if not bucket:
            bucket = conf.get("asw_default", 'bucket')
        access_key_id = conf.get(section, 'access_key_id')
        access_key_secret = conf.get(section, 'access_key_secret')
        expire = conf.get(section, 'link_expire_delay', None)
        if not expire:
            expire = conf.get("asw_default", 'link_expire_delay', 0)
        return S3Storage(bucket, path, location, region, access_key_id, access_key_secret, int(expire))

    def __init__(self, bucket_name, path, location, aws_region, access_key_id, access_key_secret, expire=0):
        """
        :param bucket_name:             The bucket name
        :type bucket_name:              str
        :param path:                    The path inside the bucket
        :type path:                     str
        :param location:                The location (example: eu, cn) where the Storage is located
        :type location:                 str
        :param aws_region:              The aws region (example: 'cn-north-1') where the Storage is located
        :type aws_region:               str
        :param access_key_id:           The access key identifier of the IAM account who will access the bucket
        :type access_key_id:            str
        :param access_key_secret:       The access key secret of the IAM account who will access the bucket
        :type access_key_secret:        str
        :param expire:                  The link expiration limit, in seconds. Optional, default 0
        :type expire:                   int
        """
        super(S3Storage, self).__init__('s3_'+location, location)
        self._bucket_name = bucket_name
        self._path = path
        self._aws_region = aws_region
        self._key_id = access_key_id
        self._key_secret = access_key_secret
        self._expire_delay = expire
        self._conn = None
        self._anonymous_conn = None

    @property
    def type(self):
        """
        :return:        The type of the storage
        :rtype:         str
        """
        return "s3"

    @property
    def path(self):
        """
        Get the folder on s3 bucket

        :return:        The folder path
        :rtype:         str
        """
        return self._path

    def download_file(self, src_filename, local_dest):
        """
        Download a stored file to local file system

        :param src_filename:        The name of the stored file
        :type src_filename:         str
        :param local_dest:          The destination path whre the file will be downloaded
        :type local_dest:           str
        """
        full_src = self._get_s3_filename(src_filename)
        self.bucket.Object(full_src).download_file(local_dest)

    @property
    def conn(self):
        """
        Get the resource object corresponding to the s3 storage credentials

        :return:            The AWS S3 Resource object
        :rtype:             boto3.resources.factory.s3.ServiceResource
        """
        import boto3

        if self._conn is None:
            self._conn = boto3.resource("s3", region_name=self.aws_region, aws_access_key_id=self._key_id,
                                        aws_secret_access_key=self._key_secret)
        return self._conn

    @property
    def bucket(self):
        """
        Get the bucket where we push and get files

        :return:        The bucket object
        :rtype:         boto3.resources.factory.s3.Bucket
        """
        return self.conn.Bucket(self.bucket_name)

    def upload_file(self, local_src, dest_filename=None):
        """
        Upload a local based file to this cloud storage

        :param local_src:           The local path of the file to send to this storage
        :type local_src:            src
        :param dest_filename:       The name of the file on the cloud storage. Optional, default None
        :type dest_filename:        str|None
        :return:                    The url of the file on the cloud storage, if any
        :rtype:                     str|None
        """
        if not dest_filename:
            dest_filename = os.path.basename(local_src)
        full_dest = self._get_s3_filename(dest_filename)
        if self._expire_delay == 0:
            self.bucket.upload_file(local_src, full_dest, ExtraArgs={'ACL': 'public-read'})
            # object_acl = self.conn.ObjectAcl(self.bucket_name, full_dest)
            # object_acl.put(ACL='public-read')
        return self.get_file_url(dest_filename)

    def file_exists(self, filename):
        """
        Check if a file exists on distant storage

        :param filename:        The name of the file on the cloud storage
        :type filename:         str
        :return:                True if the file exists, False otherwise
        :rtype:                 bool
        """
        full_filename = self._get_s3_filename(filename)
        results = list(self.bucket.objects.limit(1).filter(Prefix=full_filename))
        if len(results) == 0:
            return False
        return results[0].key == full_filename

    def get_file_url(self, filename):
        """
        Return the url of the file if it can be downloaded, or None otherwise

        :param filename:        The url of the file on the cloud storage, if any
        :type filename:         str|None
        :return:                The url of the file if found
        :rtype:                 bool|str
        """
        full_filename = self._get_s3_filename(filename)
        params = {'Bucket': self.bucket_name, 'Key': full_filename}
        if self._expire_delay == 0:
            return self.anonymous_conn.generate_presigned_url('get_object', ExpiresIn=0, Params=params)
        else:
            return self.conn.meta.client.generate_presigned_url('get_object', ExpiresIn=self._expire_delay,
                                                                Params=params)

    def delete_file(self, filename):
        """
        Remove a file from distant storage

        :param filename:        The name of the file on the cloud storage
        :type filename:         str
        """
        if not self.file_exists(filename):
            return
        full_filename = self._get_s3_filename(filename)
        self.bucket.delete_objects(Delete={"Objects": [{"Key": full_filename}]})

    def get_file_size(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The size, in bytes, of the file. Throw error if it doesn't exists
        :rtype:             int
        """
        if not self.file_exists(filename):
            raise FileMissingError("file " + str(filename) + " doesn't exists")
        full_filename = self._get_s3_filename(filename)
        return int(self.bucket.Object(full_filename).content_length)

    def get_file_creation_date(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The creation date of the file. Throw error if it doesn't exists
        :rtype:             datetime.datetime
        """
        if not self.file_exists(filename):
            raise FileMissingError("file " + str(filename) + " doesn't exists")
        full_filename = self._get_s3_filename(filename)
        return self.bucket.Object(full_filename).last_modified

    def get_file_md5(self, filename):
        """
        Get the md5 of a file
        WARNING: may not work for big files

        :param filename:    The name of the file
        :type filename:     str
        :return:            The md5 of the file. Throw error if it doesn't exists
        :rtype:             str
        """
        if not self.file_exists(filename):
            raise FileMissingError("file " + str(filename) + " doesn't exists")
        full_filename = self._get_s3_filename(filename)
        return self.bucket.Object(full_filename).etag[1:-1]

    def list_files(self):
        """
        List all files on the distant storage

        :return:                A list of file names
        :rtype:                 list[str]
        """
        result = []
        prefix = self.path + "/" if self.path else ''
        for obj in self.bucket.objects.filter(Prefix=prefix):
            result.append(str(obj.key)[len(prefix):])
        return result

    def serialize(self):
        """
        Generate a string representation so you can recreate the storage using storage_factory.unserialize

        :return:            The configuration of this storage
        :rtype:             str
        """
        return json.dumps({'type': 's3',
                           'bucket': self.bucket_name,
                           'path': self.path,
                           'location': self.location,
                           'region': self.aws_region,
                           'access_key_id': self._key_id,
                           'access_key_secret': self._key_secret,
                           'expire': self._expire_delay})

    @property
    def bucket_name(self):
        """
        :return:        The name of bucket
        :rtype:         str
        """
        return self._bucket_name

    @property
    def aws_region(self):
        """
        :return:        The name of the s3 region (for example 'cn-north-1')
        :rtype:         str
        """
        return self._aws_region

    @property
    def anonymous_conn(self):
        """
        Return the url of the file if it can be downloaded, or None otherwise

        :return:                The url of the file if found
        :rtype:                 botocore.client.S3
        """
        import boto3
        import botocore.client

        if self._anonymous_conn is None:
            config = botocore.client.Config()
            config.signature_version = botocore.UNSIGNED
            self._anonymous_conn = boto3.client("s3", region_name="eu-west-1", config=config)
        return self._anonymous_conn

    def _get_s3_filename(self, filename):
        """
        Get the path on the destination bucket

        :param filename:            The file name
        :type filename:             str
        :return:                    The full path on the bucket
        :rtype:                     str
        """
        if self._path:
            return self.path.rstrip("/") + "/" + filename
        else:
            return filename

    def __eq__(self, other):
        """
        Check Storage equality

        :param other:       Check if it's the same storage
        :type other:        Storage|S3Storage|Any
        :return:            True if the two objects represents the same storage
        :rtype:             bool
        """
        if not isinstance(other, S3Storage):
            return False
        if self.location != other.location:
            return False
        if self.aws_region != other.aws_region:
            return False
        if self.bucket_name != other.bucket_name:
            return False
        if self.path != other.path:
            return False
        return True


class SshStorage(Storage):
    @staticmethod
    def unserialize(conf):
        import lib.ssh

        if type_util.is_json(conf):
            conf = json.loads(conf)

        for param in ('type', 'conn', 'client_path', 'trusted'):
            if param not in conf:
                raise RuntimeError("invalid storage config: no "+param+" parameter")
        if conf['type'] != 'ssh':
            raise RuntimeError("invalid SshStorage config: type should be 'ssh', but it's '"+repr(conf['type'])+"'")
        conn = lib.ssh.SshConnection.unserialize(conf['conn'])

        return SshStorage(conn, conf['client_path'], conf['trusted'])

    def __init__(self, conn, client_path, trusted=False):
        """
        Create the ssh storage

        :param conn:            The connection to client
        :type conn:             lib.ssh.SshConnection
        :param client_path:     The path on the distant machine
        :type client_path:      str
        :param trusted:         Are we sure of the toolchain running on the client ? Optional, default False
        :type trusted:          bool

        """
        super(SshStorage, self).__init__("ssh_storage_" + conn.client_ip, conn.client_ip)
        self._conn = conn
        self._path = client_path
        self._trusted = trusted

    @property
    def conn(self):
        return self._conn

    @property
    def path(self):
        return self._path

    @property
    def trusted(self):
        return self._trusted

    @property
    def type(self):
        return "ssh"

    def delete_file(self, filename):
        self._conn.run(["rm", "-f", os.path.join(self._path, filename)])

    def file_exists(self, filename):
        return self._conn.file_exists(os.path.join(self._path, filename))

    def download_file(self, src_filename, local_dest):
        self._conn.get_file(os.path.join(self._path, src_filename), local_dest)

    def upload_file(self, local_src, dest_filename):
        self._conn.send_file(local_src, os.path.join(self._path, dest_filename))

    def get_file_url(self, filename):
        return None

    def get_file_size(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The size, in bytes, of the file. Throw error if it doesn't exists
        :rtype:             int
        """
        if not self._conn.file_exists(os.path.join(self._path, filename)):
            raise FileMissingError("file "+str(filename)+" doesn't exists")
        return self._conn.get_file_size(os.path.join(self._path, filename))

    def get_file_creation_date(self, filename):
        """
        Get the name of a file

        :param filename:    The name of the file
        :type filename:     str
        :return:            The creation date of the file. Throw error if it doesn't exists
        :rtype:             datetime.datetime
        """
        if not self._conn.file_exists(os.path.join(self._path, filename)):
            raise FileMissingError("file "+str(filename)+" doesn't exists")
        return self._conn.get_file_creation_date(os.path.join(self._path, filename))

    def get_file_md5(self, filename):
        """
        Get the md5 of a file
        WARNING: may not work for big files

        :param filename:    The name of the file
        :type filename:     str
        :return:            The md5 of the file. Throw error if it doesn't exists
        :rtype:             str
        """
        if not self._conn.file_exists(os.path.join(self._path, filename)):
            raise FileMissingError("file "+str(filename)+" doesn't exists")
        return self._conn.get_file_md5(os.path.join(self._path, filename))

    def list_files(self):
        """
        List all files on the distant storage

        :return:                A list oof filenames
        :rtype:                 list[str]
        """
        code, out, err = self.conn.run(['find', self.path, "-maxdepth", "1", "-type", "f", "-print", '%f\\n'])
        return out.strip().splitlines()

    def serialize(self):
        return json.dumps({'type': 'ssh',
                           'conn': self._conn.serialize(),
                           'client_path': self._path,
                           'trusted': self._trusted})

    def __eq__(self, other):
        """
        Compare two storages

        :param other:   The other storage to compare with
        :type other:    SshStorage|Storage|any
        :return:        True if 'other' param is equivalent to this one
        :rtype:         bool
        """
        if not isinstance(other, SshStorage):
            return False
        if self._path != other.path:
            return False
        if self._trusted != other.trusted:
            return False
        if self._conn != other.conn:
            return False
        return True


def copy_storage_to_storage(src_store, src_filename, dest_store, dest_filename, tmp_folder=None):
    """
    Copy file from another cloud storage to current storage.

    :param src_store:           A cloud storage instance were the file is already present
    :type src_store:            Storage
    :param src_filename:        The name of the file on the src_store storage
    :type src_filename          str
    :param dest_store:          A cloud storage instance were the will be copied
    :type dest_store:           Storage
    :param dest_filename:       The name of the file will have on destination storage. Optional
                                If not provided, it will be the same has in the source storage
    :type dest_filename:        str
    :param tmp_folder:          A folder to use on local machine to work as swap folder
    :type tmp_folder:           str|None
    :return:                    The url of the file on the destination storage, if any
    :rtype:                     str|None
    """
    if not tmp_folder:
        tmp_folder = tempfile.gettempdir()

    # The file is already there
    if src_store == dest_store and src_filename == dest_filename:
        if src_store.type == "s3":
            return src_store.get_file_url(dest_filename)
        else:
            return  # nothing to do

    # The destination and source are on the local disk, so simple os copy works
    if src_store.type == "local_filesystem" and dest_store.type == "local_filesystem":
        full_src = os.path.abspath(os.path.join(src_store.path, src_filename.lstrip("/")))
        full_dest = os.path.abspath(os.path.join(dest_store.path, dest_filename.lstrip("/")))
        if full_src == full_dest:
            return  # Same file, Nothing to do
        full_dest_dir = os.path.dirname(full_dest)
        if not os.path.exists(full_dest_dir):
            os.makedirs(full_dest_dir)
        shutil.copy(full_src, full_dest)
        return

    # Aws copy bucket to bucket
    if src_store.type == "s3" and dest_store.type == "s3":
        if src_store.aws_region == dest_store.aws_region:  # Same region
            full_src = src_store._get_s3_filename(src_filename)
            full_dest = dest_store._get_s3_filename(dest_filename)
            new_obj = dest_store.conn.Object(dest_store.bucket_name, full_dest)
            new_obj.copy_from(CopySource={'Bucket': src_store.bucket_name, 'Key': full_src})
            if dest_store._expire_delay == 0:
                object_acl = dest_store.conn.ObjectAcl(dest_store.bucket_name, full_dest)
                object_acl.put(ACL='public-read')
            return dest_store.get_file_url(dest_filename)

    # The destination and source are on the same ssh client, so we run a copy cmd through ssh
    if src_store.type == "ssh" and dest_store.type == "ssh":
        if src_store.conn.client_ip == dest_store.conn.client_ip:
            full_src = os.path.abspath(os.path.join(src_store.path, src_filename.lstrip("/")))
            full_dest = os.path.abspath(os.path.join(dest_store.path, dest_filename.lstrip("/")))
            if full_src == full_dest:
                return  # Same file, Nothing to do
            if src_store.conn.client_user == dest_store.conn.client_user:
                src_store.conn.run(["cp", "-f", full_src, full_dest])
            else:
                src_store.conn.run(["cp", "-f", full_src, full_dest], as_user=dest_store.conn.client_user)

    # We copy to local so no temp swapping copy is required
    if dest_store.type == "local_filesystem":
        full_dest = os.path.abspath(os.path.join(dest_store.path, dest_filename.lstrip("/")))
        src_store.download_file(src_filename, full_dest)
        return

    # We copy from local so no temp swapping copy is required
    if src_store.type == "local_filesystem":
        full_src = os.path.abspath(os.path.join(src_store.path, src_filename.lstrip("/")))
        dest_store.upload_file(full_src, dest_filename)
        return

    # Really common case, so here an optimized version
    if src_store.type == "ssh" and dest_store.type == "s3":
        full_src = os.path.abspath(os.path.join(src_store.path, src_filename.lstrip("/")))
        full_dest = dest_store._get_s3_filename(dest_filename)
        if src_store.trusted:
            cmd = "export AWS_ACCESS_KEY_ID='"+dest_store._key_id+"' && "
            cmd += "export AWS_SECRET_ACCESS_KEY='"+dest_store._key_secret+"' && "
            cmd += "aws '--region='"+dest_store.aws_region+" s3 cp '"+full_src+"' "
            cmd += "'s3://"+dest_store.bucket_name+"/"+full_dest+"'"
            src_store.conn.run(cmd, shell=True)
            if not dest_store.file_exists(dest_filename):
                raise RuntimeError("upload to s3 failed")
            if dest_store._expire_delay == 0:
                object_acl = dest_store.conn.ObjectAcl(dest_store.bucket_name, full_dest)
                object_acl.put(ACL='public-read')
            return dest_store.get_file_url(dest_filename)
        else:
            log.debug("SAM: using SSH proxy for upload")
            bucket = dest_store.bucket.object()
            with src_store.conn.read_file_pipe(full_src) as fh:
                bucket.Object(full_dest).upload_fileobj(fh)
            return dest_store.get_file_url(dest_filename)

    # Rely common case, so here an optimized version
    if src_store.type == "s3" and dest_store.type == "ssh":
        full_src = src_store._get_s3_filename(src_filename)
        full_dest = os.path.abspath(os.path.join(dest_store.path, dest_filename.lstrip("/")))
        if dest_store.trusted:
            full_src = src_store.path + "/" + src_filename if src_store.path else src_filename
            src_path = "s3://" + src_store.bucket_name + "/" + full_src
            cmd = "export AWS_ACCESS_KEY_ID='"+src_store._key_id+"' && "
            cmd += "export AWS_SECRET_ACCESS_KEY='"+src_store._key_secret+"' && "
            cmd += "aws '--region='"+src_store.aws_region+" s3 cp '"+src_path+"' '"+full_dest+"'"
            dest_store.conn.run(cmd, shell=True)
            if not dest_store.file_exists(dest_filename):
                raise RuntimeError("upload to ssh failed")
            return
        else:
            log.debug("SAM: using SSH proxy for download")
            s3_file = src_store.bucket.Object(full_src)
            with dest_store.conn.send_file_pipe(full_dest) as fh:
                s3_file.upload_fileobj(fh)
            return

    log.debug("SAM: default tranfert: "+str(src_store.type)+" to "+str(dest_store.type))
    # Generic case: download to a temporary folder and then push up to the new store
    with file_util.temp_filename(dir=tmp_folder) as tmp_filename:
        src_store.download_file(src_filename, tmp_filename)
        dest_store.upload_file(tmp_filename, dest_filename)
