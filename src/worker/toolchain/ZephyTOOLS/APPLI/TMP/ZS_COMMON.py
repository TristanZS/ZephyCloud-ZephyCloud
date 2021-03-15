#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ZS_VARIABLES import *

from math import gamma,modf
import pandas as pd
from scipy import interpolate
import zipfile,struct,glob,socket,simplekml,shlex
try:
	from osgeo import ogr,osr
except: pass
from shapely import ops as ops
import shapely.geometry as geometry
import requests
import urllib3
import slumber
import shutil,calendar, tempfile, contextlib, re
import copy,pickle,platform,stat, threading
import re,gettext


try: import DNS
except: DNS=False

TURN_LEFT,TURN_RIGHT,TURN_NONE=(1,-1,0)


class DebugOutput:
	_indent_levels = {}
	
	@staticmethod
	def context(description):
		return DebugOutput._DebugContext(description)
	
	@staticmethod
	def echo(content):
		thread_id =  DebugOutput._get_threadid()
		if thread_id not in DebugOutput._indent_levels.keys():
			DebugOutput._indent_levels[thread_id] = 0
		sys.stderr.write("DEBUG %-10s:%s%s" % (thread_id, "  "*DebugOutput._indent_levels[thread_id], content))
		sys.stderr.write(os.linesep)
		sys.stderr.flush()
		
	@staticmethod
	def _get_threadid():
		return str(os.getpid())+"#"+str(threading.current_thread().ident)

	class _DebugContext:
		def __init__(self, description):
			self._description = description
		
		def __enter__(self):
			thread_id = DebugOutput._get_threadid()
			if thread_id not in DebugOutput._indent_levels.keys():
				DebugOutput._indent_levels[thread_id] = 0
			DebugOutput.echo(self._description)
			DebugOutput._indent_levels[thread_id] += 1

		def __exit__(self, exc_type, exc_val, exc_tb):
			thread_id = DebugOutput._get_threadid()
			DebugOutput._indent_levels[thread_id] -= 1
			DebugOutput.echo("END " + self._description)
		
	

def UnixSanitizeStr(var, to_unicode=False):
	if to_unicode and isinstance(var, str):
		var = var.decode('utf-8')
	else:
		var = str(var)
	return var.replace("\r\n", "\n").replace("\r", "\n").strip()


def ExtractZip(zipfilepath,extractiondir):
	archive=zipfile.ZipFile(zipfilepath)
	archive.extractall(path=extractiondir)

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

def ExtractZipMainFolder(zip_file, dest_folder, overwrite=True):
	"""
	Extract a zip file and return the absolute path of the extracted folder

	:param zip_file:
	:param dest_folder:
	:return:
	"""
	with temp_folder() as tmp_folder:
		try: ExtractZip(zip_file, tmp_folder)
		except:
			print("Error ExtractZipMainFolder:")
			print(traceback.format_exc())
			return False
		main_folder_name = None
		for filename in os.listdir(tmp_folder):
			if os.path.isdir(os.path.join(tmp_folder, filename)):
				if not filename or filename.startswith("."):
					continue
				if not main_folder_name:
					main_folder_name = filename
				else:
					raise RuntimeError("To many folders in zip file " + str(zip_file))
		if not main_folder_name:
			raise RuntimeError("No main folder found in zip file " + str(zip_file))
		generated_folder = os.path.abspath(os.path.join(dest_folder, main_folder_name))
		if overwrite and os.path.exists(generated_folder):
			shutil.rmtree(generated_folder)
		shutil.move(os.path.join(tmp_folder, main_folder_name), dest_folder)
	return generated_folder


def RecursiveRenaming(path, text, replacement):
	"""
	Do file/folder name text replacement in a folder and all its sub-folders

	:param path:				The folder to look for
	:type path:					str
	:param text:				The text to replace
	:type text:					str
	:param replacement:			The replacement text
	:type replacement:			str
	"""
	basename = os.path.basename(path)
	if text in basename:
		new_path = os.path.join(os.path.dirname(path), basename.replace(text, replacement))
		shutil.move(path, new_path)
		path = new_path

	if os.path.isdir(path):
		for filename in os.listdir(path):
			RecursiveRenaming(os.path.join(path, filename), text, replacement)

def UrlToFilename(url, permissive=True):
	"""
	Get a clean file name from a download url 
	This function works for python2 and 3 but is not rock solid for special filenames
	
	:param url: 			The url of the file
	:type url:				str
	:param permissive:		Do we allow special characters in filename ? Optional, default True
	:type permissive:		bool
	:return: 				A usable and clean filename
	:rtype:					str
	"""
	if sys.version_info[0] == 2:
		import urllib
		
		base_filename = basename(url)
		if "?" in base_filename:
			base_filename = base_filename.split("?", 1)[0]
		
		filename = urllib.unquote_plus(base_filename).strip()
	else:
		import urllib.parse

		base_filename = basename(url)
		if "?" in base_filename:
			base_filename = base_filename.split("?", 1)[0]

		filename = urllib.parse.unquote_plus(base_filename).strip()

	if permissive:
		filename = re.sub(r'(?u)[^-\w._ @]', '_', filename)
	else:
		filename = re.sub(r'[^-\w._]', '_', filename)
	return filename

def CloudDownload(server_name,url,folder=None,rename=[],app='wget'):
	"""
	Downloads a file from ZephyCloud
	
	:param url:		the url to download from
	:type url:		str
	:param folder:	the folder where to save the file, defaults to APPLI/EXTERN/CLOUD/
	:type folder:	str
	:param rename:	list of arguments to rename the folder recursively; Optional, default None
	:type rename:	list|None
	:param app:		the program to use for download, defaults to wget
	:type app:		str
	"""
	if rename is None:
		rename = []

	if folder==None: folder=PATH+'../../APPLI/EXTERN/CLOUD/'
	outfile=os.path.join(folder, UrlToFilename(url))
	
	if app=='wget':
		command="wget -O '"+str(outfile)+"' -c --read-timeout=60"
		nlines='2'
	elif app=='curl':
		command="curl -o '"+str(outfile)+"' -C - "
		nlines='4'
	else:
		raise ValueError('unsupported program {} for download'.format(app))
	
	if "ZEPHYCLOUD_SERVER" in os.environ and os.environ["ZEPHYCLOUD_SERVER"]:
		server_name=os.environ["ZEPHYCLOUD_SERVER"]
	if server_name in url and "ZEPHYCLOUD_CA_ROOT" in os.environ and os.environ["ZEPHYCLOUD_CA_ROOT"]:
		if app=='wget': command += " --certificate="+os.environ["ZEPHYCLOUD_CA_ROOT"]+" "
		elif app=='curl': command+=" --cacert '"+os.environ["ZEPHYCLOUD_CA_ROOT"]+"' "
	
	command+=" '"+str(url)+"'"
	text='ZephyTOOLS - Data Download - Please do not close'
	subprocess.call(['xterm','-title',text,'-geometry','90x'+nlines,'-bg','#222222','-fg','#727375','-e',command])

	try:
		path=ExtractZipMainFolder(outfile,folder)
		if not path:
			return False
	except:
		print("Error CloudDownload:")
		print(traceback.format_exc())
		return False
	
	subprocess.call(['rm','-f',outfile])
	
	if len(rename)==2:
		RecursiveRenaming(path,rename[0],rename[1])
		path=path.replace(rename[0],rename[1])
	
	return path
	
def CloudUpdateProcesses(api):
	"""
	Updates the xml files in QUEUE by calling the ZephyCloud API
	"""
	
	if api==None: return
	
	try: jobs=api.jobs.list.post({'order':'job_id DESC'})
	except (StandardError,api.connection_error):
		print('ERROR in CloudUpdateProcesses:')
		traceback.print_exc()
		return
	
	Jobs=jobs[0:min(len(jobs),250)]
	
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			rootcloud=xml.parse(xmlfilecloud).getroot()
			OK=True
		except: time.sleep(0.1)
	if not OK:
		sys.stderr.write('Failed to parse xmlfilecloud\n')
		sys.stderr.flush()
		return
	
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			rootended=xml.parse(xmlfileended).getroot()
			OK=True
		except: time.sleep(0.1)
	if not OK:
		sys.stderr.write('Failed to parse xmlfileended\n')
		sys.stderr.flush()
		return
	
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			rootold=xml.parse(xmlfileold).getroot()
			OK=True
		except: time.sleep(0.1)
	if not OK:
		sys.stderr.write('Failed to parse xmlfileold\n')
		sys.stderr.flush()
		return
	
	FINISHED=False
	
	toremove=[]
	for balcloud in rootcloud:
		
		status=balcloud.attrib['status']
		code=balcloud.attrib['code']
		codename=balcloud.attrib['codename']
		site=balcloud.attrib['site']
		name=balcloud.attrib['name']
		idjob=balcloud.attrib['idjob']
		username=balcloud.attrib['username']
		time2use=balcloud.attrib['time']
		
		new_status='-'
		new_progress='-'
		new_ncoins='-'
		new_start='-'
		new_end='-'
		
		
		FOUND=False
		for job in Jobs:
			if int(job['job_id'])==int(idjob):
				try: new_status=job['status']
				except: new_status='-'
				try: new_progress=str(job['progress'])
				except: new_progress='-'
				try: new_ncoins=str(job['ncoins'])
				except: new_ncoins='-'
				try: new_start='%.2f'%calendar.timegm(time.strptime(job['start'],"%Y/%m/%d-%H:%M"))
				except: new_start='-'
				try: new_end='%.2f'%calendar.timegm(time.strptime(job['end'],"%Y/%m/%d-%H:%M"))
				except: new_end='-'
				FOUND=True
				break
		
		if not FOUND: continue
		
		if new_status in ['pending','launching','running']:

			balcloud.attrib['status']=new_status
			balcloud.attrib['start']=new_start
			balcloud.attrib['progress']=str(new_progress)
			balcloud.attrib['ncoins']=str(new_ncoins)
		
		elif new_status in ['finished','canceled','killed']:
			
			toremove.append(balcloud)
			
			if new_status=='finished':
				newbal=xml.SubElement(rootended,'process')
			elif new_status in ['canceled','killed']:
				newbal=xml.SubElement(rootold,'process')
			
			newbal.attrib['time']=time2use
			newbal.attrib['code']=code
			newbal.attrib['codename']=codename
			newbal.attrib['name']=name
			newbal.attrib['site']=site
			newbal.attrib['idjob']=idjob
			newbal.attrib['status']=new_status
			newbal.attrib['progress']=new_progress
			newbal.attrib['start']=new_start
			newbal.attrib['end']=new_end
			newbal.attrib['duration']='-'
			newbal.attrib['username']=username
			newbal.attrib['ncoins']=new_ncoins
			
			FINISHED=True
		
		else:
			
			sys.stderr.write('Unknown status: %s\n'%(status))
			sys.stderr.flush()
			continue
	
	for balcloud in toremove:
		rootcloud.remove(balcloud)
	
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			xml.ElementTree(rootcloud).write(xmlfilecloud)
			OK=True
		except: time.sleep(0.1)
	if not OK:
		sys.stderr.write('Failed to update xmlfilecloud\n')
		sys.stderr.flush()
		
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			xml.ElementTree(rootold).write(xmlfileold)
			OK=True
		except: time.sleep(0.1)
	if not OK:
		sys.stderr.write('Failed to update xmlfileold\n')
		sys.stderr.flush()
		
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			xml.ElementTree(rootended).write(xmlfileended)
			OK=True
		except: time.sleep(0.1)
	if not OK:
		sys.stderr.write('Failed to update xmlfileended\n')
		sys.stderr.flush()
		
	return FINISHED
		
def CloudGetProcess(job_id):
	job_id=str(job_id)
	rootcloud=xml.parse(xmlfilecloud).getroot()
	rootended=xml.parse(xmlfileended).getroot()
	rootold=xml.parse(xmlfileold).getroot()
	
	for balcloud in rootcloud:
		bal_idjob=balcloud.attrib.get('idjob')
		if bal_idjob==job_id:
			return balcloud.attrib['codename']
	for balcloud in rootended:
		bal_idjob=balcloud.attrib.get('idjob')
		if bal_idjob==job_id:
			return balcloud.attrib['codename']
	for balcloud in rootold:
		bal_idjob=balcloud.attrib.get('idjob')
		if bal_idjob==job_id:
			return balcloud.attrib['codename']
	return "not found"
	
def CloudSendToOld(codes,sitename,codename=None):
	FOUND=False
	it,OK=0,False
	while it<10 and not OK:
		it+=1
		try:
			root=xml.parse(xmlfileended).getroot()
			OK=True
		except: time.sleep(0.1)
	for bal in root:
		if bal.attrib['code'] in codes and bal.attrib['site']==sitename \
		and (codename==None or bal.attrib['codename']==codename):
			root.remove(bal)
			FOUND=True
			break
	if not FOUND:
		print("ERROR CloudSendToOld: process not in Cloud-Ended list")
		return
	it,OK=0,False
	while it<10 and not OK:
		it+=1
		try:
			xml.ElementTree(root).write(xmlfileended)
			OK=True
		except: time.sleep(0.1)
	it,OK=0,False
	while it<10 and not OK:
		it+=1
		try:
			root=xml.parse(xmlfileold).getroot()
			OK=True
		except: time.sleep(0.1)
	newbal=xml.SubElement(root,'process')
	newbal.attrib['code']=bal.attrib['code']
	newbal.attrib['codename']=bal.attrib['codename']
	newbal.attrib['duration']='%.2f'%(eval(bal.attrib['end'])-eval(bal.attrib['start']))
	newbal.attrib['end']=bal.attrib['end']
	newbal.attrib['name']=bal.attrib['name']
	newbal.attrib['site']=bal.attrib['site']
	newbal.attrib['start']=bal.attrib['start']
	newbal.attrib['status']='ok'
	newbal.attrib['username']=bal.attrib['username']
	newbal.attrib['idjob']=bal.attrib['idjob']
	newbal.attrib['ncoins']=bal.attrib['ncoins']
	newbal.attrib['time']=bal.attrib['time']
	it,OK=0,False
	while it<10 and not OK:
		it+=1
		try:
			xml.ElementTree(root).write(xmlfileold)
			OK=True
		except: time.sleep(0.1)
	return

def CloudDownloadAnal(sitename,api,cloudname):
	
	res=api.project.status.post({'project_codename':cloudname})
	if res['project_status']!='analysed':
		raise ValueError('cloud project is not analysed')
	url=res['project_url']
	if url==None:
		raise ValueError('api request did not return a download url')
	
	dirname=PATH+'../../PROJECTS_CFD/'+sitename
	path=CloudDownload(api.server,url,rename=[cloudname,sitename])
	if not path: raise RuntimeError("Error with downloaded file, please try again")
	
	for elem in ddout['anal']['folders']: subprocess.call(['cp','-rf',path+elem,dirname])
	for elem in ddout['anal']['files']: subprocess.call(['cp',path+'/'+elem,dirname])
	
	xmlfile=dirname+'/ANALYSE/analyses.xml'
	root=xml.parse(xmlfile).getroot()
	for bal in root:
		if bal.attrib['state']=='Cloud-Ended':
			bal.attrib['state']='Ready'
			size='%.3f'%(GetFolderSize(dirname+'/ANALYSE/'+sitename+'_'+bal.attrib['name'])/1.e+6)
			bal.attrib['size']=size
			xml.ElementTree(root).write(xmlfile)
			break
	root=xml.parse(xmlfilecfdprojects).getroot()
	for bal in root:
		if bal.text==sitename:
			bal.attrib['analysed']=bal.attrib['analysed'].replace('-Cloud','')
			xml.ElementTree(root).write(xmlfilecfdprojects)
			break 
	subprocess.call(['rm','-rf',path])

	CloudSendToOld(['cfd_cloud_anal'],sitename)

def CloudDownloadMesh(sitename,api,cloudname,meshname,files='preview'):
	if files not in ['preview','all']:
		raise ValueError('files must be either "preview" or "all"')
	
	url_prev=None
	url_data=None
	
	res=api.mesh.show.post({'project_codename':cloudname,'mesh_name':meshname})
	if res['status']!='computed': print 'not possible'
	else:
		url_prev=res['preview_url']
		url_data=res['mesh_data_url']
	
	if (files=='preview' and url_prev!=None) or (files=='all' and url_data!=None):
		
		dirname=PATH+'../../PROJECTS_CFD/'+sitename
		codename=sitename+'_'+meshname
		
		if files=='preview':
			path=CloudDownload(api.server,url_prev,rename=[cloudname,sitename])
			if not path: raise RuntimeError("Error with downloaded file, please try again")
			
			subprocess.call(['cp','-rf',path+'/FILES',dirname+'/MESH/'+codename])
			subprocess.call(['cp','-f',path+'/param.xml',dirname+'/MESH/'+codename])
			subprocess.call(['rm','-rf',path])
		
		elif files=='all':
			path=CloudDownload(api.server,url_data,rename=[cloudname,sitename])
			if not path: raise RuntimeError("Error with downloaded file, please try again")
			
			for elem in ddout['mesh']['folders']: subprocess.call(['cp','-rf',path+elem,dirname])
			subprocess.call(['rm','-rf',path])
		
		root=xml.parse(dirname+'/MESH/'+codename+'/param.xml')
		ncells=root.find('ncells_fine').text
		reso=root.find('resfine').text
		
		size='%.1f'%(GetFolderSize(dirname+'/MESH/'+codename)/1.e+6)
		xmlfile=dirname+'/MESH/meshes.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.attrib['name']==meshname and bal.attrib['state']=='Cloud-Ended':
				if files=='all':
					bal.attrib['state']='Ready'
				bal.attrib['ncells']=ncells
				bal.attrib['size']=size
				xml.ElementTree(root).write(xmlfile)
				break
		
		if files=='all':
			STILL=False
			root=xml.parse(xmlfile).getroot()
			for bal in root:
				if bal.attrib['state']=='Cloud-Ended':
					STILL=True
					break
			if not STILL:
				root=xml.parse(xmlfilecfdprojects).getroot()
				for bal in root:
					if bal.text==sitename:
						bal.attrib['meshed']=bal.attrib['meshed'].replace('-Cloud','')
						xml.ElementTree(root).write(xmlfilecfdprojects)
						break
		
		bal2use=None
		xmlfileprev=dirname+'/USER/cfd_mesh01/previews.xml'
		rootprev=xml.parse(xmlfileprev).getroot()
		for balprev in rootprev:
			if balprev.text==meshname:
				bal2use=balprev
				break
		if bal2use==None:
			bal2use=xml.SubElement(rootprev,'mesh')
			bal2use.text=meshname
		bal2use.attrib['ncells']=str(ncells)
		bal2use.attrib['reso']='%.1f'%float(reso)
		xml.ElementTree(rootprev).write(xmlfileprev)
		
		CloudSendToOld(['cfd_cloud_mesh01','cfd_cloud_mesh02'],sitename,codename)
	
def CloudDownloadCalc(sitename,api,cloudname,calcname,restart=False,extract=False):
	
	url_res=None
	url_iter=None
	url_reduced=None
	
	res=api.calculation.show.post({'project_codename':cloudname,'calculation_name':calcname.replace(sitename,cloudname)})
	if res['status'] not in ['computed','stopped']: print calcname+': calculation is still running'
	else:
		url_res=res['result_url']
		url_iter=res['iterations_url']
		url_reduced=res['reduce_url']
	
	if url_res!=None or (restart and url_iter!=None) or (extract and url_reduced!=None):
		
		dirname=PATH+'../../PROJECTS_CFD/'+sitename
		path=CloudDownload(api.server,url_res,rename=[cloudname,sitename])
		if not path: raise RuntimeError("Error with downloaded file, please try again")
		
		for elem in ddout['calc']['folders']: subprocess.call(['cp','-rf',path+elem,dirname])
		subprocess.call(['rm','-rf',path])
		
		if restart:
			path=CloudDownload(api.server,url_iter,rename=[cloudname,sitename])
			if not path: raise RuntimeError("Error with downloaded file, please try again")
			
			for elem in ddout['calc']['folders']: subprocess.call(['cp','-rf',path+elem,dirname])
			subprocess.call(['rm','-rf',path])
		
		if extract:
			path=CloudDownload(api.server,url_reduced,rename=[cloudname,sitename])
			if not path: raise RuntimeError("Error with downloaded file, please try again")
			
			for elem in ddout['calc']['folders']: subprocess.call(['cp','-rf',path+elem,dirname])
			subprocess.call(['rm','-rf',path])
		
		xmlfile=dirname+'/CALC/calculations.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.text==calcname:
				
				has_restart=restart
				has_extract=extract
				if bal.attrib['state']=='Ready':
					cleanstate=bal.attrib['clean']
					if cleanstate=='No restart':has_extract=True
					elif cleanstate=='No extract':has_restart=True
					elif cleanstate=='No':has_restart,has_extract=True,True
				
				infofile=dirname+'/CALC/'+calcname+'/info.xml'
				inforoot=xml.parse(infofile).getroot()
				balinfo=inforoot.find('cvg')
				if balinfo.find('cvg_rate_res').text not in ['none','0.0']:	bal.attrib['state']='Ready'
				else:													bal.attrib['state']='Diverged'
				bal.attrib['cvg']=balinfo.find('cvg_rate_res').text
				bal.attrib['size']='%.1f'%(GetFolderSize(dirname+'/CALC/'+bal.text)/1.e+6)
				
				if not has_restart and not has_extract:	bal.attrib['clean']='Clear'
				elif has_restart and not has_extract:	bal.attrib['clean']='No extract'
				elif not has_restart and has_extract:	bal.attrib['clean']='No restart'
				elif has_restart and has_extract:		bal.attrib['clean']='No'
				break
		xml.ElementTree(root).write(xmlfile)
		
		xmlfile=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.text==sitename:
				bal.attrib['calculated']=bal.attrib['calculated'].replace('-Cloud','')
				if 'No' in bal.attrib['calculated']:
					bal.attrib['calculated']=string.replace(bal.attrib['calculated'],'No','Yes')
				bal.attrib['size']='%.1f'%(GetFolderSize(dirname)/1.e+6)
				xml.ElementTree(root).write(xmlfile)
				break
		
		CloudSendToOld(['cfd_cloud_calc01','cfd_cloud_calc02'],sitename,calcname)

def VerifProcess():
	"""
	Verifies the running processes
	"""

	EXIST=False
	REMOVED=False
	root=xml.parse(xmlfileproc).getroot()
	for bal in root:
		if bal.attrib['priority']!='-1':
			try:
				process=bal.attrib['time']
				EXIST=FindProcess(process)
				if not EXIST:
					REMOVED=True
					root.remove(bal)
			except: pass
	if REMOVED: xml.ElementTree(root).write(xmlfileproc)
	
def VerifIndividualStates(xmlfile,time2use=None):
	"""
	Updates a process register (e.g. calculations.xml, meshes.xml) by checking the xml files in QUEUE
	"""
	iscalc = os.path.basename(xmlfile)=='calculations.xml'
	
	it,OK=0,False
	while it<10 and not OK:
		it+=1
		try:
			root=xml.parse(xmlfile).getroot()
			rootproc=xml.parse(xmlfileproc).getroot()
			rootcloud=xml.parse(xmlfilecloud).getroot()
			rootqueue=xml.parse(xmlfilequeue).getroot()
			rootend=xml.parse(xmlfileended).getroot()
			OK=True
		except: time.sleep(0.1)
	if not OK: return False
	
	def verif_cloud(bal2use):
		OKRUN,OKEND=False,False
		progress=None
		for bal in rootcloud:
			if bal.attrib['time']==bal2use.attrib['time2use']:
				OKRUN=True
				progress='%.1f'%(100.*float(bal.attrib['progress']))
				break
		if OKRUN: bal2use.attrib['state']='Cloud-Running'
		else:
			for bal in rootend:
				if bal.attrib['time']==bal2use.attrib['time2use']:
					OKEND=True
					progress='%.1f'%(100.*float(bal.attrib['progress']))
					break
			if OKEND:
				bal2use.attrib['state']='Cloud-Ended'
				if bal2use.tag!='analyse': bal2use.attrib['iscloud']='Yes'
			else:
				bal2use.attrib['state']='Killed'
		if iscalc and progress!=None:
			bal2use.attrib['cvg']=progress
	
	for bal2use in root:
		if time2use!=None and time2use!=bal2use.attrib['time2use']: continue
		
		if bal2use.attrib['state']=='Queued':
			OK,OKRUN=False,False
			for bal in rootqueue:
				if bal.attrib['time']==bal2use.attrib['time2use']:
					OK=True
					break
			if not OK:
				for bal in rootproc:
					if bal.attrib['time']==bal2use.attrib['time2use']:
						OKRUN=True
						break
				if OKRUN:	bal2use.attrib['state']='Running'
				else:
					bal2use.attrib['state']='Killed'
					
		elif bal2use.attrib['state']=='Running':
			OK=False
			for bal in rootproc:
				if bal.attrib['time']==bal2use.attrib['time2use']:
					OK=True
					break
			if not OK:
				bal2use.attrib['state']='Killed'
				
		elif bal2use.attrib['state']=='Cloud-Queued':
			OK=False
			for bal in rootqueue:
				if bal.attrib['time']==bal2use.attrib['time2use']:
					OK=True
					break
			if not OK:
				for bal in rootproc:
					if bal.attrib['time']==bal2use.attrib['time2use']:
						OK=True
						break
			if not OK:
				verif_cloud(bal2use)
		
		elif bal2use.attrib['state'] in ['Cloud-Waiting','Cloud-Running']:
			verif_cloud(bal2use)
	
	it,OK=0,False
	while it<10 and not OK:
		it+=1
		try:
			xml.ElementTree(root).write(xmlfile)
			OK=True
		except: time.sleep(0.1)
	if not OK: return False
	
	return True
	
def UpdateProgress(time2use,ithread,val,text):
	try:
		xmlfile = PATH + '../../APPLI/TMP/logout_' + time2use + '_' + str(ithread) + '.xml'
	except Exception as e:
		print("Error UpdateProgress: {}".format(e))
		return
	try:
		root=xml.parse(xmlfile).getroot()
		root.find('progress_text').text=UnixSanitizeStr(text, to_unicode=True)
		root.find('progress_frac').text=str(min(val,1.))
		xml.ElementTree(root).write(xmlfile,encoding="UTF-8",xml_declaration=False)
	except Exception as e:
		print("Error UpdateProgress of {}: {}".format(xmlfile,e))


class TimeoutError(RuntimeError):
	pass


def DNSResolve(domain, timeout=None):
	"""
	Try to resolve given domain into ip address using DNS call first and then calling system method
	
	:param domain:      The domain to resolve
	:type domain:       str
	:param timeout:     Timeout to give up resolution, in seconds. Optional Default None
						If timeout is less than 2, only DNS method is used, not system one.
	:type timeout:      int|None
	:return:            The domain if found, else None
	:rtype:             str|None
	"""
	try:
		signal.signal(signal.SIGALRM, dns_timeout)
		signal.alarm(1)
		if DNS:
			DNS.ParseResolvConf()
			r=DNS.DnsRequest(name=domain, qtype='A')
			a=r.req()
			if a==None:
				print 'DNS request failed using DNS method'
				return None
			if a.answers:
				return a.answers[0]['data']
	except TimeoutError:
		if timeout and timeout == 1:
			print 'DNS lookup timeout for domain '+str(domain) + ' using DNS method!'
			return None
	finally:
		signal.alarm(0)
		
	if timeout:
		signal.signal(signal.SIGALRM, dns_timeout)
		signal.alarm(timeout - 1 if DNS else timeout)
	try:
		try:
			return socket.gethostbyname(domain)
		except:
			print 'DNS request failed using OS method for '+domain
			return None
	except TimeoutError:
		print 'DNS lookup timeout for domain ' + str(domain) + ' using OS method!'
		return None
	finally:
		if timeout:
			signal.alarm(0)
	

def dns_timeout(a, b):
	raise TimeoutError()


def canIHasIP(domain_name, timeout=3):
	return DNSResolve(domain_name, timeout) is not None


def CheckDir(strPath,strSubPath=None):
	"""
	Checks if a directory exists,
	if not, it will be created
	"""
	
	if strSubPath is not None: strPath=os.path.join(strPath,strSubPath)
	if not os.path.isdir(strPath):
		try: os.makedirs(strPath)
		except: pass
	return strPath

def GetVersion():

	with open(PATH+'../../COMMON/version','r') as f: lines=f.readlines()
	version_num=lines[0].rstrip()
	version_text='<b>ZephyTOOLS</b>\n'+lines[1].rstrip()+' v.'+version_num+'\n© Zephy-Science 2012'
	software_name='ZephyTOOLS'
	return version_num,version_text,software_name

def GetOnline(server):
	"""
	Returns internet connectivity status
	"""

	if "ZEPHYCLOUD_SERVER" in os.environ and os.environ["ZEPHYCLOUD_SERVER"]: server=os.environ["ZEPHYCLOUD_SERVER"]
	return canIHasIP(server)!=False

def GetTime(i=0):
	"""
	Returns reduced cpu time in str
	"""

	return ('%.2f'%(time.time()+i))[6:]

def GetLongTime():
	"""
	Returns reduced cpu time in str
	"""

	return ('%.2f'%time.time())

class STOPWATCH():
	def __init__(self):
		self.reset()
	def time(self,text='time'):
		print(text+": {0:.2f}ms".format((time.time()-self.t0)*1000))
	def split(self,text='time'):
		t=time.time()
		print(text+": {0:.2f}ms".format((t-self.t)*1000))
		self.t=t
	def reset(self):
		self.t0=time.time()
		self.t=self.t0
	
class LAYOUT:
	
	def __init__(self):
		
		self.xcentre=0.
		self.ycentre=0.
		self.diamin=0.
		
		self.centres=[]
		
		self.n_point=0
		self.labels_point=[]
		self.plots_point=[]
		self.diams_point=[]
		self.point_x=[]
		self.point_y=[]
		self.point_h=[]
		self.point_label=[]
		self.point_label_plot=[]

		self.n_wt=0
		self.labels_wt=[]
		self.plots_wt=[]
		self.diams_wt=[]
		self.wt_x=[]
		self.wt_y=[]
		self.wt_group=[]
		self.wt_label=[]
		self.wt_label_plot=[]

		self.n_mast=0
		self.labels_mast=[]
		self.plots_mast=[]
		self.diams_mast=[]
		self.mast_x=[]
		self.mast_y=[]
		self.mast_label=[]
		self.mast_label_plot=[]

		self.n_lidar=0
		self.labels_lidar=[]
		self.plots_lidar=[]
		self.diams_lidar=[]
		self.lidar_x=[]
		self.lidar_y=[]
		self.lidar_angle=[]
		self.lidar_label=[]
		self.lidar_label_plot=[]

		self.n_meso=0
		self.labels_meso=[]
		self.plots_meso=[]
		self.diams_meso=[]
		self.meso_x=[]
		self.meso_y=[]
		self.meso_dia=[]
		self.meso_label=[]
		self.meso_label_plot=[]

		self.n_mapping=0
		self.labels_mapping=[]
		self.plots_mapping=[]
		self.diams_mapping=[]
		self.mapping_x1=[]
		self.mapping_x2=[]
		self.mapping_y1=[]
		self.mapping_y2=[]
		self.mapping_res=[]
		self.mapping_h=[]
		self.mapping_dia=[]
		self.mapping_label=[]
		self.mapping_label_plot=[]
		self.mapping_xc=[]
		self.mapping_yc=[]
		self.mapping_rad=[]

		self.n_usermap=0
		self.labels_usermap=[]
		self.plots_usermap=[]
		self.diams_usermap=[]
		self.usermap_x=[]
		self.usermap_y=[]
		self.usermap_res=[]
		self.usermap_label=[]
		self.usermap_label_plot=[]

		self.heights=[]
		
		self.contours=[]
		
		self.list_group=[]
		self.ISGROUP=False

	def Init(self, name):
		
		self.__init__()
		
		try:
			with open(PATH+'../../PROJECTS_CFD/'+name+'/centre','r') as f: self.zcentre=eval(f.readline())
		except: self.zcentre=0.

		
		xmlfile=PATH+'../../PROJECTS_CFD/'+name+'/site.xml'
		root=xml.parse(xmlfile).getroot()
		self.xcentre=eval(root.find('xcentre').text)
		self.ycentre=eval(root.find('ycentre').text)
		self.diamin=eval(root.find('diamin').text)

		xmlfile=PATH+'../../PROJECTS_CFD/'+name+'/DATA/data.xml'
		root=xml.parse(xmlfile).getroot()

		self.n_point		= eval(root.find('n_point').text)
		self.n_wt			= eval(root.find('n_wt').text)
		self.n_mast			= eval(root.find('n_mast').text)
		self.n_lidar		= eval(root.find('n_lidar').text)
		self.n_meso			= eval(root.find('n_meso').text)
		self.n_mapping		= eval(root.find('n_mapping').text)
		self.n_usermap		= eval(root.find('n_usermap').text)
		self.heights		= eval(root.find('heights').text)
		
		if self.n_point>0:
			infile=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/zspoint', 'r')
			ANALYSED=False
			try:
				infile2=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/elevations_point', 'r')
				ANALYSED=True
			except: pass
			i=0
			while i<self.n_point:
				values=infile.readline().split()
				if ANALYSED: height=eval(infile2.readline().split()[2])
				else: height=80.
				self.point_x.append(eval(values[0]))
				self.point_y.append(eval(values[1]))
				self.point_h.append(eval(values[2]))
				self.point_label.append(values[3])
				self.point_label_plot.append([self.point_label[i], True, True])
				self.centres.append([eval(values[0]), eval(values[1]), 1000., 'point', height])
				self.labels_point.append(True)
				self.plots_point.append(True)
				self.diams_point.append(True)
				i+=1
			infile.close()
			if ANALYSED: infile2.close()

		if self.n_wt>0:
			infile=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/zswt', 'r')
			ANALYSED=False
			try:
				infile2=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/elevations_wt', 'r')
				ANALYSED=True
			except: pass
			i=0
			while i<self.n_wt:
				values=infile.readline().split()
				if ANALYSED: height=eval(infile2.readline().split()[2])
				else: height=80.
				self.wt_x.append(eval(values[0]))
				self.wt_y.append(eval(values[1]))
				self.wt_label.append(values[2])
				self.wt_group.append(values[3])
				self.wt_label_plot.append([self.wt_label[i], True, True])
				self.centres.append([eval(values[0]), eval(values[1]), 1000., 'wt', height])
				self.labels_wt.append(True)
				self.plots_wt.append(True)
				self.diams_wt.append(True)
				i+=1
			infile.close()
			if ANALYSED: infile2.close()
			
			self.list_group=[]
			for group in self.wt_group:
				if group not in self.list_group: self.list_group.append(group)
			self.ISGROUP=len(self.list_group)>1

		if self.n_mast>0:
			infile=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/zsmast', 'r')
			ANALYSED=False
			try:
				infile2=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/elevations_mast', 'r')
				ANALYSED=True
			except: pass
			i=0
			while i<self.n_mast:
				values=infile.readline().split()
				if ANALYSED: height=eval(infile2.readline().split()[2])
				else: height=80.
				self.mast_x.append(eval(values[0]))
				self.mast_y.append(eval(values[1]))
				self.mast_label.append(values[2])
				self.mast_label_plot.append([self.mast_label[i], True, True])
				self.centres.append([eval(values[0]), eval(values[1]), 1000., 'mast', height])
				self.labels_mast.append(True)
				self.plots_mast.append(True)
				self.diams_mast.append(True)
				i+=1
			infile.close()
			if ANALYSED: infile2.close()

		if self.n_lidar>0:
			infile=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/zslidar', 'r')
			ANALYSED=False
			try:
				infile2=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/elevations_lidar', 'r')
				ANALYSED=True
			except: pass
			i=0
			while i<self.n_lidar:
				values=infile.readline().split()
				if ANALYSED: height=eval(infile2.readline().split()[2])
				else: height=80.
				self.lidar_x.append(eval(values[0]))
				self.lidar_y.append(eval(values[1]))
				self.lidar_angle.append(eval(values[2]))
				self.lidar_label.append(values[3])
				self.lidar_label_plot.append([self.lidar_label[i], True, True])
				self.centres.append([eval(values[0]), eval(values[1]), 1000., 'lidar', height])
				self.labels_lidar.append(True)
				self.plots_lidar.append(True)
				self.diams_lidar.append(True)
				i+=1
			infile.close()
			if ANALYSED: infile2.close()

		if self.n_meso>0:
			infile=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/zsmeso', 'r')
			i=0
			while i<self.n_meso:
				values=infile.readline().split()
				self.meso_x.append(eval(values[0]))
				self.meso_y.append(eval(values[1]))
				self.meso_dia.append(eval(values[3]))
				self.meso_label.append(values[5])
				self.meso_label_plot.append([self.meso_label[i], True, True])
				self.centres.append([eval(values[0]), eval(values[1]), eval(values[3]), 'meso'])
				self.labels_meso.append(True)
				self.plots_meso.append(True)
				self.diams_meso.append(True)
				i+=1
			infile.close()

		if self.n_mapping>0:
			infile=open(PATH+'../../PROJECTS_CFD/'+name+'/DATA/zsmapping', 'r')
			i=0
			while i<self.n_mapping:
				values=infile.readline().split()
				self.mapping_x1.append(eval(values[0]))
				self.mapping_x2.append(eval(values[1]))
				self.mapping_y1.append(eval(values[2]))
				self.mapping_y2.append(eval(values[3]))
				self.mapping_res.append(eval(values[4]))
				self.mapping_h.append(eval(values[5]))
				self.mapping_dia.append(eval(values[6]))
				self.mapping_label.append(values[7])
				self.mapping_label_plot.append([self.mapping_label[i], True, True])
				self.mapping_xc.append((self.mapping_x1[i]+self.mapping_x2[i])/2.)
				self.mapping_yc.append((self.mapping_y1[i]+self.mapping_y2[i])/2.)
				dist=sqrt((self.mapping_xc[i]-self.mapping_x1[i])**2+(self.mapping_yc[i]-self.mapping_y1[i])**2)
				self.mapping_rad.append(dist)
				self.centres.append([self.mapping_xc[i], self.mapping_yc[i], 2*self.mapping_rad[i], 'mapping'])
				self.labels_mapping.append(True)
				self.plots_mapping.append(True)
				self.diams_mapping.append(True)
				i+=1
			infile.close()

		if self.n_usermap>0:
			pass

def WeibullCalcMoment(fv,vedges=None):
	if vedges is None:# 1/ms bins
		vedges = range(len(fv)+1)
	
	A=-999.
	k=-999.
	
	vm=0.
	vs=0.
	ft=0.
	for iv,fvi in enumerate(fv):
		v=vedges[iv]+(vedges[iv+1]-vedges[iv])/2.
		val=np.log(v)
		vm+=fvi*val
		vs+=fvi*val*val
		ft+=fvi
	vs-=vm*vm
	if vs>0:
		vs=np.sqrt(vs)
		A=np.exp(vm + np.euler_gamma*(sqrt(6)/np.pi) * vs)
		k=np.pi/(sqrt(6)*vs)
		
	return [A,k]

def WeibullCalcLeast(fv,vedges=None):
	if vedges is None:# 1/ms bins
		vedges = range(len(fv)+1)
	
	ftot=np.sum(fv)
	
	nval=0
	fcum=0.
	xm=0.
	ym=0.
	for iv,fvi in enumerate(fv):
		fcum+=fvi
		if fcum<=ftot-0.0001 and fcum>0 and 1-fcum>0:
			nval+=1
			v=vedges[iv]+(vedges[iv+1]-vedges[iv])/2.
			xi=np.log(v)
			yi=np.log(-np.log(1-fcum))
			xm+=fvi*xi
			ym+=fvi*yi
	if nval==0: return -999.,-999.
	
	fcum=0.
	sumdxdx=0.
	sumdxdy=0.
	for iv,fvi in enumerate(fv):
		fcum+=fvi
		if fcum<=ftot-0.0001 and fcum>0 and 1-fcum>0:
			v=vedges[iv]+(vedges[iv+1]-vedges[iv])/2.
			xi=np.log(v)
			yi=np.log(-np.log(1-fcum))
			sumdxdx+=(xi-xm)**2
			sumdxdy+=(xi-xm)*(yi-ym)
	if sumdxdx==0.: return -999.,-999.
	
	slope = max(1., sumdxdy / sumdxdx)
	b = ym-slope*xm
	
	k=slope
	A=np.exp(-b/slope)
	
	return [A,k]

def WeibullCalcMaxlike(fv,vedges=None):
	if vedges is None:# 1/ms bins
		vedges = range(len(fv)+1)
	
	def Iterate(liste_AA,liste_kk,A,k,problogmax):
		
		for AA in liste_AA:
			for kk in liste_kk:
				expinf=1.0
				problog=0.0
				for iv,fvi in enumerate(fv):
					expsup=np.exp(-(vedges[iv+1]/AA)**kk)
					prob=expinf-expsup
					expinf=expsup
					if prob>0: problog+=fvi*np.log(prob)
					else: break
				if problog>problogmax:
					problogmax=problog
					A =AA
					k =kk
		
		return A,k,problogmax
	
	vm=0.
	for iv,fvi in enumerate(fv):
		v=vedges[iv]+(vedges[iv+1]-vedges[iv])/2.
		vm+=fvi*v
	
	A=-999.
	k=-999.
	problogmax=-9.e25
	
	liste_AA=np.arange(round(vm/2.,0),round(vm*2.,0),0.5)
	liste_kk=np.arange(1.0,3.0,0.2)
	A,k,problogmax=Iterate(liste_AA,liste_kk,A,k,problogmax)
	liste_AA=np.arange(A-0.5,A+0.5,0.1)
	liste_kk=np.arange(k-0.2,k+0.2,0.1)
	A,k,problogmax=Iterate(liste_AA,liste_kk,A,k,problogmax)
	liste_AA=np.arange(A-0.1,A+0.1,0.01)
	liste_kk=np.arange(k-0.1,k+0.1,0.01)
	A,k,problogmax=Iterate(liste_AA,liste_kk,A,k,problogmax)
	
	return [A,k]

def WeibullCalcEnergy(fv,vedges=None):
	if vedges is None:# 1/ms bins
		vedges = range(len(fv)+1)
	
	def Iterate(liste_kk):

		for kk in liste_kk:
			if np.exp(-(vm/((m3/gamma(1+3/kk))**(1./3.)))**kk)>fdepvmoy:
				k=kk
				break
		return k
		
	vm=0
	m3=0.
	for iv,fvi in enumerate(fv):
		v=vedges[iv]+(vedges[iv+1]-vedges[iv])/2.
		vm+=fvi*v
		m3+=fvi*v**3
	
	fdepvmoy=0.
	for iv,fvi in enumerate(fv):
		v=vedges[iv]+(vedges[iv+1]-vedges[iv])/2.
		if v>vm: fdepvmoy+=fvi
	
	try:
		liste_kk=np.arange(0.5,8.0,0.5)
		k=Iterate(liste_kk)
		liste_kk=np.arange(k-0.5,k+0.5,0.1)
		k=Iterate(liste_kk)
		liste_kk=np.arange(k-0.1,k+0.1,0.01)
		k=Iterate(liste_kk)
		A=(m3/gamma(1+3/k))**(1./3.)
	except:
		A=-999.
		k=-999.

	return [A,k]

def WeibullCalcMeans(weibulls):
	
	m=0.
	m3=0.
	liste_v=np.arange(0.,200,0.01)
	tot=0
	for v in liste_v:
		f=(weibulls[0]/weibulls[1])*((v/weibulls[0])**(weibulls[1]-1))*np.exp(-(v/weibulls[0])**weibulls[1])
		tot+=f
		m+=v*f
		m3+=(v**3)*f
	
	return m/tot,m3/tot

def WeibullAverage(weibulls):

	return weibulls[0]*gamma(1+1/weibulls[1])


def ListPid(): return [int(x) for x in os.listdir('/proc') if x.isdigit()]

def ListChildrens(pid): return [int(c) for c in os.listdir('/proc/%s/task' % pid)]

def Pid2Name(pid):
	try:
		with open("/proc/%s/stat" % pid) as f:
			return f.read().split()[1].replace('(', '').replace(')', '')
	except: pass

def Pid2Command(pid):
	try:
		with open("/proc/%s/cmdline" % pid) as f:
			return f.read()
	except: pass

def Pid2CmdArgs(pid):
	cmd = Pid2Command(pid)
	if not cmd:
		return cmd
	result = []
	for arg in shlex.split(cmd):
		result.extend(arg.rstrip("\x00").split("\x00"))
	return result

def FindProcess(proc_name):
	if proc_name is None: return False
	for pid in ListPid():
		cmd_args = Pid2CmdArgs(pid)
		if not cmd_args:
			continue
		if Pid2Name(pid)==proc_name or proc_name in map(os.path.basename,cmd_args[0:2]):
			process=psutil.Process(pid)
			try:
				if process.memory_info()[0]==0:
					return False
			except: return False
			return True
	return False

def KillProcess(proc_name, is_script=False):

	for pid in ListPid():
		cmd_args = Pid2CmdArgs(pid)
		if not cmd_args:
			continue
		if Pid2Name(pid)==proc_name or  proc_name in map(os.path.basename, cmd_args[0:2]):
			process=psutil.Process(pid)
			for proc in process.children(recursive=True):
				try: proc.kill()
				except: pass
			process.kill()

def KillCommand(proc_name):
	
	for pid in ListPid():
		command=Pid2Command(pid)
		if command is not None:
			if proc_name in command:
				process=psutil.Process(pid)
				try: process.kill()
				except: pass

def GetSubprocessPids(proc_name, subproc_name):
	parent_pids = []
	for pid in ListPid():
		cmd_args = Pid2CmdArgs(pid)
		if not cmd_args:
			continue
		if Pid2Name(pid)==proc_name or proc_name in map(os.path.basename, cmd_args[0:2]):
			parent_pids.append(pid)
			
	results = []
	for parent_pid in parent_pids:
		process = psutil.Process(parent_pid)
		for subproc in process.children(recursive=True):
			try:
				cmd_args = Pid2CmdArgs(subproc.pid)
				if not cmd_args:
					continue
				if Pid2Name(subproc.pid) == subproc_name or subproc_name in map(os.path.basename, cmd_args[0:2]):
					results.append(subproc.pid)
			except: pass
	return results


def ListDirectory(path):
	fichier=[]
	l=glob.glob(path+'/*')
	for i in l:
		if os.path.isdir(i): fichier.extend(ListDirectory(i))
		else: fichier.append(i)
	return fichier

def CleanTmp():
	
	print 'Cleaning TMP folder...'
	
	processes=[]
	
	xmlfile=PATH+'../../APPLI/QUEUE/processes'
	root=xml.parse(xmlfile).getroot()
	for bal in root:
		try:	processes.append(bal.attrib['time'])
		except:	pass

	for elem in ListDirectory(PATH+'../../APPLI/TMP'):
		if basename(elem) not in ['ZS_VARIABLES.pyc','ZS_COMMON.pyc','ZT_GUI.pyc']:
			if basename(elem)[-4:]!='.xml' and basename(elem)[0:5]!='table':
				if basename(elem) not in processes:
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/_'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/__'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/___'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/____'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/_____'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/______'+basename(elem)])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/logout_'+basename(elem)+'.xml'])
					subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/'+basename(elem)+'.xml'])

	print 'Done'

def ZipDir(dirpaths, zippath, compression=True, log_progress=False):
	"""
	Zip one or several directories and their content.
	
	:param dirpaths:			path to a directory, or list of paths to several directories
	:type dirpaths:				str or list
	:param zippath:				destination path
	:type zippath:				str
	:param compression:			Whether to use compression or not
	:type compression:			bool
	:param log_process			Optional callback function to run when monitoring progress,
								with the progress as a float between 0 and 1 as argument
	:type log_process			func(float)|bool
	"""
	
	if isinstance(dirpaths, basestring): dirpaths=[dirpaths]
	if compression is True: fzip=zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED,allowZip64=True)
	else: fzip=zipfile.ZipFile(zippath, 'w', zipfile.ZIP_STORED,allowZip64=True)
	
	#Prepare log
	if log_progress:
		
		#Get total data size in bytes so we can report on progress
		total = 0.
		for path in dirpaths:
			for root,_dirs,files in os.walk(path):
				if os.path.basename(root)[0]=='.': continue
				for f in files:
					if f[-1]=='~' or f[0]=='.': continue
					total += os.path.getsize(os.path.join(root,f))
		
		t_updlast = time.time()
		t_delta = 3.
		t_update = t_updlast + t_delta
		current = 0.
	
	#Archive
	for path in dirpaths:
		basedir=os.path.dirname(path)+'/' 
		for root,_dirs,files in os.walk(path):
			
			try:
				if os.path.basename(root)[0]=='.': continue
				dirname=root.replace(basedir,'')
				for f in files:
					if f[-1]=='~' or f[0]=='.': continue
					fzip.write(root+'/'+f,dirname+'/'+f)
					
					if log_progress:
						current+=os.path.getsize(os.path.join(root,f))
						if time.time() >= t_update:
							log_progress(current/total)
							t_update = time.time() + t_delta
			except: pass
	
	fzip.close()

def ZipExtract(zipfilepath,extractiondir):
	"""
	Extracts a given zip file to the specified directory
	"""
	
	archive=zipfile.ZipFile(zipfilepath)
	archive.extractall(path=extractiondir)

def GetInHM(seconds):

	hours=seconds/3600
	seconds-=3600*hours
	minutes=seconds/60.
	return '%02d:%02d'%(hours,minutes)

def GetInHMS(seconds):

	hours=seconds / 3600
	seconds -= 3600*hours
	minutes=seconds / 60
	seconds -= 60*minutes
	if hours==0: return "%02d:%02d" % (minutes, seconds)
	return "%02d:%02d:%02d" % (hours, minutes, seconds)

def GetInHMSComplete(seconds):

	hours=seconds / 3600
	seconds -= 3600*hours
	minutes=seconds / 60
	seconds -= 60*minutes
	return "%02d:%02d:%02d" % (hours, minutes, seconds)

def InitGeo(xmlfile):

	geo_loc=[]
	root=xml.parse(xmlfile).getroot()
	balises=root.find('georef')
	for elem in balises: geo_loc.append([elem.attrib['name'],elem.attrib['type'],elem.attrib['code'],elem.attrib['proj']])
	return geo_loc

def TextCorrect(text):
	
	texte=''
	for i in range(len(text)):
		if text[i]in['/',' ',';',' ','\\']: texte+='_'
		else: texte+=text[i]
	return texte

def TextCorrectNum(text):
	
	texte=''
	for i in range(len(text)):
		if text[i]==',': texte+='.'
		else: texte+=text[i]
	return texte

def TextCorrectEntity(entity,i):

	if i+1<10:		label=entity+'000'+str(i+1)
	elif i+1<100:	label=entity+'00' +str(i+1)
	elif i+1<1000:	label=entity+'0'  +str(i+1)
	else:			label=entity+str(i+1)
	return label

def SortXmlData(balises):
	
	data=[]
	for elem in balises:
		key=elem.text
		data.append((key, elem))
	data.sort()
	balises[:]=[item[-1] for item in data]
	return balises

def Direc2Char(direc):
	dirchar=''
	if direc<10.: tmp_char='00'+'%.1f'%direc
	elif direc<100.: tmp_char='0'+'%.1f'%direc
	else: tmp_char='%.1f'%direc
	for ichar in range(len(tmp_char)):
		if tmp_char[ichar]!='.': dirchar+=tmp_char[ichar]
	return dirchar


def AlphaCalc(v1, v2, v3, h1=40., h2=80., h3=120., vcalm=0.1):
	"""
	Evaluates wind shear coefficients from 3 series of speeds at 3 different heights.
	v1, v2 and v3 are floats or array-likes. h1, h2 and h3 are floats.
	vcalm is a float which specifies a low-filter on wind speeds.
	Returns an array having the same size as v1, v2 and v3.
	"""
	try:
		
		v1,v2,v3 = np.array(v1),np.array(v2),np.array(v3)
		if v1.size!=v2.size or v1.size!=v3.size:
			raise ValueError('v1, v2 and v3 should have the same size')
		if vcalm!=None:
			v1[v1<vcalm]=np.nan
			v2[v2<vcalm]=np.nan
			v3[v3<vcalm]=np.nan
		
		logh1,logh2,logh3 = log(h1),log(h2),log(h3)
		logv1,logv2,logv3 = np.log(v1),np.log(v2),np.log(v3)
		
		xmoy = np.mean([logh1,logh2,logh3])
		ymoy = np.mean([logv1,logv2,logv3],axis=0)
		
		covxy = 0.
		varx = 0.
		for logv,logh in [(logv1,logh1),(logv2,logh2),(logv3,logh3)]:
			covxy += (logv - ymoy) * (logh - xmoy)
			varx += (logh - xmoy) ** 2
			
		covxy = covxy / 3.
		varx = varx / 3.
		alpha = covxy / varx
		
		return alpha
	
	except:
		traceback.print_exc()
		return np.nan

def rect_to_polar_input(ux, uy, uz):

	direc=90.-degrees(atan2(-uy, -ux))
	if direc<-10:direc=direc+360.
	
	vh=sqrt(ux*ux+uy*uy)
	inc=90.-degrees(atan2(vh,uz))
	
	return direc,inc


class P_PARAM(object):
	'''Process Parameter parent class
	defines the mandatory meta-data for any process
	and how to write the log'''
	cat			=''# Used for report
	type		=''# Used for report
	messfile	=''#where to log
	
	def __init__(self,time2use):
		if time2use!=None:
			self.time2use	=str(time2use)
		else:
			self.time2use	=GetTime()
		self.user		=''
		self.code		=''
		self.errors		=[]#what to log
		self.LOCAL		=True
		
		self.site		=''
		self.name		=''
		self.format		=''
		self.status		=''
		self.comments	=''
		self.blocked	=''
		
		self._prog_frac = 0.
		
	def WriteLog(self,status=1,extra={},print_exc=True):
		"""
		Highlights error and exits process
		"""
		
		try:
			print("Process {}: '{}' has ended. Success:{}".format(self.cat,self.code,bool(status)))
			self.errors= [error.encode('utf8') if isinstance(error,unicode) else error for error in self.errors]
			print("time2use: {}, log:\n{}\n".format(self.time2use,'\n'.join(self.errors)))
		except StandardError: pass
		if status==0 and print_exc:
			try: print(traceback.format_exc())
			except StandardError: print("no traceback")
		self.WriteMessages(status,extra)
		
		try:
			
			if status==0:	val=9.99
			else:			val=1.01
			if not self.LOCAL:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(val))
			
			self.SetXmlFiles(status)
			
			# Clean files in APPLI/TMP/
			tmp_dir = PATH+'../../APPLI/TMP/'
			for filename in os.listdir(tmp_dir):
				if self.time2use in filename:
					os.remove(os.path.join(tmp_dir, filename))
			
			sys.exit(0)
			
		except (KeyboardInterrupt, SystemExit): raise
		except Exception as e:
			sys.stderr.write(str(e) + "\n")
			sys.stderr.flush()
			self.SetXmlFiles(0)
			sys.exit(1)
	
	def WriteMessages(self,status=1,extra={},user=True):
		if self.messfile!='':
			try:	root=xml.parse(self.messfile).getroot()
			except:	root=xml.Element('messages')
			bal=xml.SubElement(root,'message')
			if user: bal.attrib['user'] = self.user
			
			if len(self.errors)>0:
				if isinstance(self.errors[0], str):	bal.text=self.errors[0].decode('utf-8')
				else: bal.text=self.errors[0]
			elif status==0:
				bal.text = 'An error occured'
			else: bal.text=' '
			bal.attrib['num']=str(status)
			bal.attrib['code']=self.code
			bal.attrib['name']=self.name
			bal.attrib['time']=self.time2use
			for key,item in extra.iteritems():
				bal.attrib[key]=item
			
			xml.ElementTree(root).write(self.messfile,encoding='UTF-8',xml_declaration=False)
	
	def UpdateMainProgress(self,frac):
		try:
			frac = max(0.,min(1.,float(frac)))
			
			progressfile=PATH+'../../APPLI/TMP/logout_'+self.time2use+'.xml'
			if not os.path.isfile(progressfile):
				root=xml.Element('logout')
				xml.SubElement(root,'progress_text')
				xml.SubElement(root,'progress_frac').text='0'
				xml.ElementTree(root).write(progressfile)
				if not self.LOCAL:
					with open(PATH+'../../../progress.txt','w') as pf: pf.write('0')
			
			self._prog_frac=frac
			
			rootprogress=xml.parse(progressfile).getroot()
			rootprogress.find('progress_text').text='%i'%(100.*self._prog_frac)
			rootprogress.find('progress_frac').text=str(self._prog_frac)
			xml.ElementTree(rootprogress).write(progressfile)
			if not self.LOCAL:
				with open(PATH + '../../../progress.txt', 'w') as pf: pf.write(str(self._prog_frac))
		
		except Exception as e:
			print("Error UpdateMainProgress: {}".format(e))
	
	def IncrMainProgress(self,frac):
		try:
			frac = max(0.,min(1.,self._prog_frac+float(frac)))
		except Exception as e:
			print("Error IncrMainProgress: {}".format(e))
		self.UpdateMainProgress(frac)
	
	def UpdateProgress(self,ithread,frac,text):
		xmlfile = PATH + '../../APPLI/TMP/logout_' + self.time2use + '_' + str(ithread) + '.xml'
		try:
			frac = max(0.,min(1.,float(frac)))
			
			if not os.path.isfile(xmlfile):
				root=xml.Element('logout')
				xml.SubElement(root,'progress_text')
				xml.SubElement(root,'progress_frac').text='0'
				xml.ElementTree(root).write(xmlfile)
		
			root=xml.parse(xmlfile).getroot()
			root.find('progress_text').text=UnixSanitizeStr(text, to_unicode=True)
			root.find('progress_frac').text=str(min(frac,1.))
			xml.ElementTree(root).write(xmlfile,encoding="UTF-8",xml_declaration=False)
		
		except Exception as e:
			print("Error UpdateProgress of {}: {}".format(xmlfile,e))
	
	def SetXmlFiles(self,status=1):
		pass#TODO?

class PARAM_SET(P_PARAM):
	cat		='PARAM'
	
	def __init__(self,site='',time2use=None):
		P_PARAM.__init__(self, time2use)
		self.site		=site
		self.conf		=False

class CFD_PARAM(P_PARAM):
	cat		='CFD_PROCESS'
	
	def __init__(self,site='',time2use=None,LOCAL=True):
		
		P_PARAM.__init__(self, time2use)
		self.site		=site
		self.LOCAL		=LOCAL
		
		self.nproc		=1
		self.p_pool		=P_POOL()
		self.conf		=False
	
	def WriteMessages(self,status=1,extra={}):
		self.messfile	=PATH+'../../PROJECTS_CFD/'+self.site+'/messages.xml'
		P_PARAM.WriteMessages(self, status, extra, False)

class WDP_PARAM(P_PARAM):
	cat		='WDP_PROCESS'
	
	def __init__(self,site='',time2use=None):
		
		P_PARAM.__init__(self, time2use)
		self.site		=site
		
		self.version	=VERSION
		self.nproc		=1
		self.p_pool		=P_POOL()
		self.conf		=False
	
	def WriteMessages(self,status=1,extra={}):
		self.messfile	=PATH+'../../PROJECTS_WDP/'+self.site+'/messages.xml'
		P_PARAM.WriteMessages(self, status, extra, False)

class LIST_CFD_PARAM(P_PARAM):
	cat			='LIST_CFD'
	messfile	=PATH+'../../PROJECTS_CFD/messages.xml'
	
	def __init__(self,time2use):
		
		P_PARAM.__init__(self, time2use)
		
		self.filename		=''
		self.version		=''
		self.path			=''
		self.duration		=0.
		
		self.nproc		=1
		self.p_pool		=P_POOL()
		self.conf		=False

class CFD_CLOUD_PARAM(P_PARAM):
	cat			='CFD_CLOUD_PROCESS'
	
	def __init__(self,time2use=None):
		
		P_PARAM.__init__(self, time2use)
		
		self.lname					=''
		
		self.provider				=''
		self.storage				=''
		self.machine				=''
		self.nmach					=-1

		self.login					=''
		self.pwd					=''
		
		self.nproctot				=0
		self.idjob					=0
		
		self.duration_tot			=0.
		
		self.codename=''
		
		self.UPLOADED=False
	
	def WriteLog(self,status=1,extra={},print_exc=True):
		subprocess.call(['rm','-rf',PATH+'../../APPLI/EXTERN/CLOUD/'+self.time2use])
		P_PARAM.WriteLog(self,status=status,extra=extra,print_exc=print_exc)
	
	def WriteMessages(self,status=1,extra={}):
		self.messfile	=PATH+'../../PROJECTS_CFD/'+self.site+'/messages.xml'
		P_PARAM.WriteMessages(self,status=status,extra=extra,user=False)


class CFD_ASSESS_DATA(CFD_PARAM):
	type		='CFD_ASSESS'
	
	def __init__(self,time2use):
		
		CFD_PARAM.__init__(self, '', time2use)
		self.code			='cfd_assess'
		
		self.extraname		= ''
		self.wake			= ''
		self.genelayout		= {}
		self.mes_ele 		= 0
		self.air_dens		= 1.225
		self.wake_decay		= 0.07

		self.istart			= 0
		self.n_direction	= 12
		self.dic_matrix		= {}
		self.dic_matrix_d	= {}
		self.wt_lab			= []
		self.wt_ele			= []
		self.wt_loc			= []
		self.wt_hubheight	= []
		self.duration_tot	=0.
		
class CFD_MULTI_DATA(CFD_PARAM):
	type		='CFD_MULTI'
	
	def __init__(self,time2use):
		
		CFD_PARAM.__init__(self,'',time2use)
		self.code			='cfd_multi'
		
		self.rosename		= ''
		self.climatoname	= ''
		self.method			= '2'
		self.ndirec			= '12'
		self.density		= '1.225'
		self.PROCESS_MAP	= False
		self.PROCESS_SITE	= False
		self.PROCESS_TURB	= False
		self.hdirec			= '80'
		self.nexpo			= '2'
		
		self.n_mast			=0
		self.n_lidar		=0
		self.n_wt			=0
		self.n_point		=0
		self.n_meso			=0
		self.n_mapping		=0
		self.n_usermap		=0
		
		self.heights		=[]
		
		self.duration_tot	=0.
		self.duration_1		=0.
		self.duration_2		=0.
		self.duration_3		=0.
		self.duration_4		=0.
		self.duration_5		=0.
		self.duration_6		=0.
		self.duration_7		=0.
		self.duration_8		=0.
		self.duration_9		=0.
		self.duration_10	=0.


class CFD_PROJ:
	
	def __init__(self):
		
		self.cat			='PROJECT_CFD'
		self.type			='PROJECT_CFD'
		
		self.name			=''
		self.user			=''
		self.size			=''
		self.status			=''
		self.comments		=''
		self.georef			=''
		self.loaded			='No'
		self.analysed		='No'
		self.meshed			='No'
		self.calculated		='No'
		self.rosed			='No'
		self.extrapolated	='No'
		self.assessed		='No'
		self.optimized		='No'
		self.completed		='No'
		self.blocked		='No'
		self.oncloud		='No'
		
		self.processing		=False
		
		self.xc				=None
		self.yc				=None
		self.centre_method	=None
		self.diamin			=None
		self.geolat			='-'
		self.geolon			='-'
	
	def load_file(self,entity,filename):
		
		if os.path.isabs(filename):
			source = filename
			filename = os.path.basename(filename)
			name=splitext(filename)[0].strip()
		else:
			name=splitext(filename)[0].strip()
			source=PATH+'../../INPUT_FILES/'+entity.upper()+'/'+name
		destination=PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/'+entity.upper()
		subprocess.call(['mkdir','-p',destination])
		subprocess.call(['cp','-rf',source,destination])
		
		xmlfile=PATH+'../../PROJECTS_CFD/'+self.name+'/site.xml'
		rootsite = xml.parse(xmlfile).getroot()
		bal = rootsite.find(entity)
		if entity in ['picture','climato','generator']:
			name_list = eval(bal.text)
			if filename not in name_list: name_list.append(filename)
			bal.text = str(name_list)
		else:
			bal.text = filename
		xml.ElementTree(rootsite).write(xmlfile)
		
		if entity=='picture':
			xmlfile=PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/PICTURE/'+name+'/using_visualizations.xml'
			root=xml.Element('using_visualizations')
			xml.ElementTree(root).write(xmlfile)
	
	def set_center(self,entity,filename):
		name=splitext(filename)[0].strip()
		xmlfile=PATH+'../../INPUT_FILES/'+entity.upper()+'/'+name+'/'+name+'.xml'
		root=xml.parse(xmlfile).getroot()
		self.xc=float(root.find('xc').text)
		self.yc=float(root.find('yc').text)
		self.centre_method=entity.upper()
		return self.xc,self.yc
	
	def update_diamin(self,entity,filename):
		name=splitext(filename)[0].strip()
		xmlfile=PATH+'../../INPUT_FILES/'+entity.upper()+'/'+name+'/'+name+'.xml'
		root=xml.parse(xmlfile).getroot()
		diaminfile=eval(root.find('diamin_'+entity).text)
		xcf=eval(root.find('xc').text)
		ycf=eval(root.find('yc').text)
		try: 	dist=sqrt((self.xc-xcf)**2+(self.yc-ycf)**2)
		except:	dist=0.0
		self.diamin = max(diaminfile+dist*2,self.diamin)
		return self.diamin
	
	def generate_project(self,orotype=0,orodb=0,oro='500.',routype=0,roudb=0,rou='0.03',
							mast=None,wt=None,lidar=None,meso=None,point=None,mapping=None,usermap=None,
							climato=[],picture=[],generator=[],confid=False):
		
		if self.xc==None or self.yc==None or self.centre_method==None:
			raise ValueError('Center should first be set with set_center()')
		orotype,orodb,routype,roudb = int(orotype),int(orodb),int(routype),int(roudb)
		
		DO_DIAMIN = self.diamin==None
		entities={'mast':mast,'wt':wt,'lidar':lidar,'meso':meso,'point':point,'mapping':mapping,'usermap':usermap}
		for entity,filename in entities.iteritems():
			if filename not in ['',None] and DO_DIAMIN:
				self.update_diamin(entity, filename)
		
		if self.georef not in ['','No georeference','Fictive georeference','Unknown georeference']:
			self.geolon,self.geolat = convert_coords(self.xc,self.yc,inputEPSG=GetEpsg(self.georef,self.user))
		
		default_wtg = 'Vestas_V100_2200kW.wtg'
		if default_wtg not in generator:
			generator=[default_wtg]+generator
		
		subprocess.call(['rm','-rf',PATH+'../../PROJECTS_CFD/'+self.name])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/ORO'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/ROU'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/MAST'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/LIDAR'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/WT'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/POINT'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/MESO'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/MAPPING'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/USERMAP'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/PICTURE'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/CLIMATO'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/INPUT_FILES/GENERATOR'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/DATA'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/LOAD'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/ANALYSE'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/ANALYSE/VISU'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/MESH'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/MESH/VIDEOS'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/CALC'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/CALC/VIDEOS'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/ROSE'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/ROSE/VALIDATIONS'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/EXTRA'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/ASSESS'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/USER'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_load'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_analyse'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_mesh01'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_calc01'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_assess'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_CFD/'+self.name+'/LOAD/VISU'])
		
		xmlfile=PATH+'../../PROJECTS_CFD/'+self.name+'/site.xml'
		rootsite=xml.Element('site')
		rootsite.attrib['version']=VERSION
		
		xml.SubElement(rootsite,'sitename').text		= self.name
		xml.SubElement(rootsite,'wt')
		xml.SubElement(rootsite,'mast')
		xml.SubElement(rootsite,'lidar')
		xml.SubElement(rootsite,'meso')
		xml.SubElement(rootsite,'point')
		xml.SubElement(rootsite,'mapping')
		xml.SubElement(rootsite,'usermap')
		xml.SubElement(rootsite,'picture').text			= '[]'
		xml.SubElement(rootsite,'climato').text			= '[]'
		xml.SubElement(rootsite,'generator').text		= '[]'
		xml.SubElement(rootsite,'comments').text		= self.comments
		xml.SubElement(rootsite,'orotype').text			= str(orotype)
		xml.SubElement(rootsite,'orodb').text			= str(orodb)
		xml.SubElement(rootsite,'oro')
		xml.SubElement(rootsite,'routype').text			= str(routype)
		xml.SubElement(rootsite,'roudb').text			= str(roudb)
		xml.SubElement(rootsite,'rou')
		xml.SubElement(rootsite,'centre_method').text	= self.centre_method
		xml.SubElement(rootsite,'xcentre').text			= '{:.1f}'.format(self.xc)
		xml.SubElement(rootsite,'ycentre').text			= '{:.1f}'.format(self.yc)
		xml.SubElement(rootsite,'diamin').text			= '{:.0f}'.format(self.diamin)
		xml.SubElement(rootsite,'georef').text			= self.georef
		xml.SubElement(rootsite,'geolat').text			= str(self.geolat)
		xml.SubElement(rootsite,'geolon').text			= str(self.geolon)
		xml.SubElement(rootsite,'confidentiality').text	= str(confid)
		xml.SubElement(rootsite,'WDP').text				= ''
		xml.ElementTree(rootsite).write(xmlfile)
		
		if orotype==1 and orodb==0:
			self.load_file('oro', oro)
		else:
			rootsite = xml.parse(xmlfile).getroot()
			rootsite.find('oro').text = oro
			xml.ElementTree(rootsite).write(xmlfile)
		
		if routype==1 and roudb==0:
			self.load_file('rou', rou)
		else:
			rootsite = xml.parse(xmlfile).getroot()
			rootsite.find('rou').text = rou
			xml.ElementTree(rootsite).write(xmlfile)
		
		for entity,filename in entities.iteritems():
			if filename not in ['',None]:
				self.load_file(entity, filename)
		
		for filename in climato:
			self.load_file('climato', filename)
		for filename in generator:
			self.load_file('generator', filename)
		for filename in picture:
			self.load_file('picture', filename)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_mesh01/previews.xml'
		root=xml.Element('previews')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/LOAD/VISU/load_visu.xml'
		root=xml.Element(self.name)
		xml.SubElement(root,'res_close_oro').text='-'
		xml.SubElement(root,'res_close_rou').text='-'
		xml.SubElement(root,'res_large_oro').text='-'
		xml.SubElement(root,'res_large_rou').text='-'
		xml.SubElement(root,'visualizations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ANALYSE/analyses.xml'
		root=xml.Element('analyses')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ANALYSE/analvisu.xml'
		root=xml.Element('visualizations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/MESH/meshes.xml'
		root=xml.Element('meshes')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/MESH/meshvisu.xml'
		root=xml.Element('visualizations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/CALC/calculations.xml'
		root=xml.Element('calculations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/CALC/calcvisu.xml'
		root=xml.Element('visualizations')
		xml.SubElement(root,'videos')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ROSE/roses.xml'
		root=xml.Element('roses')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ROSE/rosevisu.xml'
		root=xml.Element('visualizations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ROSE/VALIDATIONS/validations.xml'
		root=xml.Element('validations')
		xml.ElementTree(root).write(outfile)

		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/EXTRA/extrapolations.xml'
		root=xml.Element('extrapolations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/EXTRA/extravisu.xml'
		root=xml.Element('visualizations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ASSESS/assessments.xml'
		root=xml.Element('assessments')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/ASSESS/assessvisu.xml'
		root=xml.Element('visualizations')
		xml.ElementTree(root).write(outfile)
		
		outfile=PATH+'../../PROJECTS_CFD/'+self.name+'/contours.xml'
		root=xml.Element('contours')
		xml.ElementTree(root).write(outfile)
		
		file1=PATH+'../../USERS/'+self.user+'/cfd_load/cfd_load.xml'
		file2=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_load/cfd_load.xml'
		subprocess.call(['cp','-f',file1,file2])
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/cfd_load.xml',file2])
		
		file1=PATH+'../../USERS/'+self.user+'/cfd_analyse/cfd_analyse.xml'
		file2=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_analyse/cfd_analyse.xml'
		subprocess.call(['cp','-f',file1,file2])
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/cfd_analyse.xml',file2])
		
		file1=PATH+'../../USERS/'+self.user+'/cfd_mesh01/cfd_mesh01.xml'
		file2=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_mesh01/cfd_mesh01.xml'
		subprocess.call(['cp','-f',file1,file2])
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/cfd_mesh01.xml',file2])
		
		file1=PATH+'../../USERS/'+self.user+'/cfd_calc01/cfd_calc01.xml'
		file2=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_calc01/cfd_calc01.xml'
		subprocess.call(['cp','-f',file1,file2])
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/cfd_calc01.xml',file2])
		
		file2=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_assess/cfd_layout.xml'
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/cfd_layout.xml',file2])
		
		file2=PATH+'../../PROJECTS_CFD/'+self.name+'/USER/cfd_assess/cfd_environ.xml'
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/cfd_environ.xml',file2])
		
		xmlfile=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
		root=xml.parse(xmlfile).getroot()
		FOUND=False
		for bal in root:
			if bal.text==self.name:
				balise=bal
				FOUND=True
				break
		if not FOUND:
			balise=xml.SubElement(root,'site')
			balise.text=self.name
		
		self.size='%.3f'%(GetFolderSize(PATH+'../../PROJECTS_CFD/'+self.name)/1.e+6)
		
		balise.attrib['oncloud']		=self.oncloud
		balise.attrib['loaded']			=self.loaded
		balise.attrib['analysed']		=self.analysed
		balise.attrib['meshed']			=self.meshed
		balise.attrib['calculated']		=self.calculated
		balise.attrib['rosed']			=self.rosed
		balise.attrib['extrapolated']	=self.extrapolated
		balise.attrib['assessed']		=self.assessed
		balise.attrib['optimized']		=self.optimized
		balise.attrib['completed']		=self.completed
		balise.attrib['comments']		=self.comments
		balise.attrib['georef']			=self.georef
		balise.attrib['size']			=self.size
		balise.attrib['status']			=self.status
		balise.attrib['user']			=self.user
		balise.attrib['blocked']		=self.blocked
		
		root=SortXmlData(root)
		xml.ElementTree(root).write(xmlfile)
		
		last_sites	=[]
		new_sites	=[]
		new_sites.append(self.name)
			
		xmlfile=PATH+'../../USERS/'+self.user+'/user.xml'
		root=xml.parse(xmlfile).getroot()
		bal=root.find('cfd_sites')
		bal2=bal.find('last_sites')
		for bal3 in bal2: last_sites.append(bal3.text)
		for i in range(len(last_sites)):
			if last_sites[i]!=self.name and len(new_sites)<4 and last_sites[i]!=None: new_sites.append(last_sites[i])
		bal.remove(bal2)
		bal2=xml.SubElement(bal,'last_sites')
		for i in range(len(new_sites)):
			bal3=xml.SubElement(bal2,'last_site')
			bal3.text=new_sites[i]
		xml.ElementTree(root).write(xmlfile)
	
	@classmethod
	def from_DB(cls,name):
		"""
		Initialize a CFD_PROJ object from an existing project
		"""
		xmlfile=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.text==name:
				FOUND=True
				break
		if not FOUND: raise ValueError('Could not find an existing project named {}'.format(name))
		
		obj=cls()
		
		obj.name			=bal.text
		obj.user			=bal.attrib.get('user')
		obj.size			=bal.attrib.get('size')
		obj.status			=bal.attrib.get('status')
		obj.comments		=bal.attrib.get('comments')
		obj.georef			=bal.attrib.get('georef')
		obj.loaded			=bal.attrib.get('loaded')
		obj.analysed		=bal.attrib.get('analysed')
		obj.meshed			=bal.attrib.get('meshed')
		obj.calculated		=bal.attrib.get('calculated')
		obj.rosed			=bal.attrib.get('rosed')
		obj.extrapolated	=bal.attrib.get('extrapolated')
		obj.assessed		=bal.attrib.get('assessed')
		obj.optimized		=bal.attrib.get('optimized')
		obj.completed		=bal.attrib.get('completed')
		obj.blocked			=bal.attrib.get('blocked')
		obj.oncloud			=bal.attrib.get('oncloud')
		
		PROCESSING=False
		try:
			rootproc=xml.parse(xmlfileproc).getroot()
			for balproc in rootproc:
				try:
					if 'cfd' in balproc.attrib['code'] and balproc.attrib['site']==siteobject.name:
						PROCESSING=True
						break
				except: pass
			if not PROCESSING:
				rootcloud=xml.parse(xmlfilecloud).getroot()
				for balcloud in rootcloud:
					try:
						if 'cfd' in balcloud.attrib['code'] and balcloud.attrib['site']==siteobject.name:
							PROCESSING=True
							break
					except: pass
		except StandardError as e: traceback.print_exc()
		
		if PROCESSING:	obj.processing='Yes'
		else:			obj.processing='No'
		
		xmlfile=PATH+'../../PROJECTS_CFD/'+name+'/site.xml'
		root=xml.parse(xmlfile).getroot()
		obj.xc				=float(root.find('xcentre').text)
		obj.yc				=float(root.find('ycentre').text)
		obj.diamin			=float(root.find('diamin').text)
		obj.centre_method	=root.find('centre_method').text
		obj.geolat			=root.find('geolat').text
		obj.geolon			=root.find('geolon').text
		
		return obj

class WDP_PROJ:
	def __init__(self):
		
		self.cat = ''
		self.format = ''
		self.name = ''
		self.loaded = ''
		self.filtered = ''
		self.predicted = ''
		self.completed = ''
		self.georef = ''
		self.size = ''
		self.status = ''
		self.user = ''
		self.comments = ''
		self.blocked = ''
	
	def generate_project(self):
		
		subprocess.call(['rm','-rf',PATH+'../../PROJECTS_WDP/'+self.name])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_WDP/'+self.name])
		#subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_WDP/'+self.name+'/Plots'])
		
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_WDP/'+self.name+'/USER'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_WDP/'+self.name+'/USER/mcp_xgb'])
		subprocess.call(['mkdir','-p',PATH+'../../PROJECTS_WDP/'+self.name+'/MCP'])
		
		outfile=PATH+'../../PROJECTS_WDP/'+self.name+'/MCP/mcp.xml'
		root=xml.Element('mcp')
		xml.ElementTree(root).write(outfile)
		
		file1=PATH+'../../USERS/'+self.user+'/mcp_xgb/mcp_xgb.xml'
		file2=PATH+'../../PROJECTS_WDP/'+self.name+'/USER/mcp_xgb/mcp_xgb.xml'
		subprocess.call(['cp','-f',file1,file2])
		if os.path.isfile(file2) is False: subprocess.call(['cp','-f',PATH+'../../COMMON/default/mcp_xgb.xml',file2])
	
	def update_metadata(self):
		
		xmlfile=PATH+'../../PROJECTS_WDP/'+self.name+'/site.xml'
		root=xml.Element('site')
		root.attrib['version']=VERSION
		xml.SubElement(root,'comments').text	= self.comments
		xml.SubElement(root,'georef').text		= self.georef
		xml.SubElement(root,'savetime').text	= GetTime()
		xml.SubElement(root,'CFD').text			= ''
		xml.ElementTree(root).write(xmlfile)
		
		last_sites	=[]
		new_sites	=[]
		new_sites.append(self.name)
			
		xmlfile=PATH+'../../USERS/'+self.user+'/user.xml'
		root=xml.parse(xmlfile).getroot()
		bal=root.find('wdp_sites')
		bal2=bal.find('last_sites')
		for bal3 in bal2: last_sites.append(bal3.text)
		for i in range(len(last_sites)):
			if last_sites[i]!=self.name and len(new_sites)<4 and last_sites[i]!=None: new_sites.append(last_sites[i])
		bal.remove(bal2)
		bal2=xml.SubElement(bal,'last_sites')
		for i in range(len(new_sites)):
			bal3=xml.SubElement(bal2,'last_site')
			bal3.text=new_sites[i]
		xml.ElementTree(root).write(xmlfile)
		
		xmlfile=PATH+'../../PROJECTS_WDP/projects_wdp.xml'
		root=xml.parse(xmlfile).getroot()
		FOUND=False
		for bal in root:
			if bal.text==self.name:
				balise=bal
				FOUND=True
				break
		if not FOUND:
			balise=xml.SubElement(root,'site')
			balise.text=self.name
			
		self.size='%.3f'%(GetFolderSize(PATH+'../../PROJECTS_WDP/'+self.name)/1.e+6)

		balise.attrib['loaded']			=self.loaded
		balise.attrib['screened']		=self.screened
		balise.attrib['predicted']		=self.predicted
		balise.attrib['completed']		=self.completed
		balise.attrib['comments']		=self.comments
		balise.attrib['georef']			=self.georef
		balise.attrib['size']			=self.size
		balise.attrib['status']			=self.status
		balise.attrib['user']			=self.user
		balise.attrib['blocked']		=self.blocked
		
		root=SortXmlData(root)
		xml.ElementTree(root).write(xmlfile)


class WDG_PROJ:
	
	def __init__(self):
		
		self.cat			=''
		self.format			=''
		self.name			=''
		self.loaded			=''
		self.calculated		=''
		self.corrected		=''
		self.completed		=''
		self.size			=''
		self.status			=''
		self.user			=''
		self.comments		=''
		self.blocked		=''
		self.processing		=False

class DB:
	
	def __init__(self):
		
		self.dbname 		=''
		self.dbtype 		=''
		self.datatype 		=''
		self.comments		=''
		self.georef			=''

class COUNTRY:
	
	def __init__(self):
		
		self.name 		=''
		self.format 	=''
		self.type 		=''
		self.used 		=''
		self.size		=''
		self.status		=''
		self.user		=''
		self.comments	=''
		self.georef		=''
		self.blocked	=''

class STATE_ANAL():
	
	def __init__(self,window):
		
		self.anal=window.combobox_anal_param.get_active()
		self.climato=window.combobox_anal_climato.get_active()
		self.nproc=int(window.spinbutton_nproc_anal.get_value())

	def reset(self,window):

		window.combobox_anal_param.set_active(self.anal)
		window.combobox_anal_climato.set_active(self.climato)
		window.spinbutton_nproc_anal.set_value(self.nproc)

class STATE_MESH():
	
	def __init__(self,window):
		
		pass

	def reset(self,window):

		pass

class STATE_CALC():
	
	def __init__(self,window):
		
		self.calc=window.combobox_calc_param.get_active()
		self.mesh=window.combobox_calc_mesh.get_active()
		self.stab=window.combobox_calc_stab.get_active()
		self.dir=window.combobox_calc_dir.get_active()
		self.rose=window.combobox_calc_rose.get_active()
		self.nproc=int(window.spinbutton_nproc_calc.get_value())
		self.light=window.checkbutton_calc_light.get_active()
		self.cfd=window.checkbutton_calc_cfd.get_active()

	def reset(self,window):

		window.combobox_calc_param.set_active(self.calc)
		window.combobox_calc_mesh.set_active(self.mesh)
		window.combobox_calc_stab.set_active(self.stab)
		window.combobox_calc_dir.set_active(self.dir)
		window.combobox_calc_rose.set_active(self.rose)
		window.spinbutton_nproc_calc.set_value(self.nproc)
		window.checkbutton_calc_light.set_active(self.light)
		window.checkbutton_calc_cfd.set_active(self.cfd)

class STATE_ROSE():
	
	def __init__(self,window):
		

		self.nproc=int(window.spinbutton_nproc_rose.get_value())
		self.i2use_speed=window.combobox_rose_refspeed.get_active()
		self.i2use_dir=window.combobox_rose_refdirec.get_active()
		self.h2use_speed=window.spinbutton_speed.get_value()
		self.h2use_dir=window.spinbutton_direc.get_value()
		self.is_map=window.checkbutton_rose_map.get_active()
		self.is_site=window.checkbutton_rose_site.get_active()
		self.name=window.entry_roseconf.get_text()

	def reset(self,window):

		window.spinbutton_nproc_calc.set_value(self.nproc)
		window.combobox_rose_refspeed.set_active(self.i2use_speed)
		window.combobox_rose_refdirec.set_active(self.i2use_dir)
		window.spinbutton_speed.set_value(self.h2use_speed)
		window.spinbutton_direc.set_value(self.h2use_dir)
		window.checkbutton_rose_map.set_active(self.is_map)
		window.checkbutton_rose_site.set_active(self.is_site)
		window.entry_roseconf.set_text(self.name)


class P_THREAD(threading.Thread):
	"""
	Thread object for local processes
	p_pool: P_POOL object
	nproc: the maximum number of processors allowed
	"""
	def __init__(self,p_pool,nproc):
		threading.Thread.__init__(self)
		self.p_pool=p_pool
		self.nproc=min(NCPU,max(1,nproc))
	
	def run(self):
		"""
		This is just a template, child classes should overwrite this method.
		use prerun and postrun to avoid common objects access issues.
		ithread is usually needed for the GUI progress bars
		"""
		ithread=self.prerun()
		
		# run something here
		
		self.postrun(ithread)
	
	def prerun(self):
		"""
		function to avoid running more than nproc processes at the same time, for a given P_POOL object
		it will be executed by several threads at the same time so we must avoid any race condition
		"""
		# add to queue
		self.p_pool.queue.append(self)
		# wait until we are in the first nproc authorized processes
		while self.p_pool.queue.index(self)>=self.nproc: time.sleep(0.5)
		# get ithread number
		ithread=self.p_pool.busy.index(False)
		# tag ithread as busy
		self.p_pool.busy[ithread]=True
		return ithread
	
	def postrun(self,ithread):
		# tag ithread as not busy
		self.p_pool.busy[ithread]=False
		# remove from queue
		self.p_pool.queue.remove(self)

class P_POOL(object):
	"""
	little class to hold a queue of P_THREAD and a core availability index
	"""
	def __init__(self):
		self.queue=[]
		self.busy=[False]*NCPU

def parse_nproc(nproc):
	nproc=int(nproc)
	if nproc==0: nproc=NCPU-1
	nproc=max(1,nproc)
	return nproc

def GetProcUse():
	
	npu=0
	try:
		root=xml.parse(xmlfileproc).getroot()
		for bal in root:
			if FindProcess(bal.attrib['time']):
				try: 
					proc_cpu=int(eval(bal.attrib['nproc']))
					if proc_cpu==0: proc_cpu=NCPU-1
					npu+=proc_cpu
				except: pass
	except: pass
	return npu

def GetMemUse():
	OPENFOAM_BIN = ['simpleFoam','gmshToFoam','checkMesh','renumberMesh','foamToVTK','decomposePar','reconstructPar','sample','mapFields']
	mem=0
	try:
		root=xml.parse(xmlfileproc).getroot()
		for bal in root:
			time2use=bal.attrib['time']
			for pid in ListPid():
				try:
					if Pid2Name(pid) in OPENFOAM_BIN or time2use in Pid2Name(pid):
						process = psutil.Process(pid)
						mem += process.memory_info()[0]
					else:
						cmd_args = Pid2CmdArgs(pid)
						if not cmd_args:
							continue
						for command_short_name in map(os.path.basename, cmd_args[0:1]):
							if time2use in command_short_name:
								process = psutil.Process(pid)
								mem += process.memory_info()[0]
								break
				except: pass
	except: pass
	return mem/1024./1024./1024.

def GetNprocess():
	
	return len(xml.parse(xmlfileproc).getroot())

def GetNqueue():
	
	return len(xml.parse(xmlfilequeue).getroot())

def GetNcloud():
	
	return len(xml.parse(xmlfilecloud).getroot())+len(xml.parse(xmlfileended).getroot())


def GetFolderSize(folder):
	
	total_size=os.path.getsize(folder)
	for item in os.listdir(folder):
		itempath=os.path.join(folder, item)
		if os.path.isfile(itempath):	total_size+=os.path.getsize(itempath)
		elif os.path.isdir(itempath):	total_size+=GetFolderSize(itempath)
	return total_size

class FORTRAN_FILE(file):

	def __init__(self, fname, endian='@', header_prec='i', *args, **kwargs):

		file.__init__(self, fname, *args, **kwargs)
		self.ENDIAN=endian
		self.HEADER_PREC=header_prec

	def get_header_length(self): return struct.calcsize(self.header_prec)

	def set_endian(self,c):

		if c in '<>@=': self.endian=c
		else: raise ValueError('Cannot set endian-ness')

	def get_endian(self): return self.endian

	def set_header_prec(self, prec):
		
		if prec in 'hilq': self.header_prec=prec
		else: raise ValueError('Cannot set header precision')
		
	def get_header_prec(self): return self.header_prec

	def read_exactly(self, num_bytes):

		data=''
		while True:
			l=len(data)
			if l==num_bytes: return data
			else: read_data=self.read(num_bytes-l)
			if read_data=='': raise IOError('Could not read enough data. Wanted %d bytes, got %d.' % (num_bytes, l))
			data+=read_data

	def read_check(self): return struct.unpack(self.ENDIAN+self.HEADER_PREC,self.read_exactly(self.header_length))[0]

	def write_check(self, number_of_bytes): self.write(struct.pack(self.ENDIAN+self.HEADER_PREC,number_of_bytes))

	def readRecord(self):

		l=self.read_check()
		data_str=self.read_exactly(l)
		check_size=self.read_check()
		if check_size != l: raise IOError('Error reading record from data file')
		return data_str

	def writeRecord(self,s):
		
		length_bytes=len(s)
		self.write_check(length_bytes)
		self.write(s)
		self.write_check(length_bytes)

	def readString(self): return self.readRecord()

	def writeString(self,s): self.writeRecord(s)

	def readReals(self, prec='f'):
		
		numpy_precisions={'d':np.float64,'f':np.float32}

		if prec not in self.real_precisions: raise ValueError('Not an appropriate precision')
			
		data_str=self.readRecord()
		num=len(data_str)/struct.calcsize(prec)
		numbers=struct.unpack(self.ENDIAN+str(num)+prec,data_str) 
		return np.array(numbers, dtype=numpy_precisions[prec])

	def writeReals(self, reals, prec='f'):

		if prec not in self.real_precisions: raise ValueError('Not an appropriate precision')
		length_bytes=len(reals)*struct.calcsize(prec)
		self.write_check(length_bytes)
		fmt=self.ENDIAN+prec
		for r in reals: self.write(struct.pack(fmt,r))
		self.write_check(length_bytes)

	def readInts(self, prec='i'):

		if prec not in self.int_precisions: raise ValueError('Not an appropriate precision')
		
		data_str=self.readRecord()
		num=len(data_str)/struct.calcsize(prec)
		return np.array(struct.unpack(self.ENDIAN+str(num)+prec,data_str))

	def writeInts(self, ints, prec='i'):

		if prec not in self.int_precisions: raise ValueError('Not an appropriate precision')
		
		length_bytes=len(ints)*struct.calcsize(prec)
		self.write_check(length_bytes)
		fmt=self.ENDIAN+prec
		for item in ints: self.write(struct.pack(fmt,item))
		self.write_check(length_bytes)

	header_length=property(fget=get_header_length)
	ENDIAN=property(fset=set_endian,fget=get_endian,doc="Possible endian values are '<', '>', '@', '='")
	HEADER_PREC=property(fset=set_header_prec,fget=get_header_prec,doc="Possible header precisions are 'h', 'i', 'l', 'q'")
	real_precisions='df'
	int_precisions='hilq'

def Iterable(obj):

	try:
		len(obj)
		return True
	except:
		return False
	
def Turn(p,q,r):
	
	return cmp((q[0]-p[0])*(r[1]-p[1])-(r[0]-p[0])*(q[1]-p[1]),0)

def KeepLeft(hull, r):
	
	while len(hull)>1 and Turn(hull[-2],hull[-1],r)!=TURN_LEFT: hull.pop()
	if not len(hull) or hull[-1]!=r: hull.append(r)
	return hull

def ConvexHull(points):
	
	"""
	Returns points on convex hull of an array of points
	"""
	
	points=sorted(points)
	l=reduce(KeepLeft,points,[])
	u=reduce(KeepLeft,reversed(points),[])
	return l.extend(u[i] for i in xrange(1,len(u)-1)) or l

def AreaFromPoints(refpoints):

	x=[]
	y=[]
	for point in refpoints:
		x.append(point[0])
		y.append(point[1])
	x=np.asanyarray(x)
	y=np.asanyarray(y)
	n=len(x)
	shift_up=np.arange(-n+1, 1)
	shift_down=np.arange(-1, n-1)	
	return (x*(y.take(shift_up)-y.take(shift_down))).sum() / 2.0

def AreaFromLines(reflines):
	
	area=0.
	for line in reflines: area+=abs(AreaFromPoints(line))
	return area

def GetMachine():

	machine=''
	
	try:
		os.system('inxi -c0 -CMDI > log_inxi')
		infile=open('log_inxi','r')
		lines=infile.readlines()
		infile.close()
		subprocess.call(['rm','log_inxi'])
		
		for line in lines:
			try:
				if line[0:7]=='Machine':	machine+='Machine	 '+line[11:]
			except: pass
			try:
				if line[0:3]=='CPU':		machine+='CPU		 '+line[11:]
			except: pass
			try:
				if line[0:4]=='Info':		machine+='Memory	  '+line.split('/')[-1].split()[0]
			except: pass
			try:
				if line[0:6]=='Drives':		machine+='Drives	  '+line[11:].split('(')[0][:-1]+'\n'
			except: pass
	except: pass
	
	return machine

def GenerateLines(multizone,refloc,resdist,diaref=None,distance=None,time2use=None,ithread=None,message=None):

	if distance is None: distance=resdist/10.
	
	reflines=[]
	
	if multizone==0:
		
		if time2use is not None: UpdateProgress(time2use,ithread,0.5,message)

		nsect=72
		refpoints=[]
		for point in refloc:
			angleradinit=pi/2.0+pi/nsect
			angleradprev=angleradinit+pi/nsect
			x=point[0]+resdist*cos(angleradprev)
			y=point[1]+resdist*sin(angleradprev)
			dist=sqrt(x**2+y**2)
			if diaref is not None:
				if dist<diaref/2.-2*distance: refpoints.append([x,y])
			else: refpoints.append([x,y])
			for isect in range(nsect-1):
				angleradcentre=angleradinit-2.*isect*pi/nsect
				angleradsuiv=angleradcentre-pi/nsect
				x=point[0]+resdist*cos(angleradsuiv)
				y=point[1]+resdist*sin(angleradsuiv)
				dist=sqrt(x**2+y**2)
				if diaref is not None:
					if dist<diaref/2.-2*distance: refpoints.append([x,y])
				else: refpoints.append([x,y])
		if len(refpoints)>0: reflines.append(ConvexHull(refpoints))

	else:

		if time2use is not None: UpdateProgress(time2use,ithread,0.05,message+' - 1/2')
		
		nsect=72
		for point in refloc:
			refpoints=[]
			angleradinit=pi/2.0+pi/nsect
			angleradprev=angleradinit+pi/nsect
			x=point[0]+resdist*cos(angleradprev)
			y=point[1]+resdist*sin(angleradprev)
			dist=sqrt(x**2+y**2)
			if diaref is not None:
				if dist<diaref/2.-2*distance: refpoints.append([x,y])
			else: refpoints.append([x,y])
			for isect in range(nsect-1):
				angleradcentre=angleradinit-2.*isect*pi/nsect
				angleradsuiv=angleradcentre-pi/nsect
				x=point[0]+resdist*cos(angleradsuiv)
				y=point[1]+resdist*sin(angleradsuiv)
				dist=sqrt(x**2+y**2)
				if diaref is not None:
					if dist<diaref/2.-2*distance: refpoints.append([x,y])
				else: refpoints.append([x,y])
			if len(refpoints)>3: reflines.append(refpoints)

		ntot=len(reflines)
		npdiv=40
		ndiv=1+ntot/npdiv
		tablines=[]
		for _ in range(ndiv): tablines.append([])
		for il in range(len(reflines)):
			ic=il/npdiv
			tablines[ic].append(reflines[il])

		for iline in range(len(tablines)):
			
			if time2use is not None: UpdateProgress(time2use,ithread,max(0.05,float(iline)/len(tablines)),message+' - 1/2')
		
			STILL_CROSS=True
			
			while STILL_CROSS:
				
				CROSS=False
				
				for il2test in range(len(tablines[iline])):
					
					if CROSS: break
					
					for il in range(len(tablines[iline])):
						
						if il2test!=il:
							
							p1=geometry.Polygon(tablines[iline][il2test])
							p2=geometry.Polygon(tablines[iline][il]) 
							new_pol=ops.cascaded_union([p1,p2])
							
							if p1.distance(p2)<distance/2:
								
								CROSS=True
								try:
								
									newline=list(geometry.LinearRing(new_pol.exterior.coords).coords)
									tablines[iline][il2test]=newline
									tablines[iline].remove(tablines[iline][il])
									
									break
								
								except:
								
									newline=[]
									l1=tablines[iline][il2test]
									l2=tablines[iline][il]
									dmin=1.e+8
									ip1use=-1
									ip2use=-1
									for ip1 in range(len(l1)):
										for ip2 in range(len(l2)):
											d=sqrt((l1[ip1][0]-l2[ip2][0])**2+(l1[ip1][1]-l2[ip2][1])**2)
											if d<dmin and d<distance:
												ip1use=ip1
												ip2use=ip2
												dmin=d
									for ip1 in range(0,ip1use):
										newline.append(l1[ip1])
										if ip1==ip1use: break
									for ip2 in range(ip2use,ip2use+len(l2)):
										if ip2<len(l2)-1: ipp=ip2
										else: ipp=ip2-len(l2)
										newline.append(l2[ipp])
									for ip1 in range(ip1use+1,len(l1)):
										if ip1<len(l1)-1: ipp=ip1
										else: ipp=ip1-len(l1)
										newline.append(l1[ipp])
		
									tablines[iline][il2test]=newline
									tablines[iline].remove(tablines[iline][il])
									break
		
				if CROSS is False: STILL_CROSS=False

		reflines=[]
		for line in tablines:
			for subline in line: reflines.append(subline)
		
		ntot=len(reflines)
		
		STILL_CROSS=True
		
		while STILL_CROSS:
			
			CROSS=False
			
			if time2use is not None: UpdateProgress(time2use,ithread,1.-float(len(reflines))/ntot,message+' - 2/2')
			
			for il2test in range(len(reflines)):
				
				if CROSS: break
				
				for il in range(len(reflines)):
					
					if il2test!=il:
						
						p1=geometry.Polygon(reflines[il2test])
						p2=geometry.Polygon(reflines[il]) 
						new_pol=ops.cascaded_union([p1,p2])
						
						if p1.distance(p2)<distance/2:
							
							CROSS=True
							try:
							
								newline=list(geometry.LinearRing(new_pol.exterior.coords).coords)
								reflines[il2test]=newline
								reflines.remove(reflines[il])
								
								break
							
							except:
							
								newline=[]
								l1=reflines[il2test]
								l2=reflines[il]
								dmin=1.e+8
								ip1use=-1
								ip2use=-1
								for ip1 in range(len(l1)):
									for ip2 in range(len(l2)):
										d=sqrt((l1[ip1][0]-l2[ip2][0])**2+(l1[ip1][1]-l2[ip2][1])**2)
										if d<dmin and d<distance:
											ip1use=ip1
											ip2use=ip2
											dmin=d
								for ip1 in range(0,ip1use):
									newline.append(l1[ip1])
									if ip1==ip1use: break
								for ip2 in range(ip2use,ip2use+len(l2)):
									if ip2<len(l2)-1: ipp=ip2
									else: ipp=ip2-len(l2)
									newline.append(l2[ipp])
								for ip1 in range(ip1use+1,len(l1)):
									if ip1<len(l1)-1: ipp=ip1
									else: ipp=ip1-len(l1)
									newline.append(l1[ipp])
	
								reflines[il2test]=newline
								reflines.remove(reflines[il])
								break
	
			if CROSS is False: STILL_CROSS=False
			
	newlines=[]
	for line in reflines:
		newline=[]
		for ip in range(len(line)):
			if ip==0: newline.append((line[ip][0],line[ip][1]))
			else:
				dist=sqrt((line[ip][0]-newline[-1][0])**2+(line[ip][1]-newline[-1][1])**2)
				if dist>=distance and line[ip]!=line[0]: newline.append((line[ip][0],line[ip][1]))
			
		dist=sqrt((line[-1][0]-line[0][0])**2+(line[-1][1]-line[0][1])**2)
		if dist<distance: newline.pop()
		
		if len(newline)>2:
			p=geometry.Polygon(list(newline))
			if p.area>20000.: newlines.append(newline)

	if time2use is not None: UpdateProgress(time2use,ithread,1.,' ')
		
	return newlines

def GetDirect(ndirec,input_direc):
	"""
	Returns sector id to use from a direction data
	"""

	sect=360./ndirec
	idir=int((input_direc+sect/2)/sect)
	if idir==ndirec: idir-=ndirec
	return idir

def Harmonize(direc1,direc2):
	"""
	Applies a whole rotation to the direction to make possible direction comparisons
	"""

	if direc1<90 and direc2>270: 	direc1+=360.
	elif direc1>270 and direc2<90:	direc2+=360
	return direc1,direc2

class COUNTER:
	
	def __init__(self):
		
		self.counter_advert_small=[0]*8

def CalcDistMin(pair_list):
	
	n=len(pair_list)
	new_min_dist=float('inf')
	for i in xrange(n):
		for j in xrange(i+1, n):
			new_x_dist=pair_list[i][0]-pair_list[j][0]
			new_y_dist=pair_list[i][1]-pair_list[j][1]
			new_min_dist=min(new_x_dist*new_x_dist+new_y_dist*new_y_dist, new_min_dist)
	return new_min_dist ** 0.5

def parse_latlon(string):
	#https://github.com/NOAA-ORR-ERD/lat_lon_parser
	"""
	Attempts to parse a latitude or longitude string

	Returns the value in floating point degrees

	If parsing fails, it raises a ValueError

	NOTE: This is a naive brute-force approach. And it's quite accepting of
		  non-compliant strings. But that may be a good thing
	"""
	
	# print("starting with:", string)
	orig_string = string

	string = string.strip().lower()
	# replace full cardinal directions:
	string = string.replace('north', 'n')
	string = string.replace('south', 's')
	string = string.replace('east', 'e')
	string = string.replace('west', 'w')

	# change W and S to a negative value
	if string.endswith('w') or string.endswith('s'):
		negative = -1
	else:
		negative = 1
	negative = -1 if string.startswith("-") else negative
	string = string.lstrip("- ")

	# print("after sign stripping", string, negative)
	# get rid of everything that is not numbers
	string = re.sub(r"[^0-9.]", " ", string).strip()
	# print("after stripping non-numbers", string)
	if string == '': raise ValueError('No numeric part was detected')

	parts=[0.,0.,0.]#deg min sec
	for i,part in enumerate(string.split()):
		if i>2: raise ValueError('More than 3 numeric parts were detected')
		parts[i] = float(part)
	if not parts: raise ValueError("{} is not a valid coordinate string".format(orig_string))
	# print("parts", parts)
	
	d,m,s = parts[0],parts[1],parts[2]
	if m < 0 or s < 0:		raise ValueError("Minutes and Seconds have to be positive")
	if m > 60.0 or s > 60.0:raise ValueError("Minutes and Seconds have to be between -180 and 180")
	if abs(d) > 180.:		raise ValueError("Degrees have to be between -180 and 180")
	
	deg_has_fract = bool(modf(d)[0])
	min_has_fract = bool(modf(m)[0])
	
	if deg_has_fract and (m != 0.0 or s != 0.0):
		raise ValueError("degrees cannot have fraction unless both minutes and seconds are zero")
	if min_has_fract and s != 0.0:
		raise ValueError("minutes cannot have fraction unless seconds are zero")

	DecDegrees = negative * (d + m / 60.0 + s / 3600.0)
	
	return DecDegrees

def convert_coords(x,y,inputEPSG=4326,outputEPSG=4326):
	"""
	default EPSG numbers are GPS WGS84
	"""
	
	inSpatialRef=osr.SpatialReference()
	inSpatialRef.ImportFromEPSG(inputEPSG)
	outSpatialRef=osr.SpatialReference()
	outSpatialRef.ImportFromEPSG(outputEPSG)
	coordTransform=osr.CoordinateTransformation(inSpatialRef,outSpatialRef)
	
	point=ogr.Geometry(ogr.wkbPoint)
	if inputEPSG==4326 and OSGEO3:
		point.AddPoint(float(y),float(x))#lat,lon
	else:
		point.AddPoint(float(x),float(y))
	point.Transform(coordTransform)
	if outputEPSG==4326 and OSGEO3:
		y,x = point.GetX(),point.GetY()#lat,lon
	else:
		x,y = point.GetX(),point.GetY()
	
	return x,y#lon,lat

def SaveKmz(name,pic,save_file,lat_min,lat_max,lon_min,lon_max,pic_leg=None):
	
	kml=simplekml.Kml()
	path_pic=kml.addfile(pic)
	ground=kml.newgroundoverlay(name=name)
	ground.camera.latitude=(lat_min+lat_max)/2
	ground.camera.longitude=(lon_min+lon_max)/2
	ground.camera.altitude=30000
	ground.icon.href=path_pic
	ground.latlonbox.west=lon_min
	ground.latlonbox.east=lon_max
	ground.latlonbox.north=lat_min
	ground.latlonbox.south=lat_max
	if pic_leg:
		path_leg=kml.addfile(pic_leg)
		screen=kml.newscreenoverlay(name='Legend')
		screen.icon.href=path_leg
		screen.overlayxy=simplekml.OverlayXY(x=0,y=1,xunits=simplekml.Units.fraction,yunits=simplekml.Units.fraction)
		screen.screenxy=simplekml.ScreenXY(x=15,y=15,xunits=simplekml.Units.pixels,yunits=simplekml.Units.insetpixels)
		screen.size.x,screen.size.x=-1,-1
		screen.size.xunits,screen.size.yunits=simplekml.Units.fraction,simplekml.Units.fraction
	kml.savekmz(save_file)

def InitFileSystem():
	"""
	Checks and generate for mandatory files
	"""

	try:	xml.parse(xmlfileended).getroot()
	except:	xml.ElementTree(xml.Element('processes')).write(xmlfileended)
	try:	xml.parse(xmlfilecloud).getroot()
	except:	xml.ElementTree(xml.Element('processes')).write(xmlfilecloud)
	try:	xml.parse(xmlfileproc).getroot()
	except:	xml.ElementTree(xml.Element('processes')).write(xmlfileproc)
	try:	xml.parse(xmlfilequeue).getroot()
	except:	xml.ElementTree(xml.Element('processes')).write(xmlfilequeue)
	try:	xml.parse(xmlfileold).getroot()
	except:	xml.ElementTree(xml.Element('processes')).write(xmlfileold)
	try: 	xml.parse(xmlfilecontrol).getroot()
	except:
		root=xml.Element('control')
		xml.SubElement(root,'autocontinue').text='True'
		xml.ElementTree(root).write(xmlfilecontrol)
	
	xmlfile=PATH+'../../USERS/machine.xml'
	root=xml.parse(xmlfile).getroot()
	if root.find('machine').text is None:
		text=GetMachine()
		root.find('machine').text=text
		xml.ElementTree(root).write(xmlfile)
		os.system('xmllint --format %s --output %s'%(xmlfile,xmlfile))

def CircleExtern(r):
	num=300
	theta=2 * np.pi / num
	path=[]
	for i in range(num):
		x=r * np.sin(theta * i)
		y=r * np.cos(theta * i)
		path.append((x, y))

	path=path + [path[0]]
	poly=geometry.Polygon(path)
	string=geometry.LineString(path)
	return poly, string

def RectangleExtern(xmin, xmax, ymin, ymax):
	path=[(xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin), (xmin, ymax)]
	poly=geometry.Polygon(path)
	string=geometry.LineString(path)
	return poly, string

def CoverPolygons(res, inpType, value):
	from matplotlib import pyplot
	contour=pyplot.tricontour(res[0], res[1], res[2], [value])

	max_x=max(res[0])
	max_y=max(res[1])
	max_value=max(res[2])

	min_x=min(res[0])
	min_y=min(res[1])
	min_value=min(res[2])

	mid_x, mid_y=(min_x + max_x) / 2.0, (min_y + max_y) / 2.0
	lenth, width=max_x - min_x, max_y - min_y

	if inpType == 'VISU':
		ex_poly, ex_string=CircleExtern(max_x)
	elif inpType == 'MAPPING':
		ex_poly, ex_string=RectangleExtern(min_x, max_x, min_y, max_y)

	TOLERANCE_V=0.001
	if value < min_value + TOLERANCE_V:
		return [ex_poly]
	elif value > max_value - TOLERANCE_V:
		return []

	res=[]
	for collec in contour.collections:
		line=collec.get_paths()
		for path in line:
			v=path.vertices
			x=v[:, 0]
			y=v[:, 1]
			if len(x) > 3:
				res.append(zip(x, y))

	polyWaits=[]

	for line in res:
		if line[0] == line[-1]:
			ring=geometry.LinearRing(line)
			if ring.is_ccw:
				poly=geometry.Polygon(line)
				if not poly.is_valid: poly=poly.buffer(0)
				polyWaits.append(poly)
			else:
				poly2move=geometry.Polygon(line)
				if not poly2move.is_valid: poly2move=poly2move.buffer(0)
				poly=ex_poly.difference(poly2move)
				polyWaits.append(poly)
		else:
			TOLERANCE=0.5
			# deal with open contours
			head, tail=geometry.Point(line[0]), geometry.Point(line[-1])
			dis_head=head.distance(ex_string)
			dis_tail=tail.distance(ex_string)
			if (dis_tail <= TOLERANCE) and (dis_head <= TOLERANCE):
				if inpType == 'VISU':
					if head.x >= 0:
						xplus=max_x
					else:
						xplus=-max_x
					if head.y >= 0:
						yplus=max_y
					else:
						yplus=-max_y

					headfront=(line[0][0] + xplus, line[0][1] + yplus)

					if tail.x >= 0:
						xplus=max_x
					else:
						xplus=-max_x
					if tail.y >= 0:
						yplus=max_y
					else:
						yplus=-max_y

					tailend=(line[-1][0] + xplus, line[-1][1] + yplus)

					if head.x * tail.x < 0 and head.y * tail.y < 0:
						midpoint=(headfront[0], tailend[1])
					else:
						midpoint=(headfront[0] + tailend[0], headfront[1] + tailend[1])

				elif inpType == 'MAPPING':
					if head.x >= mid_x:
						xplus=lenth / 2.0
					else:
						xplus=-lenth / 2.0
					if head.y >= mid_y:
						yplus=width / 2.0
					else:
						yplus=-width / 2.0

					headfront=(line[0][0] + xplus, line[0][1] + yplus)

					if tail.x >= mid_x:
						xplus=lenth / 2.0
					else:
						xplus=-lenth / 2.0
					if tail.y >= mid_y:
						yplus=width / 2.0
					else:
						yplus=-width / 2.0

					tailend=(line[-1][0] + xplus, line[-1][1] + yplus)

					if (head.x - mid_x) * (tail.x - mid_x) < 0 and (head.y - mid_y) * (tail.y - mid_y) < 0:
						midpoint=(headfront[0], tailend[1])
					else:
						midpoint=(headfront[0] + tailend[0], headfront[1] + tailend[1])

				newPath=[midpoint, headfront] + line + [tailend, midpoint]
				ring=geometry.LinearRing(newPath)
				newPoly=geometry.Polygon(newPath)
				if not newPoly.is_valid: newPoly=newPoly.buffer(0)
				if ring.is_ccw:
					poly=newPoly.intersection(ex_poly)
				else:
					poly=ex_poly.difference(newPoly)

				polyWaits.append(poly)
			else:
				print "out of tolerance: ", head, dis_head, tail, dis_tail

	polyWaits2=[]
	#construct shaped by overlapse
	for poly in polyWaits:
		polyRest=list(polyWaits)
		polyRest.remove(poly)
		for poly2 in polyRest:
			if poly.overlaps(poly2):
				poly=poly.intersection(poly2)
		polyWaits2.append(poly)

	polyWaits3=[]
	for item in polyWaits2:
		if type(item) == type(geometry.Polygon()):
			polyWaits3.append(item)
		else:
			for geo in item.geoms:
				if type(geo) == type(geometry.Polygon()):
					polyWaits3.append(geo)

	#check contain relation to remove the repeat shape
	while True:
		count=0
		polyWaits4=[]
		while len(polyWaits3):
			poly=polyWaits3.pop(0)
			for poly2 in polyWaits3:
				if poly.equals(poly2) or poly.contains(poly2) or poly2.contains(poly) or poly.overlaps(poly2):
					polyWaits3.remove(poly2)
					count += 1
					poly=poly.intersection(poly2)
			polyWaits4.append(poly)

		polyWaits3=polyWaits4
		if count == 0: break

	polygons=[]
	for item in polyWaits3:
		if type(item) == type(geometry.Polygon()):
			polygons.append(item)
		else:
			for geo in item.geoms:
				if type(geo) == type(geometry.Polygon()):
					polygons.append(geo)

	return polygons

def GetEpsg(georef,user=None):
	# return the epsg number from the georef name
	if georef in ['No georeference','Fictive georeference']: return None
	epsg=None
	xmlfile=PATH+'../../USERS/default/user.xml'
	if user not in [None,'','root']: 
		xmlfile=PATH+'../../USERS/'+user+'/user.xml'
		root=xml.parse(xmlfile).getroot()
		balgeo=root.find('georef')
		for bal in balgeo:
			if bal.attrib['name']==georef:
				if bal.attrib['code'].split(':')[0]!='EPSG':
					raise ValueError('{}: Not an EPSG georeference'.format(georef))
				epsg=int(bal.attrib['code'].split(':')[-1])
				break
	if epsg==None:
		root=xml.parse(PATH+'../../COMMON/GEOREF/geo_glob.xml').getroot()
		for bal in root:
			if bal.attrib['name']==georef:
				if bal.attrib['code'].split(':')[0]!='EPSG':
					raise ValueError('{}: Not an EPSG georeference'.format(georef))
				epsg=int(bal.attrib['code'].split(':')[-1])
				break
	if epsg==None: raise ValueError('Bad georeference name')
	return epsg

def GeneratorCurves(file_path,density):
	"""
	Corrects the power curve and thrust curve by the air density
	Calculate the power curve following IEC 61400-12
	Closest thrust curve is chosen
	Return 2 curve lists for the 251 wind speeds [0.0,0.1,0.2,...,25.0]
	"""
	
	if not file_path.endswith('.zsgene'):
		raise ValueError('file must be in .zsgene format: {}'.format(file_path))
	if not os.path.isfile(file_path):
		name=os.path.splitext(os.path.basename(file_path))[0].strip()
		db_path=PATH+'../../INPUT_FILES/GENERATOR/'+name+'/'+name+'.zsgene'
		if not os.path.isfile(db_path): raise ValueError('file not found: {}'.format(file_path))
		else: file_path=db_path
		
	with open(file_path,'r') as infile: lines=infile.readlines()
	ref_density,ref_powcurve_list,ref_thrcurve_list=[],[],[]
	for i in range(len(lines))[::4]: ref_density.append(float(lines[i]))
	ref_ws=[float(x) for x in lines[1].split()]
	for i in range(len(lines))[2::4]: ref_powcurve_list.append([float(x) for x in lines[i].split()])
	for i in range(len(lines))[3::4]: ref_thrcurve_list.append([float(x) for x in lines[i].split()])

	distance=9
	for i in range(len(ref_density)):
		if (density-ref_density[i])<distance:
			dens2use=ref_density[i]
			index2use=i
			distance=density-dens2use

	ref_powcurve=ref_powcurve_list[index2use]
	ref_thrcurve=ref_thrcurve_list[index2use]

	x_res=np.linspace(0,25,251)
	x_t=np.array([0.]+ref_ws+[25.])
	thrus=np.array([0.0]+ref_thrcurve+[ref_thrcurve[-1]])

	f_t=interpolate.interp1d(x_t,thrus)
	res_thrucurve=f_t(x_res)

	if ref_powcurve[0]!=0:
		lowest=ref_ws[0]
		ref_ws=[lowest-0.5]+ref_ws
		ref_powcurve=[0]+ref_powcurve

	new_ws=[ws*(dens2use/density)**(1./3.) for ws in ref_ws]

	new_ws=[0.]+new_ws
	powc=[0.]+ref_powcurve
	if new_ws[-1]<25.0:
		new_ws+=[25.]
		powc+=[powc[-1]]
	x_p=np.array(new_ws)
	powcurv=np.array(powc)
	f_p=interpolate.interp1d(x_p,powcurv)
	res_powcurve=f_p(x_res)

	return res_powcurve,res_thrucurve

def AirDensity(elevation,mes_ele,air_dens):
	"""
	Returns density for specified elevation
	"""
	T0	=288.15			#sea level standard temperature
	L	=0.0065			#temperature lapse rate
	g	=9.80665		#gravitational acceleration
	M	=0.0289644		#molar mass
	R	=8.31447		#ideal gas constant
	h1	=elevation		#destination location elevation
	h2	=mes_ele		#mesured location elevation
	ro	=air_dens		#mesured location air density
	return ro*((T0-L*h1)/(T0-L*h2))**(g*M/(R*L)-1)

def GeneratorInfo(file_path):
	
	root=xml.parse(file_path).getroot()
	hubheight=eval(root.find('hubheight').text)
	if type(hubheight)==type([]): hubheight=hubheight[0]
	diametre=eval(root.find('rotor_dia').text)
	return hubheight,diametre

def GeneratorStrategy(file_path,density):
	#Reads a wtg file and returns the StartStopStrategy for the closest air density
	
	density=float(density)
	root=xml.parse(file_path).getroot()
	balises=root.findall('PerformanceTable')
	diff=9
	dens2use=None
	for wtgbal in balises:
		ref_density = wtgbal.attrib.get('AirDensity')
		if ref_density==None: continue
		ref_density = float(ref_density)
		if (density-ref_density)<diff:
			dens2use=ref_density
			bal2use=wtgbal
			diff=density-dens2use
	if dens2use==None:
		raise ValueError('could not find close density: {}'.format(density))
	
	strategy = bal2use.find('StartStopStrategy')
	if strategy == None: return None
	
	ret={}
	ret['low_cut_out']	= float(strategy.attrib.get('LowSpeedCutOut'))
	ret['low_cut_in']	= float(strategy.attrib.get('LowSpeedCutIn'))
	ret['high_cut_in']	= float(strategy.attrib.get('HighSpeedCutIn'))
	ret['high_cut_out']	= float(strategy.attrib.get('HighSpeedCutOut'))
	
	return ret
	

	
class ZephycloudAPIError(RuntimeError):
	""" Specific error for zephycloud api dialog errors"""
	pass
	
	
class ZephycloudSerializer(slumber.serialize.BaseSerializer):
	"""
	Class parsing zephycloud API responses.
	It ensure:
		* deserialisation of json
		* checking response format
		* rendering errors (stderr + exception)
		* get the "data" field as result
	"""
	content_types = [
		"application/json",
		"application/x-javascript",
		"text/javascript",
		"text/x-javascript",
		"text/x-json",
	]
	key = "json"
	
	def loads(self, data):
		try:
			response = json.loads(data)
		except ValueError:
			sys.stderr.write("Zephycloud error detected: response is not a valid json:\n")
			sys.stderr.write(repr(data)+"\n")
			sys.stderr.flush()
			raise ZephycloudAPIError("Zephycloud response is not json", data)
		
		if "success" not in response or "error_msgs" not in response or "data" not in response:
			sys.stderr.write("Zephycloud error detected: Invalid response format:\n")
			sys.stderr.write(repr(response) + "\n")
			sys.stderr.flush()
			raise ZephycloudAPIError("Zephycloud response is not well formatted", data)
		
		if not response["success"]:
			if not response["error_msgs"]:
				response["error_msgs"] = ["Unknown server error"]
			sys.stderr.write("Zephycloud error detected:\n")
			sys.stderr.flush()
		for error_msg in response["error_msgs"]:
			sys.stderr.write("\t"+str(error_msg) + "\n")
		sys.stderr.flush()
		if not response["success"]:
			raise ZephycloudAPIError("Zephycloud errors", "\n".join(response["error_msgs"]))
		return response["data"]
	
	def dumps(self, data):
		return json.dumps(data)
	
	def get_content_type(self):
		if self.content_types is None:
			raise NotImplementedError()
		return self.content_types[0]
	
	def get_serializer(self, name=None, content_type=None):
		return self


def GetZephycloudAPI(server, login, pwd):
	"""
	Get slumber object to use to talk to zephycloud,
	according to environment variables

	:param server: 	The server url to use. Can be overriden with env ZEPHYCLOUD_SERVER
	:type server:	str
	:param login: 	The user login
	:type login:	str
	:param pwd: 	The user password
	:type pwd:		str
	:return: 		The slumber api object
	:rtype:			slumber.API
	"""
	session = requests.Session()
	if "ZEPHYCLOUD_CA_ROOT" in os.environ and os.environ["ZEPHYCLOUD_CA_ROOT"]:
		session.verify = os.environ["ZEPHYCLOUD_CA_ROOT"]

	if "ZEPHYCLOUD_SERVER" in os.environ and os.environ["ZEPHYCLOUD_SERVER"]:
		server = os.environ["ZEPHYCLOUD_SERVER"]

	if "ZEPHYCLOUD_API_VERSION" in os.environ and os.environ["ZEPHYCLOUD_API_VERSION"]:
		api_version = os.environ["ZEPHYCLOUD_API_VERSION"]
	else:
		api_version = "1"

	if not api_version.startswith("v"):
		api_version = "v"+api_version

	server_url = server.rstrip("/")+"/"+api_version+"/"
	if not server_url.startswith("http"):
		server_url = "https://"+server_url
	
	serializer = ZephycloudSerializer()
	api = slumber.API(server_url, auth=(login, pwd), session=session, serializer=serializer, format="json")
	setattr(api, "server", server)#convenience attribute
	
	# All possible exceptions, by abstract level (low to high)
	setattr(api, "http_not_found_error", slumber.exceptions.HttpNotFoundError)
	setattr(api, "error", (urllib3.exceptions.HTTPError,
							requests.exceptions.RequestException,
							slumber.exceptions.SlumberBaseException,
							ZephycloudAPIError))
	setattr(api, "connection_error", (urllib3.exceptions.HTTPError,
										requests.exceptions.RequestException,
										slumber.exceptions.SlumberBaseException))
	setattr(api, "api_error", ZephycloudAPIError)
	return api
	
def GetUITranslator(language='EN'):
	if language in [None,'']: language='EN'
	loc=LANGUAGES.locales[LANGUAGES.codes.index(language)]
	translator = gettext.translation('UI',PATH+'../../COMMON/localedir/',languages=[loc],fallback=True)
	return translator.gettext

def GetParamText(typeset,paramname, language='EN'):
	loc=LANGUAGES.locales[LANGUAGES.codes.index(language)]
	translator = gettext.translation('UI',PATH+'../../COMMON/localedir/',languages=[loc],fallback=True)
	msg = translator.gettext
	
	dd={}
	
	dd['load']={}
	dd['load']['resvisu_crit']=		[msg('Fine'),msg('Medium'),msg('Coarse'),msg('User-Defined')]
	dd['load']['resclose_oro_crit']=[msg('Fine'),msg('Medium'),msg('Coarse'),msg('User-Defined'),msg('Not Yet')]
	dd['load']['reslarge_oro_crit']=[msg('Fine'),msg('Medium'),msg('Coarse'),msg('User-Defined'),msg('Not Yet')]
	dd['load']['resclose_rou_crit']=[msg('Fine'),msg('Medium'),msg('Coarse'),msg('User-Defined'),msg('Not Yet')]
	dd['load']['reslarge_rou_crit']=[msg('Fine'),msg('Medium'),msg('Coarse'),msg('User-Defined'),msg('Not Yet')]
	
	dd['anal']={}
	dd['anal']['rixncalc']=			['360','180','120','90','72']
	dd['anal']['rixnsect']=			['8','12','16','18','24','36','48','72']
	dd['anal']['rixncalc_site']=	['8','12','16','18','24','36','48','72']
	
	dd['mesh01']={}
	dd['mesh01']['insmoo']=			[msg('Flat'),msg('Without'),msg('Smoothed')]
	dd['mesh01']['multizone']=		[msg('Single Zone'),msg('Activated')]
	
	dd['calc01']={}
	dd['calc01']['vbc']=			[msg('ABL Profile'),msg('Uniform')]
	dd['calc01']['kbc']=			[msg('Automatic'),msg('Uniform User')]
	dd['calc01']['rbc']=			[msg('Uniform User'),msg('Uniform Auto'),msg('Local')]
	dd['calc01']['turb']=			['kEpsilon','realizableKE','RNGkEpsilon']
	dd['calc01']['init_vel']=		['No Flow','Vref']
	
	dd['calc01']['grad']=			['Gauss linear',
									'cellMDLimited Gauss linear 0.3',	'cellMDLimited Gauss linear 0.5',	'cellMDLimited Gauss linear 0.7',	'cellMDLimited Gauss linear 1.0',
									'cellLimited Gauss linear 0.3',		'cellLimited Gauss linear 0.5',		'cellLimited Gauss linear 0.7',		'cellLimited Gauss linear 1.0',
									'faceMDLimited Gauss linear 0.3',	'faceMDLimited Gauss linear 0.5',	'faceMDLimited Gauss linear 0.7',	'faceMDLimited Gauss linear 1.0',
									'faceLimited Gauss linear 0.3',		'faceLimited Gauss linear 0.5',		'faceLimited Gauss linear 0.7',		'faceLimited Gauss linear 1.0',
									'leastSquares',
									'cellMDLimited leastSquares 0.3',	'cellMDLimited leastSquares 0.5',	'cellMDLimited leastSquares 0.7',	'cellMDLimited leastSquares 1.0',
									'cellLimited leastSquares 0.3',		'cellLimited leastSquares 0.5',		'cellLimited leastSquares 0.7',		'cellLimited leastSquares 1.0',
									'faceMDLimited leastSquares 0.3',	'faceMDLimited leastSquares 0.5',	'faceMDLimited leastSquares 0.7',	'faceMDLimited leastSquares 1.0',
									'faceLimited leastSquares 0.3',		'faceLimited leastSquares 0.5',		'faceLimited leastSquares 0.7',		'faceLimited leastSquares 1.0',
									'fourth',
									'cellMDLimited fourth 0.3',			'cellMDLimited fourth 0.5',			'cellMDLimited fourth 0.7',			'cellMDLimited fourth 1.0',
									'cellLimited fourth 0.3',			'cellLimited fourth 0.5',			'cellLimited fourth 0.7',			'cellLimited fourth 1.0',
									'faceMDLimited fourth 0.3',			'faceMDLimited fourth 0.5',			'faceMDLimited fourth 0.7',			'faceMDLimited fourth 1.0',
									'faceLimited fourth 0.3',			'faceLimited fourth 0.5',			'faceLimited fourth 0.7',			'faceLimited fourth 1.0'
									]
	dd['calc01']['lap']=			['Gauss linear corrected',
									'Gauss linear limited 1.0',			'Gauss linear limited 0.7',			'Gauss linear limited 0.5',			'Gauss linear limited 0.3'
									]
	dd['calc01']['divu']=			['Gauss linearUpwind grad(U)','Gauss linearUpwind','Gauss linear','Gauss skewLinear','Gauss cubicCorrected',
									'Gauss SFCD','Gauss upwind','Gauss QUICK','TVD schemes','SFCD','NVD schemes']
	dd['calc01']['divk']=			['Gauss upwind','Gauss linear']
	dd['calc01']['diveps']=			['Gauss upwind','Gauss linear']
	dd['calc01']['psol']=			['GAMG','smoothSolver','PBiCGStab','PCG']
	dd['calc01']['ssol']=			['smoothSolver','PBiCG']
	dd['calc01']['ppred']=			['DIC','FDIC','diagonal','none']
	dd['calc01']['spred']=			['DILU','diagonal','none']
	dd['calc01']['psmoo']=			['GaussSeidel','DIC','DICGaussSeidel','FDIC','nonBlockingGaussSeidel','symGaussSeidel']
	dd['calc01']['ssmoo']=			['GaussSeidel','DILU','DILUGaussSeidel','nonBlockingGaussSeidel','symGaussSeidel']
	
	dd['calc01']['grad_init']=		dd['calc01']['grad']
	dd['calc01']['lap_init']=		dd['calc01']['lap']
	dd['calc01']['divu_init']=		dd['calc01']['divu']
	dd['calc01']['divk_init']=		dd['calc01']['divk']
	dd['calc01']['diveps_init']=	dd['calc01']['diveps']
	dd['calc01']['psol_init']=		dd['calc01']['psol']
	dd['calc01']['ssol_init']=		dd['calc01']['ssol']
	dd['calc01']['ppred_init']=		dd['calc01']['ppred']
	dd['calc01']['spred_init']=		dd['calc01']['spred']
	dd['calc01']['psmoo_init']=		dd['calc01']['psmoo']
	dd['calc01']['ssmoo_init']=		dd['calc01']['ssmoo']
	
	dd['mcp_xgb']={}
	dd['mcp_xgb']['opti']=			[msg('Automatic optimization'),msg('Predefined')]
	dd['mcp_xgb']['valid']=			[msg('No validation'),msg('Repeated K-fold cross-validation'),msg('Alternating n-hour slices')]
	
	return dd[typeset][paramname]

def InvestigateConvergence(lv,lk,npt,nmt,nld,nwt):
	
	res_mt,res_wt,vmax=[],[],0.
	if len(lv)>0:
		lmax=min(len(lv),len(lk))
		for ip in range(nmt):
			res_mt.append([])
			icol1=npt*3+ip*9+1;icol2=icol1+1
			icol3=npt*3+ip*9+4;icol4=icol3+1
			icol5=npt*3+ip*9+7;icol6=icol5+1
			for il in range(lmax):
				values=string.translate(lv[il],None,'()').split()
				try: vh1=sqrt(eval(values[icol1])**2+eval(values[icol2])**2)
				except: vh1=0.
				try: vh2=sqrt(eval(values[icol3])**2+eval(values[icol4])**2)
				except: vh2=0.
				try: vh3=sqrt(eval(values[icol5])**2+eval(values[icol6])**2)
				except: vh3=0.
				alpha=AlphaCalc(vh1,vh2,vh3)
				res_mt[-1].append(alpha)
				vmax=max(vmax,vh1,vh2,vh3)
		for ip in range(nld):
			res_mt.append([])
			icol1=npt*3+nmt*9+ip*9+1;icol2=icol1+1
			icol3=npt*3+nmt*9+ip*9+4;icol4=icol3+1
			icol5=npt*3+nmt*9+ip*9+7;icol6=icol5+1
			for il in range(lmax):
				values=string.translate(lv[il],None,'()').split()
				try: vh1=sqrt(eval(values[icol1])**2+eval(values[icol2])**2)
				except: vh1=0.
				try: vh2=sqrt(eval(values[icol3])**2+eval(values[icol4])**2)
				except: vh2=0.
				try: vh3=sqrt(eval(values[icol5])**2+eval(values[icol6])**2)
				except: vh3=0.
				alpha=AlphaCalc(vh1,vh2,vh3)
				res_mt[-1].append(alpha)
				vmax=max(vmax,vh1,vh2,vh3)
		for ip in range(nwt):
			res_wt.append([])
			icol1=npt*3+(nmt+nld)*9+ip*9+1;icol2=icol1+1
			icol3=npt*3+(nmt+nld)*9+ip*9+4;icol4=icol3+1
			icol5=npt*3+(nmt+nld)*9+ip*9+7;icol6=icol5+1
			for il in range(lmax):
				values=string.translate(lv[il],None,'()').split()
				try: vh1=sqrt(eval(values[icol1])**2+eval(values[icol2])**2)
				except: vh1=0.
				try: vh2=sqrt(eval(values[icol3])**2+eval(values[icol4])**2)
				except: vh2=0.
				try: vh3=sqrt(eval(values[icol5])**2+eval(values[icol6])**2)
				except: vh3=0.
				alpha=AlphaCalc(vh1,vh2,vh3)
				res_wt[-1].append(alpha)
				vmax=max(vmax,vh1,vh2,vh3)
	
	return res_mt,res_wt,vmax

def WriteFvSolution(fvpth,dd,lines):
	
	with open(fvpth,'w') as f:
		i=0
		while i<21:
			f.write(lines[i]);i+=1

		f.write('solvers\n')
		f.write('{\n')
		f.write('    p\n')
		f.write(bracks)
		f.write('        solver                '+dd['psol']+';\n')
		f.write('        tolerance             '+dd['tol_p']+';\n')
		f.write('        relTol                '+dd['rtol_p']+';\n')
		
		if dd['psol']=='GAMG':
			f.write('        smoother              '+dd['psmoo']+';\n')
			f.write('        nPreSweeps            '+dd['npre']+';\n')
			f.write('        nPostSweeps           '+dd['npost']+';\n')
			f.write('        cacheAgglomeration    '+'on'+';\n')
			f.write('        agglomerator          '+'faceAreaPair'+';\n')
			f.write('        processorAgglomerator '+'masterCoarsest'+';\n')
			f.write('        nCellsInCoarsestLevel '+'50'+';\n')
			f.write('        mergeLevels           '+'1'+';\n')
		elif dd['psol']=='smoothSolver':
			f.write('        smoother              '+dd['psmoo']+';\n')
		else:
			f.write('        preconditioner        '+dd['ppred']+';\n')
		f.write(bracke)
		f.write('    U\n')
		f.write(bracks)
		f.write('        solver                '+dd['ssol']+';\n')
		f.write('        tolerance             '+dd['tol_s']+';\n')
		f.write('        relTol                '+dd['rtol_s']+';\n')
		if dd['ssol']=='smoothSolver':
			f.write('        smoother              '+dd['ssmoo']+';\n')
			f.write('        nSweeps               '+'1'+';\n')
		else:
			f.write('        preconditioner        '+dd['spred']+';\n')
		f.write(bracke)
		f.write('    k\n')
		f.write(bracks)
		f.write('        solver                '+dd['ssol']+';\n')
		f.write('        tolerance             '+dd['tol_s']+';\n')
		f.write('        relTol                '+dd['rtol_s']+';\n')
		if dd['ssol']=='smoothSolver':
			f.write('        smoother              '+dd['ssmoo']+';\n')
			f.write('        nSweeps               '+'1'+';\n')
		else:
			f.write('        preconditioner        '+dd['spred']+';\n')
		f.write(bracke)
		f.write('    epsilon\n')
		f.write('        {\n')
		f.write('        solver                '+dd['ssol']+';\n')
		f.write('        tolerance             '+dd['tol_s']+';\n')
		f.write('        relTol                '+dd['rtol_s']+';\n')
		if dd['ssol']=='smoothSolver':
			f.write('        smoother              '+dd['ssmoo']+';\n')
			f.write('        nSweeps               '+'1'+';\n')
		else:
			f.write('        preconditioner        '+dd['spred']+';\n')
		f.write(bracke)
		f.write('}\n\n')
		f.write('SIMPLE\n')
		f.write('{\n')
		f.write('    nNonOrthogonalCorrectors %s;\n'%dd['ncor'])
		if dd['simplec']: f.write('    consistent yes;\n')
		f.write('\n')
		f.write('    residualControl\n')
		f.write(bracks)
		f.write('        p            '+dd['cvg_p']+';\n')
		f.write('        U            '+dd['cvg_u']+';\n')
		f.write('        k            '+dd['cvg_k']+';\n')
		f.write('        epsilon      '+dd['cvg_eps']+';\n')
		f.write(bracke)
		f.write('}\n')
		f.write('\n')
		f.write('relaxationFactors\n')
		f.write('{\n')
		f.write('    fields\n')
		f.write(bracks)
		f.write('        p            '+dd['relax_p']+';\n')
		f.write(bracke)
		f.write('    equations\n')
		f.write(bracks)
		f.write('        U            '+dd['relax_u']+';\n')
		f.write('        k            '+dd['relax_k']+';\n')
		f.write('        epsilon      '+dd['relax_eps']+';\n')
		f.write(bracke)
		f.write('}\n')
		
		while i<len(lines):
			f.write(lines[i])
			i+=1

def WriteFvSchemes(fvpth,dd,lines):

	with open(fvpth,'w') as f:
		i=0
		while i<32:
			f.write(lines[i]);i+=1

		f.write('gradSchemes\n')
		f.write('{\n')
		f.write('    default        '+dd['grad']+';\n')
		f.write('}\n')
		f.write('\n')
		f.write('laplacianSchemes\n')
		f.write('{\n')
		f.write('    default        '+dd['lap']+';\n')
		f.write('}\n')
		f.write('snGradSchemes\n')
		f.write('{\n')
		f.write('    default        '+dd['sngrad']+';\n')
		f.write('}\n')
		f.write('\n')
		f.write('divSchemes\n')
		f.write('{\n')
		f.write('    default                         none;\n')
		f.write('    div(phi,U)                      '+dd['divu']+';\n')
		f.write('    div(phi,k)                      '+dd['divk']+';\n')
		f.write('    div(phi,epsilon)                '+dd['diveps']+';\n')
		f.write('    div((nuEff*dev2(T(grad(U)))))    Gauss linear;\n')
		f.write('}\n')

		while i<len(lines):
			f.write(lines[i])
			i+=1


def WriteGeo(p,pth,code,Is3d=True):

	npt			=0
	ncircle		=0
	nlineloop	=0
	nplane		=0
	
	nsect=p.nsect*2
	nc,nc2=4,8

	with open(pth,'w') as f:
	
		f.write('Lc1='+str(1.e+8)+';\n')
	
		if code in ['fine','reduced']:
		
			f.write('Lc2='+str(p.resfine*p.resratio)+';\n')
			f.write('Lc3='+str(p.relax_resfactor*p.resfine*p.resratio)+';\n')
			f.write('Lc4='+str(p.resfine)+';\n')
	
		elif code=='coarse':
		
			f.write('Lc2='+str(p.rescoarse)+';\n')
			f.write('Lc3='+str(p.relax_resfactor*p.rescoarse)+';\n')
	
		angradini=pi/2.0+pi/nc
		angrad=angradini+pi/nc
		x='%.3f'%(p.diaref*cos(angrad)/2.0)
		y='%.3f'%(p.diaref*sin(angrad)/2.0)
		npt+=1
		f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc2};\n')
		for isect in range(nc-1):
			angrad=angradini-2.*isect*pi/nc-pi/nc
			x='%.3f'%(p.diaref*cos(angrad)/2.0)
			y='%.3f'%(p.diaref*sin(angrad)/2.0)
			npt+=1
			f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc2};\n')
	
		angradini=pi/2.0+pi/nsect
		angradpre=angradini+pi/nsect
		x='%.3f'%(p.diadom*cos(angradpre)/2.0)
		y='%.3f'%(p.diadom*sin(angradpre)/2.0)
		npt+=1
		f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc1};\n')
		for isect in range(nsect-1):
			angrad=angradini-2.*isect*pi/nsect-pi/nsect
			x='%.3f'%(p.diadom*cos(angrad)/2.0)
			y='%.3f'%(p.diadom*sin(angrad)/2.0)
			npt+=1
			f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc1};\n')

		angradini=pi/2.0+pi/nc2
		angradpre=angradini+pi/nc2
		x='%.3f'%((p.diaref+p.relax_distratio*(p.diadom-p.diaref))*cos(angradpre)/2.0)
		y='%.3f'%((p.diaref+p.relax_distratio*(p.diadom-p.diaref))*sin(angradpre)/2.0)
		npt+=1
		f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc3};\n')
		for isect in range(nc2-1):
			angrad=angradini-2.*isect*pi/nc2-pi/nc2
			x='%.3f'%((p.diaref+p.relax_distratio*(p.diadom-p.diaref))*cos(angrad)/2.0)
			y='%.3f'%((p.diaref+p.relax_distratio*(p.diadom-p.diaref))*sin(angrad)/2.0)
			npt+=1
			f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc3};\n')
			
		x='%.3f'%0.0
		y='%.3f'%0.0
		npt+=1
		f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc2};\n')
	
		for isect in range(nc):
			ncircle+=1
			ipre=isect+1
			isuiv=isect+2
			if isect==nc-1: isuiv=isect-nc+2
			f.write('Circle('+str(ncircle)+')={'+str(ipre)+','+str(npt)+','+str(isuiv)+'};\n')
		for isect in range(nsect):
			ncircle+=1
			ipre=nc+isect+1
			isuiv= nc+isect+2
			if isect==nsect-1: isuiv=nc+isect-nsect+2
			f.write('Circle('+str(ncircle)+')={'+str(ipre)+','+str(npt)+','+str(isuiv)+'};\n')
		for isect in range(nc2):
			ncircle+=1
			ipre=nc+nsect+isect+1
			isuiv=nc+nsect+isect+2
			if isect==nc2-1: isuiv=nc+nsect+isect-nc2+2
			f.write('Circle('+str(ncircle)+')={'+str(ipre)+','+str(npt)+','+str(isuiv)+'};\n')
	
		nlineloop+=1
		f.write('Line Loop('+str(nlineloop)+')={')
		for i in range(nc-1): f.write(str(i+1)+',')
		f.write(str(nc)+'};\n')
	
		nlineloop+=1
		f.write('Line Loop('+str(nlineloop)+')={')
		for i in range(nsect-1): f.write(str(nc+i+1)+',')
		f.write(str(nsect+nc)+'};\n')

		nlineloop+=1
		f.write('Line Loop('+str(nlineloop)+')={')
		for i in range(nc2-1): f.write(str(nc+nsect+i+1)+',')
		f.write(str(nsect+nc+nc2)+'};\n')
		
		if code=='coarse':
	
			f.write('Plane Surface(1)={-2,-3,-1};\n')
			f.write('Plane Surface(2)={-3,-1};\n')
			f.write('Plane Surface(3)={-1};\n')
	
		else:
			
			if p.resratio==1: 
	
				if code!='reduced':
					nplane+=1
					f.write('Plane Surface('+str(nplane)+')={-2,-3,-1};\n')
					nplane+=1
					f.write('Plane Surface('+str(nplane)+')={-3,-1};\n')
				nplane+=1
				f.write('Plane Surface('+str(nplane)+')={-1};\n')
	
			else:
				
				text=''
				
				for il in range(len(p.reflines)):
				
					ptlines=[]
					for ip in range(len(p.reflines[il])):
						npt+=1
						ptlines.append(npt)
						x='%.3f'%(p.reflines[il][ip][0])
						y='%.3f'%(p.reflines[il][ip][1])
						f.write('Point('+str(npt)+')={'+x+','+y+',0.000,Lc4};\n')
		
					lines=[]
					for iline in range(len(ptlines)-1):
						ncircle+=1
						f.write('Line('+str(ncircle)+')={'+str(ptlines[iline])+','+str(ptlines[iline+1])+'};\n')
						lines.append(ncircle)
					if ptlines[-1]!=ptlines[0]:
						ncircle+=1
						f.write('Line('+str(ncircle)+')={'+str(ptlines[-1])+','+str(ptlines[0])+'};\n')
						lines.append(ncircle)
		
					nlineloop=nlineloop+1
					f.write('Line Loop('+str(nlineloop)+')={')
					for i in range(len(lines)-1): f.write(str(lines[i])+',')
					f.write(str(lines[-1])+'};\n')
					
					text+='-'+str(nlineloop)+','
	
				if code!='reduced':
					nplane+=1
					f.write('Plane Surface('+str(nplane)+')={-2,-3,-1};\n')
					nplane+=1
					f.write('Plane Surface('+str(nplane)+')={-3,-1};\n')
				nplane+=1
				f.write('Plane Surface('+str(nplane)+')={-1,'+text[:-1]+'};\n')
				
				for il in range(len(p.reflines)):
					nplane+=1
					f.write('Plane Surface('+str(nplane)+')={-'+str(il+4)+'};\n')
		
		if Is3d:
		
			f.write('cells[0]=0;\n')
			f.write('heights[0]=0.0;\n')
			if code!='reduced':	f.write('For i In{0:'+str(p.nz-1)+'}\n')
			else:				f.write('For i In{0:'+str(p.nzcst-1)+'}\n')
			f.write('    cells[i]=1;\n')
			if code!='reduced':	f.write('    heights[i]=heights[i-1]+1/'+str(p.nz)+';\n')
			else:				f.write('    heights[i]=heights[i-1]+1/'+str(p.nzcst)+';\n')
			f.write('EndFor\n')
			
			if code=='coarse':
				
				f.write('test1[]=Extrude{0,0,'+str(p.nz)+'}{Surface{1};Layers{cells[],heights[]};Recombine;};\n') 
				f.write('test2[]=Extrude{0,0,'+str(p.nz)+'}{Surface{2};Layers{cells[],heights[]};Recombine;};\n')
				f.write('test3[]=Extrude{0,0,'+str(p.nz)+'}{Surface{3};Layers{cells[],heights[]};Recombine;};\n')
				f.write('Physical Volume("internal")={test1[1],test2[1],test3[1]};\n')
				f.write('Physical Surface("top")={test1[0],test2[0],test3[0]};\n')
				f.write('Physical Surface("ground")={1,2,3};\n')
			
			else:
				if p.resratio==1:
					f.write('test1[]=Extrude{0,0,'+str(p.nz)+'}{Surface{1};Layers{cells[],heights[]};Recombine;};\n') 
					f.write('test2[]=Extrude{0,0,'+str(p.nz)+'}{Surface{2};Layers{cells[],heights[]};Recombine;};\n')
					f.write('test3[]=Extrude{0,0,'+str(p.nz)+'}{Surface{3};Layers{cells[],heights[]};Recombine;};\n')
					f.write('Physical Volume("internal")={test1[1],test2[1],test3[1]};\n')
					f.write('Physical Surface("top")={test1[0],test2[0],test3[0]};\n')
					f.write('Physical Surface("ground")={1,2,3};\n')
				else:
					line1=''
					line2=''
					line3=''
					for iplane in range(nplane):
						if code!='reduced':	f.write('test'+str(iplane+1)+'[]=Extrude{0,0,'+str(p.nz)+'}{Surface{'+str(iplane+1)+'};Layers{cells[],heights[]};Recombine;};\n')
						else:				f.write('test'+str(iplane+1)+'[]=Extrude{0,0,'+str(p.nzprof)+'}{Surface{'+str(iplane+1)+'};Layers{cells[],heights[]};Recombine;};\n')
						line1+='test'+str(iplane+1)+'[1],'
						line2+='test'+str(iplane+1)+'[0],'
						line3+=str(iplane+1)+','
					line1='Physical Volume("internal")={'+line1[:-1]+'};\n'
					line2='Physical Surface("top")={'+line2[:-1]+'};\n'
					line3='Physical Surface("ground")={'+line3[:-1]+'};\n'
					f.write(line1)
					f.write(line2)
					f.write(line3)
			
			if code!='reduced': nsect2use=nsect
			else: nsect2use=4
			for isect in range(nsect2use):
				if isect+1<10:		line='Physical Surface("inout00'+str(isect+1)+'")={test1['+str(nsect2use-isect+1)+']};\n'
				elif isect+1<100:	line='Physical Surface("inout0'+str(isect+1)+'")={test1['+str(nsect2use-isect+1)+']};\n'
				else:				line='Physical Surface("inout'+str(isect+1)+'")={test1['+str(nsect2use-isect+1)+']};\n'
				f.write(line)


def shell_quote(arg):
	"""
	Quote a parameter for shell usage
	Example:
		shell_quote("c'est cool aujourd'hui, il fait beau") => 'c'"'"'est cool aujourd'"'"'hui, il fait beau'

	:param arg:         The argument to quote, required
	:type arg:          str
	:return:            The quoted argument
	:rtype:				str
	"""
	if sys.version_info[0] >= 3:  # Python 3
		import shlex
		return shlex.quote(arg)
	else:  # Python 2
		import pipes
		return pipes.quote(arg)


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


def PrepareSubprocess(prog, *args):
	"""
	Open a subprocess, even for pyc file, in a more robust way

	:param prog:		The script or binary file to call
	:type prog:			str|list[str]
	:param args:		The script arguments
	:type args:			str
	:return:			The parsed arguments
	:rtype:				list[str]
	"""
	if not args and not is_string(prog):
		return PrepareSubprocess(*prog)

	if platform.system().lower() != "linux":
		return [prog] + list(args)
	return DetectExecutableFile(prog) + list(args)


def DetectExecutableFile(prog):
	"""
	Try to detect the good command line to run given file

	:param prog: 	a path to a file to run
	:type prog:		str
	:return:		A list of argument to run this file
	:rtype:			list[str]
	"""

	# Try to ensure executable rights
	real_prog_path = os.path.realpath(prog)
	file_rights = os.stat(real_prog_path).st_mode
	if not bool(file_rights & (stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC)):  # Not all exec rights
		with open(os.devnull, 'w') as dev_null:
			try:  # Try to change rights
				subprocess.call(['chmod', 'a+x', real_prog_path], stdout=dev_null, stderr=dev_null)
			except StandardError:
				pass  # but do nothing on error

	# If classic linux, just run it as usual
	if not WSL.detected():
		return [prog]

	# If it has a python extension, run it with pyton
	if prog.endswith(".py") or prog.endswith(".pyc"):
		return ["python2", prog]

	# Read file to detect format
	file_info = subprocess.check_output(['file', "-b", real_prog_path]).strip()
	if file_info.startswith("ELF "):  # Standard linux binary file
		return [prog]
	if "python" in file_info:  # Python compiled file
		return ["python2", prog]
	if "ASCII text executable":  # simple script
		with open(real_prog_path, "r") as fh:
			shellbang = fh.readline(1024)
		if shellbang.startswith("#!"):
			return shlex.split(shellbang[2:].lstrip()) + [prog]
	# I don't know, play it normally...
	return [prog]


def PrepareShellSubprocess(prog, *args):
	"""
	Try to detect real command to run

	:param prog:		The script or binary file to call
	:type prog:			str
	:param args:		The script arguments
	:type args:			str
	:return:			The command to run
	:rtype:				str
	"""
	cmd_args = shlex.split(prog)
	prog = cmd_args.pop(0)
	real_cmd = DetectExecutableFile(prog) + cmd_args + list(args)
	return " ".join([shell_quote(arg) for arg in real_cmd])


def SubprocessPopen(prog, *args, **kwargs):
	"""
	Open a subprocess, even for pyc file, in a more robust way

	:param prog:		The script or binary file to call
	:type prog:			str|list[str]
	:param args:		The script arguments
	:type args:			str
	:return:			The created process
	:rtype:				subprocess.Process
	"""
	if "shell" in kwargs.keys() and kwargs["shell"]:
		cmd_args = PrepareShellSubprocess(prog, *args)
	else:
		cmd_args = PrepareSubprocess(prog, *args)
	try:
		return subprocess.Popen(cmd_args, **kwargs)
	except StandardError as e:
		sys.stderr.write("Unable to run "+str(prog)+": "+repr(e)+"\n")
		sys.stderr.flush()
		raise


def SubprocessCall(prog, *args, **kwargs):
	"""
	Open a subprocess, even for pyc file, in a more robust way

	:param prog:		The script or binary file to call
	:type prog:			str|list[str]
	:param args:		The script arguments
	:type args:			str
	:return:			The created process
	:rtype:				subprocess.Process
	"""
	if "shell" in kwargs.keys() and kwargs["shell"]:
		cmd_args = PrepareShellSubprocess(prog, *args)
	else:
		cmd_args = PrepareSubprocess(prog, *args)
	try:
		return subprocess.call(cmd_args, **kwargs)
	except StandardError as e:
		sys.stderr.write("Unable to run "+str(prog)+": "+repr(e)+"\n")
		sys.stderr.flush()
		raise
