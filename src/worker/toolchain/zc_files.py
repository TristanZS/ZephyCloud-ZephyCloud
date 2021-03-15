#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os,sys,subprocess,zipfile, shutil, tempfile, contextlib, logging, distutils.dir_util
from zc_variables import *

ztfold='ZephyTOOLS/'


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


def path(element, *sub_path):
	sub_parts = []
	for part in sub_path:
		sub_parts.extend(part.strip("/").split("/"))
	if sub_parts:
		return os.path.abspath(os.path.join(element.rstrip("/"), *sub_parts))
	else:
		return os.path.abspath(element.rstrip("/"))


def is_string(var):
	"""
	Check if parameter is a string

	:param var:     The variable to test
	:type var:      any
	:return:        True is the variable is a string or unicode
	:rtype:         bool
	"""
	if sys.version_info[0] > 2:
		return isinstance(var, str)
	else:
		return isinstance(var, basestring)


def Extract(zipfilepath,extractiondir):
	archive=zipfile.ZipFile(zipfilepath)
	archive.extractall(path=extractiondir)


def ExtractMainFolder(zip_file, dest_folder):
	"""
	Extract a zip file and return the absoltute path of the extracted folder

	:param zip_file:
	:param dest_folder:
	:return:
	"""
	Extract(zip_file, dest_folder)
	main_folder_name = None
	for filename in os.listdir(dest_folder):
		if os.path.isdir(os.path.join(dest_folder, filename)):
			if not filename or filename.startswith("."):
				continue
			if not main_folder_name:
				main_folder_name = filename
			else:
				raise RuntimeError("To many folders in zip file " + str(zip_file))
	if not main_folder_name:
		raise RuntimeError("No main folder found in zip file " + str(zip_file))
	return os.path.abspath(os.path.join(dest_folder, main_folder_name))


def ZipDir(dirpath, zippath, compression=True):

	if compression is True: fzip=zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED,allowZip64=True)
	else: fzip=zipfile.ZipFile(zippath, 'w', zipfile.ZIP_STORED,allowZip64=True)
	basedir=os.path.dirname(dirpath)+'/'
	for root,_,files in os.walk(dirpath):
		if os.path.basename(root)[0]=='.': continue
		dirname=root.replace(basedir,'')
		for f in files:
			if f[-1]=='~' or f[0]=='.': continue
			fzip.write(root+'/'+f,dirname+'/'+f)
	fzip.close()


def InitFiles(i, filename, ch, codename, log=None):
	if not filename.endswith(".zip"):
		filename += ".zip"
	filename = os.path.abspath(filename)
	if log is None:
		log = logging.getLogger()
	abs_ztfold = os.path.abspath(ztfold)
	log.info("Extracting file " + filename)
	with temp_folder() as tmp_folder:
		extracted_folder = ExtractMainFolder(filename, tmp_folder)
		if not os.path.exists(abs_ztfold):
			try:
				os.makedirs(abs_ztfold)
			except StandardError as e:
				log.warning("Unable to create folder " + str(abs_ztfold) + ": " + str(e))

		for elem in ddin[ch][i]['tree']:
			dest = path(abs_ztfold, elem)
			if not os.path.exists(dest):
				try:
					os.makedirs(dest)
				except StandardError as e:
					log.warning("Unable to create folder " + str(dest) + ": " + str(e))

		for elem in ddin[ch][i]['folders']:
			src = path(extracted_folder, elem)
			try:
				if not os.path.exists(src):
					raise RuntimeError("Unable to find file " + src)
				distutils.dir_util.copy_tree(src, path(abs_ztfold, elem))
			except StandardError as e:
				log.warning("Unable to copy folder " + src + " into " + abs_ztfold + ": " + str(e))

		for elem in ddin[ch][i]['folders_to_projectscfd']:
			src = path(extracted_folder, elem)
			try:
				if not os.path.exists(src):
					raise RuntimeError("Unable to find file " + src)
				distutils.dir_util.copy_tree(src, path(abs_ztfold, 'PROJECTS_CFD', codename, elem))
			except StandardError as e:
				log.warning("Unable to copy folder " + src + " into " + abs_ztfold + ": " + str(e))

		for elem in ddin[ch][i]['files']:
			src = path(extracted_folder, elem)
			dest = path(abs_ztfold, 'PROJECTS_CFD', codename, elem)
			try:
				if not os.path.isfile(src):
					raise RuntimeError("Unable to find file " + src)
				if not os.path.exists(os.path.dirname(dest)):
					os.makedirs(os.path.dirname(dest))
				shutil.copy(src, dest)
			except StandardError as e:
				log.warning("Unable to copy file " + src + " to " + dest + ": " + str(e))

		for elem in ddin[ch][i]['remove']:
			to_remove = path(abs_ztfold, os.path.dirname(extracted_folder), elem)
			try:
				if not os.path.exists(to_remove):
					continue
				if os.path.isdir(to_remove):
					os.remove(to_remove)
				else:
					shutil.rmtree(to_remove)
			except StandardError as e:
				log.warning("Unable to remove " + to_remove + ": " + str(e))

def StoreFiles(codename,ch,jobid, call_args=None):
	if not call_args:
		call_args = {}
	outfolder='%s-%s-%s'%(codename,ch,jobid)
	subprocess.call(['mkdir','-p',outfolder], **call_args)
	for elem in ddout[ch]['tree']:		subprocess.call(['mkdir','-p',outfolder+elem], **call_args)
	for elem in ddout[ch]['folders']:	subprocess.call(['cp','-r',ztfold+'PROJECTS_CFD/'+codename+elem,outfolder], **call_args)
	for elem in ddout[ch]['files']:		subprocess.call(['cp','-r',ztfold+'PROJECTS_CFD/'+codename+'/'+elem,outfolder], **call_args)
	for elem in ddout[ch]['remove']:		subprocess.call(['rm','-f',outfolder+elem], **call_args)
	ZipDir('./%s'%outfolder,outfolder+'.zip')
