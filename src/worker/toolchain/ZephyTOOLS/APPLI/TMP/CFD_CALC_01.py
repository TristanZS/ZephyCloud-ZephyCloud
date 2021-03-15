#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ZS_VARIABLES	import *
from ZS_COMMON 		import P_THREAD,CFD_PARAM,GetUITranslator,InvestigateConvergence,WriteFvSolution
from ZS_COMMON		import GetFolderSize,ZipDir,GetMachine,SortXmlData,GetParamText
import pandas as pd
from scipy import interpolate
import shutil,re,contextlib

class PARAM(CFD_PARAM):
	
	def __init__(self,time2use,LOCAL):
		
		CFD_PARAM.__init__(self,'',time2use,LOCAL)
		self.type					='CFD_CALC'
		self.code					='cfd_calc01'
		
		self.meshname			=''
		self.projdir			=''
		self.nproc2use			=1
		self.direction			='0'
		self.direcval			=float(self.direction)
		self.vref				=0.
		self.href				=0.
		self.vbc				=''
		self.kbc				=''
		self.rbc				=''
		self.kval				=0.
		self.rval				=0.
		self.turb				=''
		self.cmu_keps			=0.
		self.c1_keps			=0.
		self.c2_keps			=0.
		self.sigmaeps_keps		=0.
		self.cmu_krea			=0.
		self.a0_krea			=0.
		self.c2_krea			=0.
		self.sigmak_krea		=0.
		self.sigmaeps_krea		=0.
		self.cmu_krng			=0.
		self.c1_krng			=0.
		self.c2_krng			=0.
		self.sigmak_krng		=0.
		self.sigmaeps_krng		=0.
		self.eta0_krng			=0.
		self.beta_krng			=0.
		self.nu					=0.
		self.grad				=''
		self.lap				=''
		self.divu				=''
		self.divk				=''
		self.diveps				=''
		self.grad_init			=''
		self.lap_init			=''
		self.divu_init			=''
		self.divk_init			=''
		self.diveps_init		=''
		self.n_it_max			=0
		self.correctors			=0
		self.cvg_p				=0.
		self.cvg_u				=0.
		self.cvg_k				=0.
		self.cvg_eps			=0.
		self.relax_p			=0.
		self.relax_u			=0.
		self.relax_k			=0.
		self.relax_eps			=0.
		self.init_vel			=0.
		self.init_k				=0.
		self.init_eps			=0.
		self.n_it_max_init		=0
		self.correctors_init	=0
		self.cvg_p_init			=0.
		self.cvg_u_init			=0.
		self.cvg_k_init			=0.
		self.cvg_eps_init		=0.
		self.relax_p_init		=0.
		self.relax_u_init		=0.
		self.relax_k_init		=0.
		self.relax_eps_init		=0.
		self.psol_init			=0
		self.ssol_init			=0
		self.ppred_init			=0
		self.spred_init			=0
		self.psmoo_init			=0
		self.ssmoo_init			=0
		self.psol				=0
		self.ssol				=0
		self.ppred				=0
		self.spred				=0
		self.psmoo				=0
		self.ssmoo				=0
		self.npre_init			=0
		self.npost_init			=0
		self.npre				=0
		self.npost				=0
		self.tol_p_init			=0.
		self.rtol_p_init		=0.
		self.tol_s_init			=0.
		self.rtol_s_init		=0.
		self.tol_p				=0.
		self.rtol_p				=0.
		self.tol_s				=0.
		self.rtol_s				=0.
		self.simplec			=True
		self.simplec_init		=True
		self.priority			=''
		self.machine_filename	=None #path of the file containing the ip of the cluster machines
		self.nbr_machines		=1
		
		self.dirchar=''
		
		self.nsect=0
		
		self.auto_z0=0.01
		
		self.inlet_coarse=[]
		self.outlet_coarse=[]
		self.inout_coarse=[]
		self.roughness_coarse=[]
		self.inlet_fine=[]
		self.outlet_fine=[]
		self.inout_fine=[]
		self.roughness_fine=[]
		self.inlet_reduced=[]
		self.outlet_reduced=[]
		self.inout_reduced=[]
		self.roughness_reduced=[]

		self.nmast=0
		self.nlidar=0
		self.nwt=0
		self.npoint=0
		self.nline=0
		
		self.heights=[]

		self.cvg_rate			=0.
		self.cvg_rate_res		=0.
		self.varlim				='no'
		self.last_it_fine		='0'
		self.last_it_coarse		='0'
		
		self.LIGHT				=False
		self.CFD				=False
		self.VALID_RUN_COARSE	=False
		self.VALID_RUN_FINE		=False
		self.PAUSED				=False
		self.RESTARTED			=False
		self.INIT				=False
		
		self.missing_entities=[]
		
		self.duration_tot		=0.
		self.duration_1			=0.
		self.duration_2			=0.
		self.duration_3			=0.
		self.duration_4			=0.
		self.duration_5			=0.
		self.duration_6			=0.
		self.duration_7			=0.
		self.duration_8			=0.
		self.duration_9			=0.
		self.duration_10		=0.
		self.duration_tot		=0.

@contextlib.contextmanager
def using_machine_file(params, workdir):
	""" Crete and remove machine file in context folder to enable cluster runtime"""
	if params.machine_filename and not os.path.exists("machines"):
		shutil.copy(params.machine_filename, "machines")
	if params.machine_filename and not os.path.exists(os.path.join(workdir, "machines")):
		shutil.copy(params.machine_filename, os.path.join(workdir, "machines"))
	try:
		yield
	finally:
		if params.machine_filename:
			abs_param_file = os.path.abspath(params.machine_filename)
			if os.path.abspath("machines") != abs_param_file and os.path.exists("machines"):
				os.remove("machines")
			workdir_file = os.path.abspath(os.path.join(workdir, "machines"))
			if workdir_file != abs_param_file and os.path.exists(workdir_file):
					os.remove(workdir_file)

class THREAD_Command(P_THREAD):
	
	def __init__(self,command,message):
		
		if isinstance(message, str): message=message.decode('utf-8')
		self.command=command
		self.message=message
		P_THREAD.__init__(self,p.p_pool,p.nprocsample)
	
	def run(self):
		
		ithread=self.prerun()
	
		if p.EXTERN: print self.message
		
		with open(p.logfile,'a') as f: f.write(self.message.encode('utf8')+'\n')

		os.system(self.command)

		self.postrun(ithread)

class THREAD_GetRes(P_THREAD):
	
	def __init__(self,restype,num='0'):
		
		self.restype=restype
		self.num=num
		P_THREAD.__init__(self,p.p_pool,p.nproc2use)
	
	def run(self):
		
		ithread=self.prerun()
	
		if self.restype=='CVG':			GetCvg()
		elif self.restype=='CVG_RES':	GetCvgRes()
		if self.restype=='RESULTS':		GetResults()
		elif self.restype=='SITE':		GetResSite()
		elif self.restype=='MESO':		GetResMeso(self.num)
		elif self.restype=='MAPPING':	GetResMapping(self.num)
		
		self.postrun(ithread)

def Rect2Polar(ux,uy,uz):
	"""
	IEC 61400-12-1:
	Wind direction is defined as the direction from which the wind blows,
	and it is measured clockwise from true geographical north.
	"""
	
	direc=90.-degrees(atan2(-uy,-ux))
	while direc<0: direc+=360.
	while direc>=360: direc-=360.
	vh=sqrt(ux*ux+uy*uy)
	inc=90.-degrees(atan2(vh,uz))
	return direc,inc

def Cart2WindDir(ux,uy):
	"""
	IEC 61400-12-1:
	Wind direction is defined as the direction from which the wind blows,
	and it is measured clockwise from true geographical north.
	"""
	direc=90.-degrees(atan2(-uy,-ux))
	while direc<0: direc+=360.
	while direc>=360: direc-=360.
	
	return direc

def ReadParam():
	
	try:

		init_vel	=GetParamText('calc01','init_vel')
		turb		=GetParamText('calc01','turb')
		vbc			=GetParamText('calc01','vbc')
		kbc			=GetParamText('calc01','kbc')
		rbc			=GetParamText('calc01','rbc')
		grad		=GetParamText('calc01','grad')
		lap			=GetParamText('calc01','lap')
		psol		=GetParamText('calc01','psol')
		ssol		=GetParamText('calc01','ssol')
		psmoo		=GetParamText('calc01','psmoo')
		ssmoo		=GetParamText('calc01','ssmoo')
		ppred		=GetParamText('calc01','ppred')
		spred		=GetParamText('calc01','spred')
		
		sngrad=[]
		for elem in lap: sngrad.append(elem[13:])
		
		tmp=GetParamText('calc01','divu')
		divu=[]
		for elem in tmp: divu.append('bounded '+elem)
	
		tmp=GetParamText('calc01','divk')
		divk=[]
		for elem in tmp: divk.append('bounded '+elem)
	
		tmp=GetParamText('calc01','diveps')
		diveps=[]
		for elem in tmp: diveps.append('bounded '+elem)
	
		p.PAUSED=False
		p.RESTARTED=False
		
		p.text_meso=[]
	
		xmlfile=PATH+'../../APPLI/TMP/'+time2use+'.xml'
		root=xml.parse(xmlfile).getroot()
	
		p.version	=root.find('version').text
		p.user		=root.find('username').text
		p.site		=root.find('sitename').text
		p.name		=root.find('calcname').text
		p.meshname	=root.find('meshname').text
		p.suffix	=root.find('suffix').text
		
		if p.suffix==None: p.suffix=''
	
		p.lname=p.site+'_'+p.name
		p.projdir=os.path.abspath(PATH+'../../PROJECTS_CFD/'+p.site)
	
		p.direction			=root.find('direction').text
		p.vref				=root.find('vref').text
		p.href				=root.find('href').text
		p.vbc				=vbc[int(root.find('vbc').text)]
		p.kbc				=kbc[int(root.find('kbc').text)]
		p.rbc				=rbc[int(root.find('rbc').text)]
		p.kval				=root.find('kval').text
		p.rval				=root.find('rval').text
		p.turb				=turb[int(root.find('turb').text)]
		p.cmu_keps			=root.find('cmu_keps').text
		p.c1_keps			=root.find('c1_keps').text
		p.c2_keps			=root.find('c2_keps').text
		p.sigmaeps_keps		=root.find('sigmaeps_keps').text
		p.cmu_krea			=root.find('cmu_krea').text
		p.a0_krea			=root.find('a0_krea').text
		p.c2_krea			=root.find('c2_krea').text
		p.sigmak_krea		=root.find('sigmak_krea').text
		p.sigmaeps_krea		=root.find('sigmaeps_krea').text
		p.cmu_krng			=root.find('cmu_krng').text
		p.c1_krng			=root.find('c1_krng').text
		p.c2_krng			=root.find('c2_krng').text
		p.sigmak_krng		=root.find('sigmak_krng').text
		p.sigmaeps_krng		=root.find('sigmaeps_krng').text
		p.eta0_krng			=root.find('eta0_krng').text
		p.beta_krng			=root.find('beta_krng').text
		p.nu				=root.find('nu').text
		p.grad				=grad[int(root.find('grad').text)]
		p.lap				=lap[int(root.find('lap').text)]
		p.sngrad			=sngrad[int(root.find('lap').text)]
		p.divu				=divu[int(root.find('divu').text)]
		p.divk				=divk[int(root.find('divk').text)]
		p.diveps			=diveps[int(root.find('diveps').text)]
		p.grad_init			=grad[int(root.find('grad_init').text)]
		p.lap_init			=lap[int(root.find('lap_init').text)]
		p.sngrad_init		=sngrad[int(root.find('lap_init').text)]
		p.divu_init			=divu[int(root.find('divu_init').text)]
		p.divk_init			=divk[int(root.find('divk_init').text)]
		p.diveps_init		=diveps[int(root.find('diveps_init').text)]
		p.n_it_max			=root.find('n_it_max').text
		p.correctors		=root.find('correctors').text
		p.cvg_p				=root.find('cvg_p').text
		p.cvg_u				=root.find('cvg_u').text
		p.cvg_k				=root.find('cvg_k').text
		p.cvg_eps			=root.find('cvg_eps').text
		p.relax_p			=root.find('relax_p').text
		p.relax_u			=root.find('relax_u').text
		p.relax_k			=root.find('relax_k').text
		p.relax_eps			=root.find('relax_eps').text
		p.init_vel			=init_vel[int(root.find('init_vel').text)]
		p.init_k			=root.find('init_k').text
		p.init_eps			=root.find('init_eps').text
		p.n_it_max_init		=root.find('n_it_max_init').text
		p.correctors_init	=root.find('correctors_init').text
		p.cvg_p_init		=root.find('cvg_p_init').text
		p.cvg_u_init		=root.find('cvg_u_init').text
		p.cvg_k_init		=root.find('cvg_k_init').text
		p.cvg_eps_init		=root.find('cvg_eps_init').text
		p.relax_p_init		=root.find('relax_p_init').text
		p.relax_u_init		=root.find('relax_u_init').text
		p.relax_k_init		=root.find('relax_k_init').text
		p.relax_eps_init	=root.find('relax_eps_init').text
		p.psol_init			=psol[int(root.find('psol_init').text)]
		p.ssol_init			=ssol[int(root.find('ssol_init').text)]
		p.ppred_init		=ppred[int(root.find('ppred_init').text)]
		p.spred_init		=spred[int(root.find('spred_init').text)]
		p.psmoo_init		=psmoo[int(root.find('psmoo_init').text)]
		p.ssmoo_init		=ssmoo[int(root.find('ssmoo_init').text)]
		p.psol				=psol[int(root.find('psol').text)]
		p.ssol				=ssol[int(root.find('ssol').text)]
		p.ppred				=ppred[int(root.find('ppred').text)]
		p.spred				=spred[int(root.find('spred').text)]
		p.psmoo				=psmoo[int(root.find('psmoo').text)]
		p.ssmoo				=ssmoo[int(root.find('ssmoo').text)]
		p.npre_init			=root.find('npre_init').text
		p.npost_init		=root.find('npost_init').text
		p.npre				=root.find('npre').text
		p.npost				=root.find('npost').text
		p.tol_p_init		=root.find('tol_p_init').text
		p.rtol_p_init		=root.find('rtol_p_init').text
		p.tol_s_init		=root.find('tol_s_init').text
		p.rtol_s_init		=root.find('rtol_s_init').text
		p.tol_p				=root.find('tol_p').text
		p.rtol_p			=root.find('rtol_p').text
		p.tol_s				=root.find('tol_s').text
		p.rtol_s			=root.find('rtol_s').text
		
		p.LIGHT				=root.find('light').text=='True'
		p.CFD				=root.find('cfd').text=='True'
		p.EXTERN			=root.find('extern').text=='True'
		p.nproc				=int(root.find('nproc').text)
		
		if root.find('simplec')!=None:		p.simplec		=root.find('simplec').text=='True'
		else:								p.simplec		=False
		if root.find('simplec_init')!=None:	p.simplec_init	=root.find('simplec_init').text=='True'
		else:								p.simplec_init	=False
		if root.find('cvg_alpha')!=None:	p.cvg_alpha		=float(root.find('cvg_alpha').text)
		else:								p.cvg_alpha		=float(ddParam['calc01']['cvg_alpha'])
		
		
		p.INIT=int(p.n_it_max_init)!=0
				
		if os.path.exists("machines"):
			p.machine_filename = os.path.abspath("machines")
		elif os.path.exists(os.path.join(expanduser("~"), "machines")):
			p.machine_filename = os.path.join(expanduser("~"), "machines")
		else:
			p.machine_filename = None

		host_nbr_proc = 0
		total_nbr_proc = 0
		machine_count = 0
		if p.machine_filename:
			with open(p.machine_filename, "r") as fh:
				for raw_line in fh:
					line = str(raw_line).strip()
					if line and not line.startswith("#"):
						machine_count += 1
						match = re.search('max-slots *= *([0-9]+)', line)
						if not match:
							raise RuntimeError("bad machines file")
						if machine_count == 1:
							host_nbr_proc = int(match.group(1))
							total_nbr_proc += host_nbr_proc
						else:
							total_nbr_proc += int(match.group(1))
			p.nbr_machines = machine_count
			if machine_count == 0:
				raise RuntimeError("bad machines file")
			
		if p.nproc==0:
			if p.machine_filename:
				p.nproc2use = total_nbr_proc
			elif "DOCKER_WORKER" in os.environ.keys() and os.environ["DOCKER_WORKER"].strip() == "1":
				p.nproc2use = (NCPU - 1)
			else:
				p.nproc2use=(NCPU-1) + NCPU*(p.nbr_machines-1)
		else:
			if p.machine_filename:
				p.nproc2use = p.nproc
			else:
				p.nproc2use= min(NCPU,p.nproc)
		
		p.direcval=float(p.direction)
		if p.direcval<10.: tmp_char='00'+'%.1f'%p.direcval
		elif p.direcval<100.: tmp_char='0'+'%.1f'%p.direcval
		else: tmp_char='%.1f'%p.direcval
		for ichar in range(len(tmp_char)):
			if tmp_char[ichar]!='.': p.dirchar+=tmp_char[ichar]
		
		p.codecalc=p.site+'_D'+p.dirchar+'_S5'+'_'+p.name+'_'+p.meshname+p.suffix
		p.folder=p.projdir+'/CALC/'+p.codecalc+'/'
		
		xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/data.xml'
		root=xml.parse(xmlfile).getroot()
		p.nmast		=int(root.find('n_mast').text)
		p.nlidar	=int(root.find('n_lidar').text)
		p.nwt		=int(root.find('n_wt').text)
		p.npoint	=int(root.find('n_point').text)
		p.nline		=int(root.find('n_line').text)
		p.nmeso		=int(root.find('n_meso').text)
		p.nmapping	=int(root.find('n_mapping').text)
		p.heights	=eval(root.find('heights').text)
	
		if LOCAL and not p.EXTERN:
	
			xmlfile=PATH+'../../USERS/machine.xml'
			root=xml.parse(xmlfile).getroot()
			bal=root.find('machine')
			if bal.text is not None: p.machine=bal.text
			else:
				p.machine=GetMachine()
				bal.text=p.machine
				xml.ElementTree(root).write(xmlfile)
		
		else: p.machine=GetMachine()
	
		
		if os.path.isfile(p.folder+'paused'): p.PAUSED=True
		if os.path.isfile(p.folder+'restarted'): p.RESTARTED=True
		
		p.logfile=p.folder+'log'
		
		if p.EXTERN: print 'START'
	
		if not p.RESTARTED: 
			with open(p.folder+'itstart_i','w') as f: f.write('0')
			with open(p.folder+'itstart_c','w') as f: f.write('0')
			with open(p.logfile,'a') as f: f.write('START\n')
		else:
			with open(p.logfile,'a') as f: f.write('RESTART\n')
	
		if not p.PAUSED and LOCAL:
	
			EXTRA_Q=False
			rootqueue=xml.parse(xmlfilequeue).getroot()
			for bal in rootqueue:
				if bal.attrib['code'] in ['cfd_calc01','cfd_calc02'] and bal.attrib['site']==p.site:
					EXTRA_Q=True
					break
	
			xmlfilecfd=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
			rootcfd=xml.parse(xmlfilecfd).getroot()
			
			for balcfd in rootcfd:
				
				if balcfd.text==p.site:
						
					newtext=''
					if 'Yes' in balcfd.attrib['calculated']:	newtext='Yes'
					else:										newtext='No'
					if EXTRA_Q: newtext+='-Queued'
					newtext+='-Running'
					balcfd.attrib['calculated']=newtext
					xml.ElementTree(rootcfd).write(xmlfilecfd)
					break 
		
			xmlfilelist=PATH+'../../PROJECTS_CFD/'+p.site+'/CALC/calculations.xml'
			rootlist=xml.parse(xmlfilelist).getroot()
			for bal in rootlist:
				if bal.text==p.codecalc:
					bal.attrib['state']='Running'
					bal.attrib['nproc']=str(p.nproc2use)
					bal.attrib['time2use']=time2use
					rootlist=SortXmlData(rootlist)
					xml.ElementTree(rootlist).write(xmlfilelist)
					break
		
		xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/param.xml'
		root=xml.parse(xmlfile).getroot()
		directions=root.find('directions').text[1:-1].split(',')
		ncells=int(root.find('ncells_reduced').text)
		ncellsf=int(root.find('ncells_fine').text)
		p.nsect=2*len(directions)
		
		need=ncells*750./1000000.
		needf=ncellsf*750./1000000.
		
		p.nprocsample=min(((MEMMAX/1024.)-needf)/need,p.nproc2use)
		if p.nprocsample<1: p.nprocsample=1

		p.rmoy=float(root.find('rmoy_int').text)
	
		if p.rbc=='Uniform User':	p.auto_z0=float(p.rval)
		elif p.rbc=='Uniform Auto':	p.auto_z0=p.rmoy
	
		file1=PATH+'../../APPLI/TMP/'+time2use+'.xml'
		subprocess.call(['cp',file1,p.folder+'param.xml'])
		subprocess.call(['cp',file1,p.folder+'actual.xml'])
	
		i=0
		OK=False
		while not OK and i<100:
			i+=1
			try:
				xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/using_calc.xml'
				root=xml.parse(xmlfile).getroot()
				balise=root.find(p.codecalc)
				if balise is None:
					xml.SubElement(root,p.codecalc)
					xml.ElementTree(root).write(xmlfile)
				OK=True
			except: pass
	
		i=0
		OK=False
		while not OK and i<100:
			i+=1
			try:
				xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/meshes.xml'
				root=xml.parse(xmlfile).getroot()
				for bal in root:
					if bal.text==p.site+'_'+p.meshname:
						bal.attrib['used']='Yes'
						break
				xml.ElementTree(root).write(xmlfile)
				OK=True
			except: pass
	
		xmlfile=p.folder+'using_rose.xml'
		root=xml.Element('using_rose')
		xml.ElementTree(root).write(xmlfile)
	except (KeyboardInterrupt, SystemExit): raise
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': ReadParam')
		p.WriteLog(0)

def CalcBC():
	"""
	Defines the boundary conditions
	"""

	try:

		start=time.time()

		inlet	=[]
		outlet	=[]
		direc	=[]
	
		direction=float(p.direction)
		delta=360./p.nsect
		dirinit=-delta
	
		for idir in range(p.nsect):
			dir2write=dirinit+idir*delta
			if dir2write<0: dir2write+=360.
			direc.append(dir2write)
			
		deltamin=360.
		for idir in range(p.nsect):
			if abs(direction-direc[idir])<deltamin:
				deltamin=abs(direction-direc[idir])
				ideltamin=idir
		istart=ideltamin-p.nsect/4
		
		i2write=istart
		if i2write<0: i2write+=p.nsect
		elif i2write>p.nsect-1: i2write-=p.nsect
		inlet.append(i2write+1)  
		for i in range(p.nsect/2-1):
			i2write=istart+i+1
			if(i2write<0): i2write+=p.nsect
			if i2write>p.nsect-1: i2write-=p.nsect
			inlet.append(i2write+1)
			
		istart=i2write+1
		i2write=istart
		if i2write<0: i2write+=p.nsect
		if i2write>p.nsect-1: i2write-=p.nsect
		outlet.append(i2write+1)		
		for i in range(p.nsect/2-1):
			i2write=istart+i+1
			if i2write<0: i2write+=p.nsect
			if i2write>p.nsect-1: i2write-=p.nsect
			outlet.append(i2write+1)

		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/FILES/coarse_ground_bc','r')
		lines=infile.readlines()
		infile.close()
		for i in range(len(lines)): p.roughness_coarse.append('ground_'+lines[i].rstrip())
			
		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/FILES/fine_ground_bc','r')
		lines=infile.readlines()
		infile.close()
		for i in range(len(lines)): p.roughness_fine.append('ground_'+lines[i].rstrip())

		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/FILES/reduced_ground_bc','r')
		lines=infile.readlines()
		infile.close()
		for i in range(len(lines)): p.roughness_reduced.append('ground_'+lines[i].rstrip())
	
		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/FILES/coarse_inout_bc','r')
		lines=infile.readlines()
		infile.close()
		for i in range(len(lines)):
			values=lines[i].split()
			p.inout_coarse.append([])
			p.inout_coarse[i].append(values[0])
			p.inout_coarse[i].append(eval(values[1]))
			p.inout_coarse[i].append(eval(values[2]))
			p.inout_coarse[i].append(eval(values[3]))
	
		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/FILES/fine_inout_bc','r')
		lines=infile.readlines()
		infile.close()
		for i in range(len(lines)):
			values=lines[i].split()
			p.inout_fine.append([])
			p.inout_fine[i].append(values[0])
			p.inout_fine[i].append(eval(values[1]))
			p.inout_fine[i].append(eval(values[2]))
			p.inout_fine[i].append(eval(values[3]))

		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/FILES/reduced_inout_bc','r')
		lines=infile.readlines()
		infile.close()
		for i in range(len(lines)):
			values=lines[i].split()
			p.inout_reduced.append([])
			p.inout_reduced[i].append(values[0])
			p.inout_reduced[i].append(eval(values[1]))
			p.inout_reduced[i].append(eval(values[2]))
			p.inout_reduced[i].append(eval(values[3]))
		
		p.inlet_coarse=[]
		p.outlet_coarse=[]
		p.inlet_fine=[]
		p.outlet_fine=[]
		p.inlet_reduced=[]
		p.outlet_reduced=[]
	
		for i in range(p.nsect/2):
			p.inlet_coarse.append([])
			p.inlet_fine.append([])
			p.outlet_coarse.append([])
			p.outlet_fine.append([])
			numchar=str(inlet[i])
			if len(numchar)==1:
				p.inlet_coarse[i].append('inout00'+numchar)
				p.inlet_fine[i].append('inout00'+numchar)
			elif len(numchar)==2:
				p.inlet_coarse[i].append('inout0'+numchar)
				p.inlet_fine[i].append('inout0'+numchar)
			elif len(numchar)==3:
				p.inlet_coarse[i].append('inout'+numchar)
				p.inlet_fine[i].append('inout'+numchar)
			numchar=str(outlet[i])
			if len(numchar)==1:
				p.outlet_coarse[i].append('inout00'+numchar)
				p.outlet_fine[i].append('inout00'+numchar)
			elif len(numchar)==2:
				p.outlet_coarse[i].append('inout0'+numchar)
				p.outlet_fine[i].append('inout0'+numchar)
			elif len(numchar)==3:
				p.outlet_coarse[i].append('inout'+numchar)
				p.outlet_fine[i].append('inout'+numchar)
			for iinout in range(len(p.inout_coarse)):
				if p.inout_coarse[iinout][0]==p.inlet_coarse[i][0]:
					p.inlet_coarse[i].append(p.inout_coarse[iinout][1])
					p.inlet_coarse[i].append(p.inout_coarse[iinout][2])
					p.inlet_coarse[i].append(p.inout_coarse[iinout][3])
			for iinout in range(len(p.inout_fine)):
				if p.inout_fine[iinout][0]==p.inlet_fine[i][0]:
					p.inlet_fine[i].append(p.inout_fine[iinout][1])
					p.inlet_fine[i].append(p.inout_fine[iinout][2])
					p.inlet_fine[i].append(p.inout_fine[iinout][3])

		for i in range(2):
			p.inlet_reduced.append([])
			p.outlet_reduced.append([])
			numchar=str(i+1)
			if len(numchar)==1:
				p.inlet_reduced[i].append('inout00'+numchar)
			elif len(numchar)==2:
				p.inlet_reduced[i].append('inout0'+numchar)
			elif len(numchar)==3:
				p.inlet_reduced[i].append('inout'+numchar)
			numchar=str(i+3)
			if len(numchar)==1:
				p.outlet_reduced[i].append('inout00'+numchar)
			elif len(numchar)==2:
				p.outlet_reduced[i].append('inout0'+numchar)
			elif len(numchar)==3:
				p.outlet_reduced[i].append('inout'+numchar)
			for iinout in range(len(p.inout_reduced)):
				if p.inout_reduced[iinout][0]==p.inlet_reduced[i][0]:
					p.inlet_reduced[i].append(p.inout_reduced[iinout][1])
					p.inlet_reduced[i].append(p.inout_reduced[iinout][2])
					p.inlet_reduced[i].append(p.inout_reduced[iinout][3])
		
		p.duration_1=time.time()-start
	except (KeyboardInterrupt, SystemExit): raise
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcBC')
		p.WriteLog(0)

def SetCase():
	"""
	Sets OpenFoam cases
	"""
	
	if p.RESTARTED: return
	
	def SetFile_U(level):

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/U','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/0'): subprocess.call(['mkdir','-p',p.folder+level+'/0'])
		outfile=open(p.folder+level+'/0/U','w')
		
		for i in range(30): outfile.write(lines[i])
		
		if level=='COARSE':		n=len(p.roughness_coarse)
		elif level=='FINE':		n=len(p.roughness_fine)
		elif level=='REDUCED':	n=len(p.roughness_reduced)
		for ii in range(n):
			if level=='COARSE': outfile.write('    '+p.roughness_coarse[ii]+'\n')
			elif level=='FINE': outfile.write('    '+p.roughness_fine[ii]+'\n')
			elif level=='REDUCED': outfile.write('    '+p.roughness_reduced[ii]+'\n')
			outfile.write(bracks)
			outfile.write('        type        fixedValue;\n')
			outfile.write('        value       uniform (0 0 0);\n')
			outfile.write(bracke)

		if level=='COARSE': n=len(p.inlet_coarse)
		elif level=='FINE':	n=len(p.inlet_fine)
		elif level=='REDUCED':	n=len(p.inlet_reduced)
		if p.vbc=='ABL Profile':
			for ii in range(n):
				if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
				elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
				elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
				outfile.write(bracks)
				outfile.write('        type        atmBoundaryLayerInletVelocity;\n')
				outfile.write('        Uref        $Uref;\n')
				outfile.write('        Zref        $Zref;\n')
				outfile.write('        flowDir     $flowDir;\n')
				outfile.write('        zDir        $zDir;\n')
				if p.rbc=='Local':
					if level=='COARSE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_coarse[ii][2]+';\n')
					elif level=='FINE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_fine[ii][2]+';\n')
					elif level=='REDUCED':	outfile.write('        z0          uniform    '+'%.8f'%p.inlet_reduced[ii][2]+';\n')
				elif p.rbc=='Upwind':
					if level=='COARSE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_coarse[ii][3]+';\n')
					elif level=='FINE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_fine[ii][3]+';\n')
					elif level=='REDUCED':	outfile.write('        z0          uniform    '+'%.8f'%p.inlet_reduced[ii][3]+';\n')
				else: outfile.write('        z0          uniform    '+'%.8f'%p.auto_z0+';\n')
				
				if level=='COARSE':		outfile.write('        zGround     uniform    '+'%.8f'%p.inlet_coarse[ii][1]+';\n')
				elif level=='FINE':		outfile.write('        zGround     uniform    '+'%.8f'%p.inlet_fine[ii][1]+';\n')
				elif level=='REDUCED':	outfile.write('        zGround     uniform    '+'%.8f'%p.inlet_reduced[ii][1]+';\n')
				outfile.write('        value       $internalField;\n')
				outfile.write(bracke)
			
		elif p.vbc=='Uniform':
			
			for ii in range(n):
				if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
				elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
				elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
				outfile.write(bracks)
				outfile.write('        type     fixedValue;\n')
				outfile.write('        value    $flowVelocity;\n')
				outfile.write(bracke)

		if level=='COARSE':		n=len(p.outlet_coarse)
		elif level=='FINE':		n=len(p.outlet_fine)
		elif level=='REDUCED':	n=len(p.outlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.outlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.outlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.outlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type        zeroGradient;\n')
			outfile.write(bracke)
			
		while i<len(lines): 
			outfile.write(lines[i])
			i+=1
			
		outfile.close()

	def SetFile_k(level):

		vref=eval(p.vref)
		href=eval(p.href)
		kappa=0.4

		if p.turb=='kEpsilon':			Cmu=eval(p.cmu_keps)
		elif p.turb=='RNGkEpsilon':		Cmu=eval(p.cmu_krng)
		elif p.turb=='realizableKE':	Cmu=eval(p.cmu_krea)
		
		infile=open(PATH+'../../COMMON/foam/calc_openfoam/k','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/0'): subprocess.call(['mkdir','-p',p.folder+level+'/0'])
		outfile=open(p.folder+level+'/0/k','w')

		n=29
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1
		
		if level=='COARSE':		n=len(p.roughness_coarse)
		elif level=='FINE':		n=len(p.roughness_fine)
		elif level=='REDUCED':	n=len(p.roughness_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.roughness_coarse[ii]+'\n')
			elif level=='FINE':		outfile.write('    '+p.roughness_fine[ii]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.roughness_reduced[ii]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      kqRWallFunction;\n')
			outfile.write('        value                     $internalField;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.inlet_coarse)
		elif level=='FINE':		n=len(p.inlet_fine)
		elif level=='REDUCED':	n=len(p.inlet_reduced)
		if p.kbc=='Automatic':
				for ii in range(n):
					if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
					elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
					elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
					outfile.write(bracks)
					outfile.write('        type                      uniformFixedValue;\n')
					if p.rbc=='Local':
						if level=='COARSE':		z0=p.inlet_coarse[ii][2]
						elif level=='FINE':		z0=p.inlet_fine[ii][2]
						elif level=='REDUCED':	z0=p.inlet_reduced[ii][2]
						us=vref*kappa/log(href/z0)
						tke=us*us/sqrt(Cmu)
						outfile.write('        value         uniform     '+'%.8f'%tke+';\n')
						outfile.write('        uniformValue  constant    '+'%.8f'%tke+';\n')
					elif p.rbc=='Upwind':
						if level=='COARSE':		z0=p.inlet_coarse[ii][3]
						elif level=='FINE':		z0=p.inlet_fine[ii][3]
						elif level=='REDUCED':	z0=p.inlet_reduced[ii][3]
						us=vref*kappa/log(href/z0)
						tke=us*us/sqrt(Cmu)
						outfile.write('        value         uniform     '+'%.8f'%tke+';\n')
						outfile.write('        uniformValue  constant    '+'%.8f'%tke+';\n')
					else:
						z0=p.auto_z0
						us=vref*kappa/log(href/z0)
						tke=us*us/sqrt(Cmu)
						outfile.write('        value         uniform     '+'%.8f'%tke+';\n')
						outfile.write('        uniformValue  constant    '+'%.8f'%tke+';\n')
					outfile.write(bracke)
		elif p.kbc=='Uniform User':
			tke=float(p.kval)
			for ii in range(n):
				if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
				elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
				elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
				outfile.write(bracks)
				outfile.write('        type                      uniformFixedValue;\n')
				outfile.write('        value         uniform     '+'%.8f'%tke+';\n')
				outfile.write('        uniformValue  constant    '+'%.8f'%tke+';\n')
				outfile.write(bracke)

		if level=='COARSE':		n=len(p.outlet_coarse)
		elif level=='FINE':		n=len(p.outlet_fine)
		elif level=='REDUCED':	n=len(p.outlet_reduced)

		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.outlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.outlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.outlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      zeroGradient;\n')
			outfile.write(bracke)
		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_p(level):

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/p','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/0'): subprocess.call(['mkdir','-p',p.folder+level+'/0'])
		outfile=open(p.folder+level+'/0/p','w')

		n=29
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1

		if level=='COARSE':		n=len(p.roughness_coarse)
		elif level=='FINE':		n=len(p.roughness_fine)
		elif level=='REDUCED':	n=len(p.roughness_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.roughness_coarse[ii]+'\n')
			elif level=='FINE':		outfile.write('    '+p.roughness_fine[ii]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.roughness_reduced[ii]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      zeroGradient;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.inlet_coarse)
		elif level=='FINE':		n=len(p.inlet_fine)
		elif level=='REDUCED':	n=len(p.inlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      zeroGradient;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.outlet_coarse)
		elif level=='FINE':		n=len(p.outlet_fine)
		elif level=='REDUCED':	n=len(p.outlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.outlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.outlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.outlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      uniformFixedValue;\n')
			outfile.write('        value         uniform     $pressure;\n')
			outfile.write('        uniformValue  constant    $pressure;\n')
			outfile.write(bracke)

		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_nut(level):

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/nut','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/0'): subprocess.call(['mkdir','-p',p.folder+level+'/0'])
		outfile=open(p.folder+level+'/0/nut','w')
		
		n=29
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1

		if level=='COARSE':		n=len(p.roughness_coarse)
		elif level=='FINE':		n=len(p.roughness_fine)
		elif level=='REDUCED':	n=len(p.roughness_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.roughness_coarse[ii]+'\n')
			elif level=='FINE':		outfile.write('    '+p.roughness_fine[ii]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.roughness_reduced[ii]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      nutkAtmRoughWallFunction;\n')
			if level=='COARSE':		outfile.write('        z0                        uniform '+p.roughness_coarse[ii][7:]+';\n')
			elif level=='FINE':		outfile.write('        z0                        uniform '+p.roughness_fine[ii][7:]+';\n')
			elif level=='REDUCED':	outfile.write('        z0                        uniform '+p.roughness_reduced[ii][7:]+';\n')
			outfile.write('        value                     uniform 0.0;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.inlet_coarse)
		elif level=='FINE':		n=len(p.inlet_fine)
		elif level=='REDUCED':	n=len(p.inlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      calculated;\n')
			outfile.write('        value                     uniform 0.0;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.outlet_coarse)
		elif level=='FINE':		n=len(p.outlet_fine)
		elif level=='REDUCED':	n=len(p.outlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.outlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.outlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.outlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      calculated;\n')
			outfile.write('        value                     uniform 0.0;\n')
			outfile.write(bracke)

		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_epsilon(level):

		kappa=0.4
		E=9.8

		if p.turb=='kEpsilon':			Cmu=eval(p.cmu_keps)
		elif p.turb=='RNGkEpsilon':		Cmu=eval(p.cmu_krng)
		elif p.turb=='realizableKE':	Cmu=eval(p.cmu_krea)

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/epsilon','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/0'): subprocess.call(['mkdir','-p',p.folder+level+'/0'])
		outfile=open(p.folder+level+'/0/epsilon','w')

		n=30
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1
		
		if level=='COARSE':		n=len(p.roughness_coarse)
		elif level=='FINE':		n=len(p.roughness_fine)
		elif level=='REDUCED':	n=len(p.roughness_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.roughness_coarse[ii]+'\n')
			elif level=='FINE':		outfile.write('    '+p.roughness_fine[ii]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.roughness_reduced[ii]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      epsilonWallFunction;\n')
			outfile.write('        Cmu                       '+'%.5f'%Cmu+';\n')
			outfile.write('        kappa                     '+'%.5f'%kappa+';\n')
			outfile.write('        E                         '+'%.5f'%E+';\n')
			outfile.write('        value                     $internalField;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.inlet_coarse)
		elif level=='FINE':		n=len(p.inlet_fine)
		elif level=='REDUCED':	n=len(p.inlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.inlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.inlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.inlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type        atmBoundaryLayerInletEpsilon;\n')
			outfile.write('        Uref        $Uref;\n')
			outfile.write('        Zref        $Zref;\n')
			outfile.write('        flowDir     $flowDir;\n')
			outfile.write('        zDir     $zDir;\n')
			if p.rbc=='Local': 
				if level=='COARSE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_coarse[ii][2]+';\n')
				elif level=='FINE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_fine[ii][2]+';\n')
				elif level=='REDUCED':	outfile.write('        z0          uniform    '+'%.8f'%p.inlet_reduced[ii][2]+';\n')
			elif p.rbc=='Upwind': 
				if level=='COARSE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_coarse[ii][3]+';\n')
				elif level=='FINE':		outfile.write('        z0          uniform    '+'%.8f'%p.inlet_fine[ii][3]+';\n')
				elif level=='REDUCED':	outfile.write('        z0          uniform    '+'%.8f'%p.inlet_reduced[ii][3]+';\n')
			else: outfile.write('        z0          uniform    '+'%.8f'%p.auto_z0+';\n')
			if level=='COARSE':		outfile.write('        zGround     uniform    '+'%.8f'%p.inlet_coarse[ii][1]+';\n')
			elif level=='FINE':		outfile.write('        zGround     uniform    '+'%.8f'%p.inlet_fine[ii][1]+';\n')
			elif level=='REDUCED':	outfile.write('        zGround     uniform    '+'%.8f'%p.inlet_reduced[ii][1]+';\n')
			outfile.write('        value       $internalField;\n')
			outfile.write(bracke)

		if level=='COARSE':		n=len(p.outlet_coarse)
		elif level=='FINE':		n=len(p.outlet_fine)
		elif level=='REDUCED':	n=len(p.outlet_reduced)
		for ii in range(n):
			if level=='COARSE':		outfile.write('    '+p.outlet_coarse[ii][0]+'\n')
			elif level=='FINE':		outfile.write('    '+p.outlet_fine[ii][0]+'\n')
			elif level=='REDUCED':	outfile.write('    '+p.outlet_reduced[ii][0]+'\n')
			outfile.write(bracks)
			outfile.write('        type                      zeroGradient;\n')
			outfile.write(bracke)
		
		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_transportProperties(level):

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/transportProperties','r')
		lines=infile.readlines()
		infile.close()

		outfile=open(p.folder+level+'/constant/transportProperties','w')

		n=18
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1

		outfile.write('        nu              [0 2 -1 0 0 0 0] '+p.nu+';\n')

		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_turbulenceProperties(level):

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/turbulenceProperties','r')
		lines=infile.readlines()
		infile.close()
		
		outfile=open(p.folder+level+'/constant/turbulenceProperties','w')

		n=21
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1
		
		outfile.write('\n    RASModel            '+p.turb+';\n\n')
		outfile.write('    '+p.turb+'Coeffs\n')
		outfile.write('    {\n')
		
		
		if p.turb=='kEpsilon':
			
			outfile.write('    Cmu            '+p.cmu_keps+';\n')
			outfile.write('    C1             '+p.c1_keps+';\n')
			outfile.write('    C2             '+p.c2_keps+';\n')
			outfile.write('    sigmaEps       '+p.sigmaeps_keps+';\n')
			
		elif p.turb=='RNGkEpsilon':
			outfile.write('    Cmu            '+p.cmu_krng+';\n')
			outfile.write('    C1             '+p.c1_krng+';\n')
			outfile.write('    C2             '+p.c2_krng+';\n')
			outfile.write('    sigmak         '+p.sigmak_krng+';\n')
			outfile.write('    sigmaEps       '+p.sigmaeps_krng+';\n')
			outfile.write('    eta0           '+p.eta0_krng+';\n')
			outfile.write('    beta           '+p.beta_krng+';\n')
			
		elif p.turb=='realizableKE':
			outfile.write('    Cmu            '+p.cmu_krea+';\n')
			outfile.write('    A0             '+p.a0_krea+';\n')
			outfile.write('    C2             '+p.c2_krea+';\n')
			outfile.write('    sigmak         '+p.sigmak_krea+';\n')
			outfile.write('    sigmaEps       '+p.sigmaeps_krea+';\n')
		
		outfile.write('    }\n')

		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_ABLConditions(level):

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/ABLConditions','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/0/include'): subprocess.call(['mkdir','-p',p.folder+level+'/0/include'])
		outfile=open(p.folder+level+'/0/include/ABLConditions','w')

		direction=eval(p.direction)
		ux=-sin(direction*pi/180.)
		uy=-cos(direction*pi/180.)

		n=8
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1
		
		outfile.write('Uref            '+p.vref+';\n')
		outfile.write('Zref            '+p.href+';\n')
		outfile.write('flowDir         '+'('+str(ux)+' '+str(uy)+' 0);\n')
		outfile.write('zDir            '+'(0 0 1);\n')

		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_initialConditions(level):

		vref=float(p.vref)
		tke=float(p.init_k)
		eps=float(p.init_eps)
		
		if tke<0:
			vref=float(p.vref)
			href=float(p.href)
			kappa=0.4
			if p.turb=='kEpsilon':			Cmu=float(p.cmu_keps)
			elif p.turb=='RNGkEpsilon':		Cmu=float(p.cmu_krng)
			elif p.turb=='realizableKE':	Cmu=float(p.cmu_krea)
			us=vref*kappa/log(href/p.rmoy)
			tke=us*us/sqrt(Cmu)

		if eps<0: eps=0.2

		infile=open(PATH+'../../COMMON/foam/calc_openfoam/initialConditions','r')
		lines=infile.readlines()
		infile.close()
		
		if not os.path.isdir(p.folder+level+'/include/0'): subprocess.call(['mkdir','-p',p.folder+level+'/include/0'])
		outfile=open(p.folder+level+'/0/include/initialConditions','w')

		if p.init_vel=='No Flow': vref=1.e-8

		direction=float(p.direction)
		ux=-sin(direction*pi/180.)
		uy=-cos(direction*pi/180.)

		n=8
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1

		outfile.write('flowVelocity                '+'('+str(ux*vref)+' '+str(uy*vref)+' 0);\n')
		outfile.write('pressure                    0;\n')
		outfile.write('turbulentKE                 '+'%.8f'%tke+';\n')
		outfile.write('turbulentEpsilon            '+'%.8f'%eps+';\n')


		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_fvSolution(level):
		
		dd={}
		
		if level=='COARSE':
			dd['ncor']		= p.correctors_init
			dd['cvg_p']		= p.cvg_p_init
			dd['cvg_u']		= p.cvg_u_init
			dd['cvg_k']		= p.cvg_k_init
			dd['cvg_eps']	= p.cvg_eps_init
			dd['relax_p']	= p.relax_p_init
			dd['relax_u']	= p.relax_u_init
			dd['relax_k']	= p.relax_k_init
			dd['relax_eps']	= p.relax_eps_init
			dd['psol']		= p.psol_init
			dd['ppred']		= p.ppred_init
			dd['psmoo']		= p.psmoo_init
			dd['tol_p']		= p.tol_p_init
			dd['rtol_p']	= p.rtol_p_init
			dd['npre']		= p.npre_init
			dd['npost']		= p.npost_init
			dd['ssol']		= p.ssol_init
			dd['spred']		= p.spred_init
			dd['ssmoo']		= p.ssmoo_init
			dd['tol_s']		= p.tol_s_init
			dd['rtol_s']	= p.rtol_s_init
			dd['simplec']	= p.simplec_init
		elif level in ['FINE','REDUCED']:
			dd['ncor']		= p.correctors
			dd['cvg_p']		= p.cvg_p
			dd['cvg_u']		= p.cvg_u
			dd['cvg_k']		= p.cvg_k
			dd['cvg_eps']	= p.cvg_eps
			dd['relax_p']	= p.relax_p
			dd['relax_u']	= p.relax_u
			dd['relax_k']	= p.relax_k
			dd['relax_eps']	= p.relax_eps
			dd['psol']		= p.psol
			dd['ppred']		= p.ppred
			dd['psmoo']		= p.psmoo
			dd['tol_p']		= p.tol_p
			dd['rtol_p']	= p.rtol_p
			dd['npre']		= p.npre
			dd['npost']		= p.npost
			dd['ssol']		= p.ssol
			dd['spred']		= p.spred
			dd['ssmoo']		= p.ssmoo
			dd['tol_s']		= p.tol_s
			dd['rtol_s']	= p.rtol_s
			dd['simplec']	= p.simplec
		
		with open(PATH+'../../COMMON/foam/calc_openfoam/fvSolution','r') as f: lines=f.readlines()
		
		fvpth=p.folder+level+'/system/fvSolution'
		
		WriteFvSolution(fvpth,dd,lines)

	def SetFile_fvSchemes(level):

		if level=='COARSE':
			grad		=p.grad_init
			lap			=p.lap_init
			sngrad		=p.sngrad_init
			divu		=p.divu_init
			divk		=p.divk_init
			diveps		=p.diveps_init
		elif level in ['FINE','REDUCED']:
			grad		=p.grad
			lap			=p.lap
			sngrad		=p.sngrad
			divu		=p.divu
			divk		=p.divk
			diveps		=p.diveps
		
		infile=open(PATH+'../../COMMON/foam/calc_openfoam/fvSchemes','r')
		lines=infile.readlines()
		infile.close()
		
		outfile=open(p.folder+level+'/system/fvSchemes','w')

		n=32
		i=0
		while i<n:
			outfile.write(lines[i])
			i+=1
		
		outfile.write('gradSchemes\n')
		outfile.write('{\n')
		outfile.write('    default        '+grad+';\n')
		outfile.write('}\n')
		outfile.write('\n')
		outfile.write('laplacianSchemes\n')
		outfile.write('{\n')
		outfile.write('    default        '+lap+';\n')
		outfile.write('}\n')
		outfile.write('snGradSchemes\n')
		outfile.write('{\n')
		outfile.write('    default        '+sngrad+';\n')
		outfile.write('}\n')
		outfile.write('\n')
		outfile.write('divSchemes\n')
		outfile.write('{\n')
		outfile.write('    default                         none;\n')
		outfile.write('    div(phi,U)                      '+divu+';\n')
		outfile.write('    div(phi,k)                      '+divk+';\n')
		outfile.write('    div(phi,epsilon)                '+diveps+';\n')
		outfile.write('    div((nuEff*dev2(T(grad(U)))))    Gauss linear;\n')
		outfile.write('}\n')
		
		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetFile_boundary(level):
		
		infile=open(p.folder+level+'/constant/polyMesh/boundary','r')
		lines=infile.readlines()
		infile.close()

		if		level=='COARSE':	nrou=len(p.roughness_coarse)
		elif 	level=='FINE':		nrou=len(p.roughness_fine)
		elif 	level=='REDUCED':	nrou=len(p.roughness_reduced)
			
		n=19
		outfile=open(p.folder+level+'/constant/polyMesh/boundary','w')
		for i in range(n):
			outfile.write(lines[i])
		ii=0
		while ii<nrou:
			i+=1
			outfile.write(lines[i])
			i+=1
			outfile.write(lines[i])
			i+=1
			outfile.write('        type            wall;\n')
			i+=2
			outfile.write(lines[i])
			i+=1
			outfile.write(lines[i])
			i+=1
			outfile.write(lines[i])
			ii=ii+1
		i+=1
		while i<len(lines):
			outfile.write(lines[i])
			i+=1
		outfile.close()

	def SetDict_control(level):

		xprobe=[]
		yprobe=[]
		zprobe=[]
		liste_label=[]

		if p.npoint>0:

			liste_hp=[]
			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zspoint','r')
			lines=infile.readlines()
			infile.close()
			for i in range(p.npoint):
				values=lines[i].split()
				liste_hp.append(float(values[2]))
				liste_label.append(values[3])

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_point','r')
			lines=infile.readlines()
			infile.close()
			
			for i in range(len(lines)):
				values=lines[i].split()
				x=float(values[0])
				y=float(values[1])
				z=float(values[2])
				z+=liste_hp[i]
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z)

		if p.nmast>0:

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmast','r')
			lines=infile.readlines()
			infile.close()
			for i in range(p.nmast): values=lines[i].split()

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_mast','r')
			lines=infile.readlines()
			infile.close()

			for i in range(p.nmast):
				values=lines[i].split()
				x=float(values[0])
				y=float(values[1])
				z=float(values[2])
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+40.)
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+80.)
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+120.)

		if p.nlidar>0:

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zslidar','r')
			lines=infile.readlines()
			infile.close()
			for i in range(p.nlidar): values=lines[i].split()

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_lidar','r')
			lines=infile.readlines()
			infile.close()

			for i in range(p.nlidar):
				values=lines[i].split()
				x=float(values[0])
				y=float(values[1])
				z=float(values[2])
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+40.)
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+80.)
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+120.)

		if p.nwt>0:

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zswt','r')
			lines=infile.readlines()
			infile.close()
			for i in range(p.nwt): values=lines[i].split()

			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_wt','r')
			lines=infile.readlines()
			infile.close()

			for i in range(p.nwt):
				values=lines[i].split()
				x=float(values[0])
				y=float(values[1])
				z=float(values[2])
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+40.)
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+80.)
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z+120.)

		if level=='COARSE':					nit=str(abs(int(p.n_it_max_init)))
		elif level in ['FINE','REDUCED']:	nit=str(abs(int(p.n_it_max)))
		
		infile=open(PATH+'../../COMMON/foam/calc_openfoam/controlDict','r')
		lines=infile.readlines()
		infile.close()
		
		outfile=open(p.folder+level+'/system/controlDict','w')

		n=46
		i=0
		while i<24:
			outfile.write(lines[i])
			i+=1
		outfile.write('endTime         '+nit+';\n')

		i+=1
		while i<30:
			outfile.write(lines[i])
			i+=1
		outfile.write('writeInterval   '+nit+';\n')

		i+=1
		while i<n:
			outfile.write(lines[i])
			i+=1

		outfile.write('libs ("libatmosphericModels.so");\n\n')
		
		outfile.write('functions\n')
		outfile.write('{\n')
		outfile.write('  probes\n')
		outfile.write('  {\n')
		outfile.write('    type probes;\n')
		outfile.write('    functionObjectLibs ("libsampling.so");\n')
		outfile.write('    writeControl timeStep;\n')
		outfile.write('    writeInterval 5;\n')
		outfile.write('    probeLocations\n')
		outfile.write('    (\n')
		for ii in range(len(xprobe)):
			outfile.write('        ( '+str(xprobe[ii])+' '+str(yprobe[ii])+' '+str(zprobe[ii])+')\n')
		outfile.write('    );\n')
		outfile.write('    fields\n')
		outfile.write('    (\n')
		outfile.write('        U\n')
		outfile.write('        k\n')
		outfile.write('    );\n')
		outfile.write('  }\n')
		outfile.write('}\n')
		outfile.close()

	def SetDict_sample(level):

		def SampleProfiles():

			
			liste_hp=[]
			
			if p.npoint>0:
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zspoint','r')
				lines=infile.readlines()
				infile.close()
				for i in range(p.npoint):
					values=lines[i].split()
					liste_hp.append(float(values[2]))

			xprobe=[]
			yprobe=[]
			zprobe=[]
			
			if p.nmast>0:

				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_mast','r')
				lines=infile.readlines()
				infile.close()
				
				for i in range(len(lines)):
					values=lines[i].split()
					x=round(float(values[0]),1)
					y=round(float(values[1]),1)
					z=float(values[2])
					hp=0.
					i=1
					while i<211:
						hp=211.-i
						zp=z+hp
						xprobe.append(x)
						yprobe.append(y)
						zprobe.append(zp)
						i+=1

			if p.nlidar>0:

				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_lidar','r')
				lines=infile.readlines()
				infile.close()
				
				for i in range(len(lines)):
					values=lines[i].split()
					x=round(float(values[0]),1)
					y=round(float(values[1]),1)
					z=float(values[2])
					hp=0.
					i=1
					while i<211:
						hp=211.-i
						zp=z+hp
						xprobe.append(x)
						yprobe.append(y)
						zprobe.append(zp)
						i+=1

			if p.nwt>0:

				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_wt','r')
				lines=infile.readlines()
				infile.close()
				
				for i in range(len(lines)):
					values=lines[i].split()
					x=round(float(values[0]),1)
					y=round(float(values[1]),1)
					z=float(values[2])
					hp=0.
					i=1
					while i<211:
						hp=211.-i
						zp=z+hp
						xprobe.append(x)
						yprobe.append(y)
						zprobe.append(zp)
						i+=1

			if p.npoint>0:

				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_point','r')
				lines=infile.readlines()
				infile.close()
				
				for i in range(len(lines)):
					values=lines[i].split()
					x=round(float(values[0]),1)
					y=round(float(values[1]),1)
					z=float(values[2])
					if liste_hp[i]<10:
						xprobe.append(x)
						yprobe.append(y)
						zprobe.append(z+liste_hp[i])
					else:
						for ih in range(20):
							had=liste_hp[i]+10.-ih
							xprobe.append(x)
							yprobe.append(y)
							zprobe.append(z+had)

			infile=open(PATH+'../../COMMON/foam/calc_openfoam/sampleDict','r')
			lines=infile.readlines()
			infile.close()
		
			outfile=open(p.folder+level+'/system/sampleDict_RESULTS','w')
	
			n=30
			i=0
			while i<n:
				outfile.write(lines[i])
				i+=1
	
			outfile.write('sets\n')
			outfile.write('(\n')
			outfile.write('  results\n')
			outfile.write('  {\n')
			outfile.write('    type    points;\n')
			outfile.write('    functionObjectLibs ("libsampling.so");\n')
			outfile.write('    axis    xyz;\n')
			outfile.write('    ordered yes;\n')
			outfile.write('    points (\n')
			for ip in range(len(xprobe)):
				outfile.write('        ( '+str(xprobe[ip])+' '+str(yprobe[ip])+' '+str(zprobe[ip])+' )\n')
			outfile.write('    );\n')
			outfile.write('  }\n')
			outfile.write(');\n')
			
			while i<len(lines):
				outfile.write(lines[i])
				i+=1
			outfile.close()

		def SampleMapping():

			liste_hp=[]
			liste_dp=[]
			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmapping','r')
			lines=infile.readlines()
			infile.close()
			for i in range(p.nmapping):
				values=lines[i].split()
				liste_hp.append(float(values[5]))
				liste_dp.append(float(values[6]))
	
			for imap in range(p.nmapping):
	
				xprobe=[]
				yprobe=[]
				zprobe=[]
				zprobeup=[]
				zprobedown=[]
	
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_mapping_'+str(imap),'r')
				lines=infile.readlines()
				infile.close()
				
				for i in range(len(lines)):
					values=lines[i].split()
					x=round(float(values[0]),1)
					y=round(float(values[1]),1)
					z=float(values[2])
					xprobe.append(x)
					yprobe.append(y)
					zprobe.append(z+liste_hp[imap])
					zprobeup.append(z+liste_hp[imap]+liste_dp[imap]/2.)
					zprobedown.append(z+liste_hp[imap]-liste_dp[imap]/2.)

				infile=open(PATH+'../../COMMON/foam/calc_openfoam/sampleDict','r')
				lines=infile.readlines()
				infile.close()
			
				outfile=open(p.folder+level+'/system/sampleDict_MAPPING_'+str(imap),'w')
				
				n=30
				i=0
				while i<n:
					outfile.write(lines[i])
					i+=1
				outfile.write('sets\n')
				outfile.write('(\n')
				outfile.write('  results\n')
				outfile.write('  {\n')
				outfile.write('    type    points;\n')
				outfile.write('    functionObjectLibs ("libsampling.so");\n')
				outfile.write('    axis    xyz;\n')
				outfile.write('    ordered yes;\n')
				outfile.write('    points (\n')
				for ip in range(len(xprobe)): outfile.write('        ( '+str(xprobe[ip])+' '+str(yprobe[ip])+' '+str(zprobe[ip])+' )\n')
				outfile.write('    );\n')
				outfile.write('  }\n')
				outfile.write(');\n')
				while i<len(lines):
					outfile.write(lines[i])
					i+=1
				outfile.close()

				outfile=open(p.folder+level+'/system/sampleDict_MAPPING_'+str(imap)+'_down','w')
				
				n=30
				i=0
				while i<n:
					outfile.write(lines[i])
					i+=1
				outfile.write('sets\n')
				outfile.write('(\n')
				outfile.write('  results\n')
				outfile.write('  {\n')
				outfile.write('    type    points;\n')
				outfile.write('    functionObjectLibs ("libsampling.so");\n')
				outfile.write('    axis    xyz;\n')
				outfile.write('    ordered yes;\n')
				outfile.write('    points (\n')
				for ip in range(len(xprobe)): outfile.write('        ( '+str(xprobe[ip])+' '+str(yprobe[ip])+' '+str(zprobedown[ip])+' )\n')
				outfile.write('    );\n')
				outfile.write('  }\n')
				outfile.write(');\n')
				while i<len(lines):
					outfile.write(lines[i])
					i+=1
				outfile.close()

				outfile=open(p.folder+level+'/system/sampleDict_MAPPING_'+str(imap)+'_up','w')
				
				n=30
				i=0
				while i<n:
					outfile.write(lines[i])
					i+=1
				outfile.write('sets\n')
				outfile.write('(\n')
				outfile.write('  results\n')
				outfile.write('  {\n')
				outfile.write('    type    points;\n')
				outfile.write('    functionObjectLibs ("libsampling.so");\n')
				outfile.write('    axis    xyz;\n')
				outfile.write('    ordered yes;\n')
				outfile.write('    points (\n')
				for ip in range(len(xprobe)): outfile.write('        ( '+str(xprobe[ip])+' '+str(yprobe[ip])+' '+str(zprobeup[ip])+' )\n')
				outfile.write('    );\n')
				outfile.write('  }\n')
				outfile.write(');\n')
				while i<len(lines):
					outfile.write(lines[i])
					i+=1
				outfile.close()

		def SampleMeso():

			liste_hmes=[]
			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmeso','r')
			lines=infile.readlines()
			infile.close()
			for i in range(p.nmeso):
				values=lines[i].split()
				liste_hmes.append(float(values[2]))

			for imes in range(p.nmeso):
	
				xprobe=[]
				yprobe=[]
				zprobe=[]
	
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_meso_'+str(imes),'r')
				lines=infile.readlines()
				infile.close()
				
				for i in range(len(lines)):
					values=lines[i].split()
					x=round(float(values[0]),1)
					y=round(float(values[1]),1)
					z=float(values[2])
					z+=liste_hmes[imes]
					xprobe.append(x)
					yprobe.append(y)
					zprobe.append(z)

				infile=open(PATH+'../../COMMON/foam/calc_openfoam/sampleDict','r')
				lines=infile.readlines()
				infile.close()
			
				outfile=open(p.folder+level+'/system/sampleDict_MESO_'+str(imes),'w')
	
				n=30
				i=0
				while i<n:
					outfile.write(lines[i])
					i+=1
	
				outfile.write('sets\n')
				outfile.write('(\n')
				outfile.write('  results\n')
				outfile.write('  {\n')
				outfile.write('    type    points;\n')
				outfile.write('    functionObjectLibs ("libsampling.so");\n')
				outfile.write('    axis    xyz;\n')
				outfile.write('    ordered yes;\n')
				outfile.write('    points (\n')
				for ip in range(len(xprobe)):
					outfile.write('        ( '+str(xprobe[ip])+' '+str(yprobe[ip])+' '+str(zprobe[ip])+' )\n')
				outfile.write('    );\n')
				outfile.write('  }\n')
				outfile.write(');\n')
				
				while i<len(lines):
					outfile.write(lines[i])
					i+=1
				outfile.close()

		def SampleSite():

			xprobe=[]
			yprobe=[]
			zprobe=[]
	
			infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_site','r')
			lines=infile.readlines()
			infile.close()

			for line in lines:
				values=line.split()
				x=round(float(values[0]),1)
				y=round(float(values[1]),1)
				z=float(values[2])
				xprobe.append(x)
				yprobe.append(y)
				zprobe.append(z)

			infile=open(PATH+'../../COMMON/foam/calc_openfoam/sampleDict','r')
			lines=infile.readlines()
			infile.close()

			for ih in range(len(p.heights)):

				outfile=open(p.folder+level+'/system/sampleDict_SITE_'+str(ih),'w')
	
				n=30
				i=0
				while i<n:
					outfile.write(lines[i])
					i+=1
	
				outfile.write('sets\n')
				outfile.write('(\n')
				outfile.write('  results\n')
				outfile.write('  {\n')
				outfile.write('    type    points;\n')
				outfile.write('    functionObjectLibs ("libsampling.so");\n')
				outfile.write('    axis    xyz;\n')
				outfile.write('    ordered yes;\n')
				outfile.write('    points (\n')
				for ip in range(len(xprobe)): outfile.write('        ( '+str(xprobe[ip])+' '+str(yprobe[ip])+' '+str(zprobe[ip]+float(p.heights[ih]))+' )\n')
				outfile.write('    );\n')
				outfile.write('  }\n')
				outfile.write(');\n')
				
				while i<len(lines):
					outfile.write(lines[i])
					i+=1
				outfile.close()

		SampleSite()
		SampleProfiles()
		if p.nmapping>0:	SampleMapping()
		if p.nmeso>0:		SampleMeso()

	def SetDict_mapFields():
		
		file1=PATH+'../../COMMON/foam/calc_openfoam/mapFieldsDict'
		file2=p.folder+'FINE/system/'
		subprocess.call(['cp',file1,file2])
		
		file2=p.folder+'REDUCED/system/'
		subprocess.call(['cp',file1,file2])

	def SetFoam(level):
		
		initdir=PATH+'../../PROJECTS_CFD/'+p.site+'/MESH/'+p.site+'_'+p.meshname+'/MESH_'+level
		targdir=p.folder+level
		subprocess.call(['rm','-rf',targdir])
		subprocess.call(['mkdir','-p', targdir])
		subprocess.call(['mkdir','-p',targdir+'/0'])
		subprocess.call(['cp','-r',initdir+'/constant',targdir])
		subprocess.call(['cp','-r',initdir+'/system',targdir])
		
		SetFile_U(level)
		SetFile_k(level)
		SetFile_p(level)
		SetFile_nut(level)
		SetFile_epsilon(level)
		SetFile_transportProperties(level)
		SetFile_turbulenceProperties(level)
		SetFile_ABLConditions(level)
		SetFile_initialConditions(level)
		SetFile_fvSolution(level)
		SetFile_fvSchemes(level)
		SetFile_boundary(level)
		SetDict_control(level)
		SetDict_sample(level)

	try:

		start=time.time()
		
		if p.INIT: SetFoam('COARSE')
		SetFoam('FINE')
		SetFoam('REDUCED')
		SetDict_mapFields()

		with open(PATH+'../../COMMON/foam/calc_openfoam/fvOptions','r') as f: lines=f.readlines()
		for fold in ['COARSE','FINE']:
			if fold=='COARSE' and p.INIT==False: continue
			with open(p.folder+fold+'/system/fvOptions','w') as f:
				for line in lines: f.write(line)
				f.write('limitU'+'\n')
				f.write('{'+'\n')
				f.write('type limitVelocity;'+'\n')
				f.write('active yes;'+'\n')
				f.write('selectionMode all;'+'\n')
				f.write('max %.1f;'%(2.5*float(p.vref))+'\n')
				f.write('}'+'\n')

		p.duration_2=time.time()-start
	except (KeyboardInterrupt, SystemExit): raise
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': SetCase')
		p.WriteLog(0)

def RunCase():

	def RunCoarse():

		start=time.time()

		if os.path.isfile(p.folder+'COARSE/terminated'): return
		
		if p.nproc2use>1:
			
			workdir=p.folder+'FINE'
					
			infile=open(PATH+'../../COMMON/foam/calc_openfoam/decomposeParDict','r')
			lines=infile.readlines()
			infile.close()
			outfile=open(p.folder+'FINE/system/decomposeParDict','w')
			n=17
			i=0 
			while i<n:
				outfile.write(lines[i])
				i+=1
			outfile.write('numberOfSubdomains '+str(p.nproc2use)+';\n')
			i=i+1
			while i<len(lines):
				outfile.write(lines[i])
				i+=1
			outfile.close()
			
			if p.EXTERN: print msg("Running decomposePar (fine)")
			
			logfile=open(p.logfile,'a')
			logfile.write(msg("Running decomposePar (fine)").encode('utf8')+'\n')
			logfile.close()
			
			with using_machine_file(p, workdir):
				os.system('decomposePar -force -case '+workdir+ SHELL_REDIR +workdir+'/log_decomposePar')
			
			if os.path.isfile(p.folder+'paused'): p.PAUSED=True

			if not p.PAUSED:
			
				workdir=p.folder+'COARSE'
				
				infile=open(PATH+'../../COMMON/foam/calc_openfoam/decomposeParDict','r')
				lines=infile.readlines()
				infile.close()
				outfile=open(p.folder+'COARSE/system/decomposeParDict','w')
				n=17
				i=0 
				while i<n:
					outfile.write(lines[i])
					i+=1
				outfile.write('numberOfSubdomains '+str(p.nproc2use)+';\n')
				i=i+1
				while i<len(lines):
					outfile.write(lines[i])
					i+=1
				outfile.close()

				if p.EXTERN: print msg("Running decomposePar (coarse)")
				
				logfile=open(p.logfile,'a')
				logfile.write(msg("Running decomposePar (coarse)").encode('utf8')+'\n')
				logfile.close()
				with using_machine_file(p, workdir):
					os.system('decomposePar -force -case '+workdir+ SHELL_REDIR +workdir+'/log_decomposePar')
		
		p.duration_3+=time.time()-start
	
		if os.path.isfile(p.folder+'paused'):
			p.PAUSED=True
			return
		
		if p.EXTERN: print msg("Running simpleFoam (coarse)")
		
		with open(p.logfile,'a') as f: f.write(msg("Running simpleFoam (coarse)").encode('utf8')+'\n')
		
		workdir=p.folder+'COARSE'
		open(workdir+'/launched','w').close()
		
		pth=os.path.join(PATH,'..','..','APPLI','TMP','CFD_CALC_01_SURVEY.py')
		
		if not os.path.isfile(pth): pth=os.path.join(PATH,'..','..','APPLI','BIN','CFD_CALC_01_SURVEY.pyc')
		
		subprocess.Popen(['python2',pth,'--input',workdir])
		
		if p.nproc2use==1:
			run_cmd = "simpleFoam -case '" + workdir + "'"
		elif p.machine_filename:
			run_cmd = "foamJob -parallel -screen -case '" + workdir + "' simpleFoam -case '" + workdir + "' -parallel"
		else:
			run_cmd = "mpirun --oversubscribe -np "+str(p.nproc2use)+" simpleFoam -case '" + workdir + "' -parallel"
			
		with using_machine_file(p, workdir):
			os.system(run_cmd + SHELL_REDIR + "'"+workdir+"/log_simpleFoam'")

		with open(workdir+'/log_simpleFoam','r') as f: lines=f.readlines()

		try:
			if len(lines)<5: p.VALID_RUN_COARSE=False
			else:
				if lines[-1].rstrip()=='End' or lines[-2].rstrip()=='End' or lines[-3].rstrip()=='End': p.VALID_RUN_COARSE=True
		except: p.VALID_RUN_COARSE=False
		
		p.last_it_coarse='0'
		
		if p.VALID_RUN_COARSE:
			FOUND=False
			i=0
			while not FOUND:
				i+=1
				try:
					if lines[-i].startswith('Time ='):
						p.last_it_coarse=lines[-i].split()[-1]
						FOUND=True
				except:
					pass
				if i>100:
					p.VALID_RUN_COARSE=False
					break
		
		if p.EXTERN: print msg("Running foamLog")
		
		logfile=open(p.logfile,'a')
		logfile.write(msg("Running foamLog").encode('utf8')+'\n')
		logfile.close()
		
		MakeLogs(p.folder,'COARSE')
		
		if os.path.isfile(p.folder+'paused'): p.PAUSED=True
		
		if not p.PAUSED: open(workdir+'/terminated','w').close()
		
		if p.PAUSED and p.nproc2use>1: os.system('reconstructPar -withZero -case '+workdir+ SHELL_REDIR +p.folder+'COARSE/log_reconstructPar')
		
		p.duration_4+=time.time()-start
		
	def RunMap():
		
		if os.path.isfile(p.folder+'paused'):
			p.PAUSED=True
			return

		if p.VALID_RUN_COARSE:

			start=time.time()

			if p.EXTERN: print msg("Running mapFields from coarse to fine Mesh")
			
			logfile=open(p.logfile,'a')
			logfile.write(msg("Running mapFields from coarse to fine Mesh").encode('utf8')+'\n')
			logfile.close()
			
			workdir=p.folder+'FINE'

			if p.nproc2use>1:	os.system('cd '+workdir+'; mapFields -parallelSource -parallelTarget -sourceTime latestTime ../COARSE/'+ SHELL_REDIR +'log_mapFields')
			else:				os.system('cd '+workdir+'; mapFields -sourceTime latestTime ../COARSE/'+ SHELL_REDIR +'log_mapFields')
			p.duration_5+=time.time()-start
		
	def RunFine():

		if os.path.isfile(p.folder+'FINE/terminated') and not p.RESTARTED: return
		
		if os.path.isfile(p.folder+'paused'):
			p.PAUSED=True
			return
		
		workdir=p.folder+'FINE'

		if (not p.INIT and p.nproc2use>1) or p.RESTARTED:
			
			start=time.time()
			
			infile=open(PATH+'../../COMMON/foam/calc_openfoam/decomposeParDict','r')
			lines=infile.readlines()
			infile.close()
			outfile=open(p.folder+'FINE/system/decomposeParDict','w')
			n=17
			i=0 
			while i<n:
				outfile.write(lines[i])
				i+=1
			outfile.write('numberOfSubdomains '+str(p.nproc2use)+';\n')
			i=i+1
			while i<len(lines):
				outfile.write(lines[i])
				i+=1
			outfile.close()
			
			if p.EXTERN: print msg("Running decomposePar (fine)")
			
			logfile=open(p.logfile,'a')
			logfile.write(msg("Running decomposePar (fine)").encode('utf8')+'\n')
			logfile.close()
			
			with using_machine_file(p, workdir):
				os.system('decomposePar -force -case '+workdir+ SHELL_REDIR +workdir+'/log_decomposePar')
			
			p.duration_3+=time.time()-start

		if os.path.isfile(p.folder+'paused'):
			p.PAUSED=True
			return

		start=time.time()

		if p.EXTERN: print msg("Running simpleFoam (fine)")
		
		logfile=open(p.logfile,'a')
		logfile.write(msg("Running simpleFoam (fine)").encode('utf8')+'\n')
		logfile.close()
		
		open(workdir+'/launched','w').close()
		
		pth=os.path.join(PATH,'..','..','APPLI','TMP','CFD_CALC_01_SURVEY.py')
		
		if not os.path.isfile(pth): pth=os.path.join(PATH,'..','..','APPLI','BIN','CFD_CALC_01_SURVEY.pyc')
		
		subprocess.Popen(['python2',pth,'--input',workdir])
		
		if p.nproc2use==1:
			run_cmd = "simpleFoam -case '" + workdir + "'"
		elif p.machine_filename:
			run_cmd = "foamJob -parallel -screen -case '" + workdir + "' simpleFoam -case '" + workdir + "' -parallel"
		else:
			run_cmd = "mpirun --oversubscribe -np "+str(p.nproc2use)+" simpleFoam -case '" + workdir + "' -parallel"
		
		with using_machine_file(p, workdir):
			os.system(run_cmd + SHELL_REDIR + "'" + workdir + "/log_simpleFoam'")
			
		infile=open(workdir+'/log_simpleFoam','r')
		lines=infile.readlines()
		infile.close()

		try:
			if len(lines)<5: p.VALID_RUN_FINE=False
			else:
				if lines[-1].rstrip()=='End' or lines[-2].rstrip()=='End' or lines[-3].rstrip()=='End': p.VALID_RUN_FINE=True
		except: p.VALID_RUN_FINE=False

		p.last_it_fine='0'
		
		if p.VALID_RUN_FINE:
			FOUND=False
			i=0
			while not FOUND:
				i+=1
				try:
					if lines[-i].split()[0]=='Time':
						p.last_it_fine=lines[-i].split()[-1]
						FOUND=True
				except: pass
				if i>100:
					p.VALID_RUN_FINE=False
					break

		if p.EXTERN: print msg("Running foamLog")
		
		logfile=open(p.logfile,'a')
		logfile.write(msg("Running foamLog").encode('utf8')+'\n')
		logfile.close()
		
		MakeLogs(p.folder,'FINE')
		
		p.duration_6+=time.time()-start

		if p.nproc2use>1:
			
			start=time.time()
			
			if p.EXTERN: print msg("Running case reconstruction (fine)")
			
			logfile=open(p.logfile,'a')
			logfile.write(msg("Running case reconstruction (fine)").encode('utf8')+'\n')
			logfile.close()

			os.system('reconstructPar -withZero -case '+p.folder+'FINE' + SHELL_REDIR + p.folder+'FINE/log_reconstructPar')
			p.duration_7+=time.time()-start

		open(workdir+'/terminated','w').close()

	if os.path.isfile(p.folder+'paused'):
		p.PAUSED=True
		return
	
	try:

		if not LOCAL:
			with open(PATH + '../../../progress.txt', 'w') as pf: pf.write('0.01')
		if p.INIT:
			RunCoarse()
			if not LOCAL:
				with open(PATH + '../../../progress.txt', 'w') as pf: pf.write('0.10')
			RunMap()
		if not LOCAL:
			with open(PATH + '../../../progress.txt', 'w') as pf: pf.write('0.15')
		RunFine()
		if not LOCAL:
			with open(PATH + '../../../progress.txt', 'w') as pf: pf.write('1.00')

	except (KeyboardInterrupt, SystemExit): raise
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': RunCase')
		p.WriteLog(0)

def GetResults():
	
	workdir=p.folder+'FINE'
	
	# results acquisition
	
	infile=workdir+'/postProcessing/sampleDict_RESULTS/'+p.last_it_fine+'/results_U.xy'
	df_vel= pd.read_csv(infile,sep='\s+',names=['x','y','z','vx','vy','vz'],dtype='float64')
	df_vel['x']=df_vel['x'].round(1)
	df_vel['y']=df_vel['y'].round(1)
	
	infile=workdir+'/postProcessing/sampleDict_RESULTS/'+p.last_it_fine+'/results_p_nut_k_epsilon.xy'
	df_tur= pd.read_csv(infile,sep='\s+',names=['x','y','z','p','nut','k','eps'],dtype='float64')
	df_tur['x']=df_tur['x'].round(1)
	df_tur['y']=df_tur['y'].round(1)
	
	# reference frame
	
	X=[]
	Y=[]
	Z=[]
	with open(workdir+'/system/sampleDict_RESULTS','r') as ref_file:
		lines=ref_file.readlines()
		for line in lines[38:]:
			try:
				s=line.lstrip('		( ').rstrip(' )\n')
				x,y,z=s.split()
				x,y,z=round(float(x),1),round(float(y),1),float(z)
				X.append(x)
				Y.append(y)
				Z.append(z)
			except:pass
			
	labels=['mast_'+str(i) for i in range(p.nmast) for _ in range(210)]+\
			['lidar_'+str(i) for i in range(p.nlidar) for _ in range(210)]+\
			['wt_'+str(i) for i in range(p.nwt) for _ in range(210)]
	if p.npoint>0:
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zspoint','r') as f:
			lines_data=f.readlines()
		for i in range(p.npoint):
			h = float(lines_data[i].split()[2])
			if h<10: labels.append('point_'+str(i))
			else: labels+= ['point_'+str(i) for _ in range(20)]
	
	it = iter([labels,X,Y,Z])
	the_len = len(next(it))
	if not all(len(l) == the_len for l in it):
		raise ValueError("""Number of probes inconsistent with the number of entities:
		expected: {}
		found: {}""".format(len(labels),len(X)))

	ref_df= pd.DataFrame({'entity':labels,'x':X,'y':Y,'z':Z})
	
	# joining and gap filling
	
	df_vel= df_vel.drop_duplicates()
	df_tur= df_tur.drop_duplicates()
	
	ref_df=ref_df.merge(df_vel,how='left',on=['x','y','z'])
	ref_df=ref_df.merge(df_tur,how='left',on=['x','y','z'])
	
	ref_df=ref_df.groupby('entity').ffill()
	ref_df=ref_df.groupby('entity').bfill()
	
	# smoothing
	
	groups=ref_df.groupby('entity')
	def smoothing(x):
		if len(x.index)==1: return x
		else: return x.rolling(window=20, win_type='gaussian', center=True).mean(std=4)
	
	ref_df['vx_smooth']=groups['vx'].transform(smoothing)
	ref_df['vy_smooth']=groups['vy'].transform(smoothing)
	ref_df['vz_smooth']=groups['vz'].transform(smoothing)

	ref_df['vh_smooth']=np.sqrt(ref_df['vx_smooth']**2+ref_df['vy_smooth']**2)
	ref_df['v_smooth']=np.sqrt(ref_df['vx_smooth']**2+ref_df['vy_smooth']**2+ref_df['vz_smooth']**2)
	
	ref_df['p_smooth']=groups['p'].transform(smoothing)
	ref_df['nut_smooth']=groups['nut'].transform(smoothing)
	ref_df['k_smooth']=groups['k'].transform(smoothing)
	ref_df['eps_smooth']=groups['eps'].transform(smoothing)
	
	ref_df['iu_smooth']=np.sqrt(ref_df['k_smooth'])/ref_df['vh_smooth']
	
	ref_df['dir_smooth']=ref_df.apply(lambda row: Cart2WindDir(row['vx_smooth'], row['vy_smooth']), axis=1)
	ref_df['inc_smooth']=np.degrees(np.arctan2(ref_df['vz_smooth'],ref_df['vh_smooth']))
	
	ref_df['deltadir_smooth']=ref_df['dir_smooth']-p.direcval
	ref_df.loc[ref_df['deltadir_smooth']>180, 'deltadir_smooth']-=360
	ref_df.loc[ref_df['deltadir_smooth']<-180, 'deltadir_smooth']+=360
	
	# write profiles results
	
	entities_param=[(p.nmast,'mast',-1),(p.nwt,'wt',-2),(p.nlidar,'lidar',-1)]
	
	for n_ent,ent,name_loc in entities_param:
		
		if n_ent>0:
	
			with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zs'+ent,'r') as f:
				lines_data=f.readlines()
			with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_'+ent,'r') as f:
				lines_coord=f.readlines()
				
			for i in range(n_ent):
				name=lines_data[i].split()[name_loc]
				coords=lines_coord[i].split()
				
				with open(p.folder+'RES/'+ent+'_'+name+'.txt','w') as outfile:
				
					outfile.write('Name'.rjust(20)+'\t'+'X[m]'.rjust(20)+'\t'+'Y[m]'.rjust(20)+'\t'+'Elevation[m]'.rjust(20)+'\n')
					outfile.write(name.rjust(20)+'\t'+'%20.2f'%float(coords[0])+'\t'+'%20.2f'%float(coords[1])+'\t'+'%20.2f'%float(coords[2])+'\n\n')
						
					df_ent= groups.get_group(ent+'_'+str(i)).copy()
					df_ent['h']=df_ent['z']-float(coords[2])
					
					headers=['h[m]',	'Vh[m/s]',	'Iu[-]',	'Dir[deg]',			'Inc[deg]']
					columns=['h',		'vh_smooth','iu_smooth','deltadir_smooth',	'inc_smooth']
					formats=['{:10.1f}','{:10.5f}',	'{:10.5f}',	'{:10.5f}',			'{:10.5f}']
					
					if p.CFD:
						headers.extend(['Vel[m/s]',	'Vz[m/s]',	'Tke[m2/s2]',	'Eps[m2/s3]',	'nut[m2/s]',	'p[Pa]'])
						columns.extend(['v_smooth',	'vz_smooth','k_smooth',		'eps_smooth',	'nut_smooth',	'p_smooth'])
						formats.extend(['{:10.5f}',	'{:10.5f}',	'{:10.5f}',		'{:10.5f}',		'{:10.5f}',		'{:10.5f}'])
					
					df_ent=df_ent.loc[:,columns].dropna()
					formatters= [fmt.format for fmt in formats]
					df_ent.to_string(outfile,index=False,col_space=10,justify='right',\
									 columns=columns,header=headers,formatters=formatters)
	
	# write points results
	
	if p.npoint>0:
		
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zspoint','r') as f:
			lines_data=f.readlines()
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_point','r') as f:
			lines_coord=f.readlines()
		
		names=[]
		labels=[]
		elevs=[]
		for i in range(p.npoint):
			names.append(lines_data[i].split()[-1])
			elevs.append(float(lines_coord[i].split()[2]))
			labels.append('point_'+str(i))
		df_info=pd.DataFrame({'entity':labels,'name':names,'elev':elevs})
		
		df_points= ref_df.loc[ref_df['entity'].str.startswith('point'), :].copy()
		df_points['h']=0
		
		df_points= df_points.merge(df_info,on=['entity'],how='left')
		df_points['h']=df_points['z']-df_points['elev']
		
		with open(p.folder+'RES/points.txt','w') as outfile:
			
			headers=['Name',	'X[m]',		'Y[m]',		'Elevation[m]',	'h[m]',		'Vh[m/s]',	'Iu[-]',	'Dir[deg]',			'Inc[deg]']
			columns=['name',	'x',		'y',		'elev',			'h',		'vh_smooth','iu_smooth','deltadir_smooth',	'inc_smooth']
			formats=['{}',		'{:20.2f}',	'{:20.2f}',	'{:20.2f}',		'{:10.2f}',	'{:10.5f}',	'{:10.5f}',	'{:10.5f}',			'{:10.5f}']
			
			if p.CFD:
				headers.extend(['Vel[m/s]','Vz[m/s]',	'Tke[m2/s2]',	'Eps[m2/s3]','nut[m2/s]',	'p[Pa]'])
				columns.extend(['v_smooth','vz_smooth',	'k_smooth',		'eps_smooth','nut_smooth',	'p_smooth'])
				formats.extend(['{:10.5f}',	'{:10.5f}',	'{:10.5f}',		'{:10.5f}',		'{:10.5f}',		'{:10.5f}'])
				
			df_points=df_points.loc[:,columns].dropna()
			formatters= [fmt.format for fmt in formats]
			df_points.to_string(outfile,index=False,col_space=10,justify='right',\
							 columns=columns,header=headers,formatters=formatters)

def GetResMeso(num):

	workdir=p.folder+'FINE'

	imes=int(num)

	infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmeso','r')
	lines_zs=infile.readlines()
	infile.close()

	entity='MESO_'+num

	_,_,_,vx,vy,vz=np.loadtxt(workdir+'/postProcessing/sampleDict_'+entity+'/'+p.last_it_fine+'/results_U.xy',unpack=True)
	_,_,_,pr,nut,tke,eps=np.loadtxt(workdir+'/postProcessing/sampleDict_'+entity+'/'+p.last_it_fine+'/results_p_nut_k_epsilon.xy',unpack=True)

	v_np=np.sqrt(vx*vx+vy*vy+vz*vz)
	vh_np=np.sqrt(vx*vx+vy*vy)
	iu_np=np.sqrt(tke)/vh_np

	tmp_np=np.sqrt(vx*vx+vy*vy)
	direc_np=tmp_np
	inc_np=tmp_np
	
	for ip in range(len(v_np)):
		vvx=vx[ip]
		vvy=vy[ip]
		vvz=vz[ip]
		direc,inc=Rect2Polar(vvx,vvy,vvz)
		
		direc1=p.direcval
		direc2=direc
		if direc1<90. and direc2>270:	direc1+=360.
		elif direc1>270. and direc2<90:	direc2+=360.
		ecart=direc2-direc1
		if ecart>+180.:		ecart-=360
		elif ecart<-180.:	ecart+=360
		
		direc_np[ip]=ecart
		inc_np[ip]=inc
	
	v=np.average(v_np)
	vh=np.average(vh_np)
	vz=np.average(vz)
	iu=np.average(iu_np)
	direc=np.average(direc_np)
	inc=np.average(inc_np)
	tke=np.average(tke)
	eps=np.average(eps)
	nut=np.average(nut)
	pr=np.average(pr)

	values=lines_zs[imes].split()
	x=float(values[0])
	y=float(values[1])
	h=float(values[2])
	dia=float(values[3])
	res=float(values[4])
	label=values[5]

	if p.CFD:	p.text_meso.append([num,label.rjust(20)+'\t'+'%20.2f'%x+'\t'+'%20.2f'%y+'\t'+'%10.2f'%h+'\t'+'%10.2f'%dia+'\t'+'%10.2f'%res+'\t'+'%10.5f'%vh+'\t'+'%10.5f'%iu+'\t'+'%10.5f'%direc+'\t'+'%10.5f'%inc+'\t'+'%10.5f'%v+'\t'+'%10.5f'%vz+'\t'+'%10.5f'%tke+'\t'+'%10.5f'%eps+'\t'+'%10.5f'%nut+'\t'+'%10.5f'%pr+'\n'])
	else:		p.text_meso.append([num,label.rjust(20)+'\t'+'%20.2f'%x+'\t'+'%20.2f'%y+'\t'+'%10.2f'%h+'\t'+'%10.2f'%dia+'\t'+'%10.2f'%res+'\t'+'%10.5f'%vh+'\t'+'%10.5f'%iu+'\t'+'%10.5f'%direc+'\t'+'%10.5f'%inc+'\n'])

def GetResMapping(num):
	
	workdir=p.folder+'FINE'
	
	# results acquisition
	
	infile=workdir+'/postProcessing/sampleDict_MAPPING_'+num+'/'+p.last_it_fine+'/results_U.xy'
	df_vel= pd.read_csv(infile,sep='\s+',names=['x','y','z','vx','vy','vz'],dtype='float64')
	df_vel['x']=df_vel['x'].round(1)
	df_vel['y']=df_vel['y'].round(1)
	
	infile=workdir+'/postProcessing/sampleDict_MAPPING_'+num+'/'+p.last_it_fine+'/results_p_nut_k_epsilon.xy'
	df_tur= pd.read_csv(infile,sep='\s+',names=['x','y','z','p','nut','k','eps'],dtype='float64')
	df_tur['x']=df_tur['x'].round(1)
	df_tur['y']=df_tur['y'].round(1)
	
	workdir=p.folder+'REDUCED'
	
	infile=workdir+'/postProcessing/sampleDict_MAPPING_'+num+'_up/0/results_U.xy'
	df_up= pd.read_csv(infile,sep='\s+',names=['x','y','z_up','vx_up','vy_up','vz_up'],dtype='float64')
	df_up['x']=df_up['x'].round(1)
	df_up['y']=df_up['y'].round(1)
	df_up=df_up.drop(columns='vz_up')
	
	infile=workdir+'/postProcessing/sampleDict_MAPPING_'+num+'_down/0/results_U.xy'
	df_down= pd.read_csv(infile,sep='\s+',names=['x','y','z_down','vx_down','vy_down','vz_down'],dtype='float64')
	df_down['x']=df_down['x'].round(1)
	df_down['y']=df_down['y'].round(1)
	df_down=df_down.drop(columns='vz_down')
	
	# reference frame
	
	X,Y,Z=[],[],[]
	with open(workdir+'/system/sampleDict_MAPPING_'+num,'r') as ref_file:
		lines=ref_file.readlines()
		for line in lines[38:]:
			try:
				s=line.lstrip('		( ').rstrip(' )\n')
				x,y,z=s.split()
				x,y,z=round(float(x),1),round(float(y),1),float(z)
				X.append(x)
				Y.append(y)
				Z.append(z)
			except:pass
			
	ref_df= pd.DataFrame({'x':X,'y':Y,'z':Z})
	
	X,Y,Z=[],[],[]
	with open(workdir+'/system/sampleDict_MAPPING_'+num+'_down','r') as ref_file:
		lines=ref_file.readlines()
		for line in lines[38:]:
			try:
				s=line.lstrip('		( ').rstrip(' )\n')
				x,y,z=s.split()
				x,y,z=round(float(x),1),round(float(y),1),float(z)
				X.append(x)
				Y.append(y)
				Z.append(z)
			except:pass
			
	ref_down= pd.DataFrame({'x':X,'y':Y,'z_down':Z})
	ref_df=ref_df.merge(ref_down,how='left',on=['x','y'])
	
	X,Y,Z=[],[],[]
	with open(workdir+'/system/sampleDict_MAPPING_'+num+'_up','r') as ref_file:
		lines=ref_file.readlines()
		for line in lines[38:]:
			try:
				s=line.lstrip('		( ').rstrip(' )\n')
				x,y,z=s.split()
				x,y,z=round(float(x),1),round(float(y),1),float(z)
				X.append(x)
				Y.append(y)
				Z.append(z)
			except:pass
			
	ref_up= pd.DataFrame({'x':X,'y':Y,'z_up':Z})
	ref_df=ref_df.merge(ref_up,how='left',on=['x','y'])
	
	# joining and gap filling
	
	df_vel= df_vel.drop_duplicates()
	df_tur= df_tur.drop_duplicates()
	df_up= df_up.drop_duplicates()
	df_down= df_down.drop_duplicates()
	
	ref_df=ref_df.merge(df_vel,how='left',on=['x','y','z'])
	ref_df=ref_df.merge(df_tur,how='left',on=['x','y','z'])
	iout = ref_df.isna().any(axis='columns').sum()
	if iout>0: p.missing_entities.append(['mapping_'+num,iout])
	
	ref_df=ref_df.merge(df_down,how='left',on=['x','y','z_down'])
	iout = ref_df['vx_down'].isna().sum()
	if iout>0: p.missing_entities.append(['mapping_down_'+num,iout])
	
	ref_df=ref_df.merge(df_up,how='left',on=['x','y','z_up'])
	iout = ref_df['vx_up'].isna().sum()
	if iout>0: p.missing_entities.append(['mapping_up_'+num,iout])
	
	for col in ref_df.columns:
		miss = ref_df[col].isna()
		if miss.values.any():
			print("interpolating {} missing results on mapping {}: {}...".format(miss.sum(),num,col))
			
			miss_pts = np.column_stack([ref_df.loc[miss,'x'],ref_df.loc[miss,'y']])
			found_pts = np.column_stack([ref_df.loc[~miss,'x'],ref_df.loc[~miss,'y']])
			found_vals = ref_df.loc[~miss,col].values
			
			miss_vals = interpolate.griddata(found_pts,found_vals,miss_pts,method='nearest')
			ref_df.loc[miss,col] = miss_vals
			
			
	# variables calculation
	
	ref_df['vh']=np.sqrt(ref_df['vx']**2+ref_df['vy']**2)
	ref_df['vh_up']=np.sqrt(ref_df['vx_up']**2+ref_df['vy_up']**2)
	ref_df['vh_down']=np.sqrt(ref_df['vx_down']**2+ref_df['vy_down']**2)
	ref_df['v']=np.sqrt(ref_df['vx']**2+ref_df['vy']**2+ref_df['vz']**2)
	
	ref_df['iu']=np.sqrt(ref_df['k'])/ref_df['vh']
	ref_df['dir']=ref_df.apply(lambda row: Cart2WindDir(row['vx'], row['vy']), axis=1)
	ref_df['inc']=np.degrees(np.arctan2(ref_df['vz'],ref_df['vh']))
	
	ref_df['deltadir']=ref_df['dir']-p.direcval
	ref_df.loc[ref_df['deltadir']>180, 'deltadir']-=360
	ref_df.loc[ref_df['deltadir']<-180, 'deltadir']+=360
	
	# alpha calculation
	
	with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmapping','r') as zsfile:
		zslines=zsfile.readlines()
	
	imap=int(float(num))
	h=float(zslines[imap].split()[5])
	h_up=float(zslines[imap].split()[5])+float(zslines[imap].split()[6])/2.
	h_down=float(zslines[imap].split()[5])-float(zslines[imap].split()[6])/2.
	
	x = np.array([h_down,h,h_up])
	x = np.log(x)
	xmoy = np.mean(x)
	xdiff = x-xmoy
	
	y = np.log(ref_df.loc[:,['vh_down','vh','vh_up']])# shape (n,3)
	y.columns = ['down','mid','up']
	ymoy = y.mean(axis='columns')# shape (n,)
	ydiff = y.sub(ymoy,axis='index')# shape (n,3)
	
	covxy = (xdiff*ydiff).mean(axis='columns')# shape (n,)
	varx = np.mean(xdiff**2)
	
	ref_df['alpha'] = covxy / varx
	
	# write results
	
	coord_df=pd.read_csv(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_mapping_'+num,names=['x','y','elev'],sep='\s+')
	ref_df=ref_df.merge(coord_df,how='left',on=['x','y'])
	
	with open(p.folder+'RES/mapping_'+num+'.txt','w') as outfile:
		
		headers=['X[m]',	'Y[m]',		'Elevation[m]',	'Vh[m/s]',	'Iu[-]',	'Dir[deg]',	'Inc[deg]']
		columns=['x',		'y',		'elev',			'vh',		'iu',		'deltadir',	'inc']
		formats=['{:20.2f}','{:20.2f}',	'{:20.2f}',		'{:10.5f}',	'{:10.5f}',	'{:10.5f}',	'{:10.5f}']
		
		if p.CFD:
			headers.extend(['Vel[m/s]',	'Vz[m/s]',	'Tke[m2/s2]',	'Eps[m2/m3]',	'nut[m2/s]','p[Pa]'])
			columns.extend(['v',		'vz',		'k',			'eps',			'nut',		'p'])
			formats.extend(['{:10.5f}',	'{:10.5f}',	'{:10.5f}',		'{:10.5f}',		'{:10.5f}',	'{:10.5f}'])
			
		df_out=ref_df.loc[:,columns].dropna()
		formatters= [fmt.format for fmt in formats]
		df_out.to_string(outfile,index=False,col_space=10,justify='right',\
						 columns=columns,header=headers,formatters=formatters)
	
	with open(p.folder+'RES/mapping_'+num+'_shear.txt','w') as outfile:
		
		headers=['X[m]',	'Y[m]',		'Elevation[m]',	'Shear[-]']
		columns=['x',		'y',		'elev',			'alpha']
		formats=['{:20.2f}','{:20.2f}',	'{:20.2f}',		'{:10.5f}']
		
		df_out=ref_df.loc[:,columns].dropna()
		formatters= [fmt.format for fmt in formats]
		df_out.to_string(outfile,index=False,col_space=10,justify='right',\
						 columns=columns,header=headers,formatters=formatters)

def GetResSite():
	
	workdir=p.folder+'REDUCED'
	
	infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_site','r')
	lines_res=infile.readlines()
	infile.close()

	for ih in range(len(p.heights)):
		
		entity='SITE_'+str(ih)

		x2use=[]
		y2use=[]
		z2use=[]
		
		vh2use=[]
		iu2use=[]
		ecart2use=[]
		inc2use=[]
		v2use=[]
		vz2use=[]
		tke2use=[]
		eps2use=[]
		nut2use=[]
		p2use=[]

		infile=open(workdir+'/postProcessing/sampleDict_'+entity+'/0/results_U.xy','r')
		lines_vel=infile.readlines()
		infile.close()
	
		infile=open(workdir+'/postProcessing/sampleDict_'+entity+'/0/results_p_nut_k_epsilon.xy','r')
		lines_tur=infile.readlines()
		infile.close()

		z2add=float(p.heights[ih])
		
		iline=-1
		iwritten=0
		iout=0
		for line in lines_res:
			iline+=1
			iline2use=iline-iout
			values=line.split()
			x=float(values[0])
			y=float(values[1])
			z=float(values[2])
			zp=-99.
			try:
				values=lines_vel[iline2use].split()
				zp=float(values[2])
			except: zp=-99
			if abs(zp-z-z2add)<=1e-2:
				vx=float(values[3])
				vy=float(values[4])
				vz=float(values[5])
				values=lines_tur[iline2use].split()
				pr=float(values[3])
				nut=float(values[4])
				k=float(values[5])
				eps=float(values[6])
				v=sqrt(vx*vx+vy*vy+vz*vz)
				vh=sqrt(vx*vx+vy*vy)
				if vh>0:	iu=sqrt(k)/vh
				else:		iu=10.
				direc,inc=Rect2Polar(vx,vy,vz)
				direc1=p.direcval
				direc2=direc
				if direc1<90. and direc2>270: direc1+=360.
				elif direc1>270. and direc2<90: direc2+=360.
				ecart=direc2-direc1
				if ecart>180: ecart-=360.
				elif ecart<-180: ecart+=360.

				iwritten+=1
				x2use.append(x)
				y2use.append(y)
				z2use.append(zp)
				vh2use.append(vh)
				iu2use.append(iu)
				ecart2use.append(ecart)
				inc2use.append(inc)
				v2use.append(v)
				vz2use.append(vz)
				tke2use.append(k)
				eps2use.append(eps)
				nut2use.append(nut)
				p2use.append(pr)
			else: iout+=1

		ntot=iwritten
		if iout>0: p.missing_entities.append(['site_'+str(ih),iout])

		outfile=open(p.folder+'RES/site_'+str(ih)+'.txt','w')
		
		head_cfd='X[m]'.rjust(20)+'\t'+'Y[m]'.rjust(20)+'\t'+'Elevation[m]'.rjust(20)+'\t'+'Vh[m/s]'.rjust(10)+'\t'+'Iu[-]'.rjust(10)+'\t'+'Dir[deg]'.rjust(10)+'\t'+'Inc[deg]'.rjust(10)+'\t'+'Vel[m/s]'.rjust(10)+'\t'+'Vz[m/s]'.rjust(10)+'\t'+'Tke[m2/s2]'.rjust(10)+'\t'+'Eps(m2/m3)'.rjust(10)+'\t'+'nut[m2/s]'.rjust(10)+'\t'+'p[Pa]'.rjust(10)+'\n'
		head_std='X[m]'.rjust(20)+'\t'+'Y[m]'.rjust(20)+'\t'+'Elevation[m]'.rjust(20)+'\t'+'Vh[m/s]'.rjust(10)+'\t'+'Iu[-]'.rjust(10)+'\t'+'Dir[deg]'.rjust(10)+'\t'+'Inc[deg]'.rjust(10)+'\n'
		if p.CFD: outfile.write(head_cfd)
		else: outfile.write(head_std)
		for i in range(ntot):
			if p.CFD:	outfile.write('%20.2f'%x2use[i]+'\t%20.2f'%y2use[i]+'\t%20.2f'%z2use[i]+'\t%10.5f'%vh2use[i]+'\t%10.5f'%iu2use[i]+'\t%10.5f'%ecart2use[i]+'\t%10.5f'%inc2use[i]+'\t%10.5f'%v2use[i]+'\t%10.5f'%vz2use[i]+'\t%10.5f'%tke2use[i]+'\t%10.5f'%eps2use[i]+'\t%10.5f'%nut2use[i]+'\t%10.5f\n'%p2use[i])
			else:			outfile.write('%20.2f'%x2use[i]+'\t%20.2f'%y2use[i]+'\t%20.2f'%z2use[i]+'\t%10.5f'%vh2use[i]+'\t%10.5f'%iu2use[i]+'\t%10.5f'%ecart2use[i]+'\t%10.5f\n'%inc2use[i])
		outfile.close()

def GetResZoom():

	if os.path.isfile(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_res_zoom'):
	
		workdir=p.folder+'REDUCED'
		
		infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/elevations_res_zoom','r')
		lines_res=infile.readlines()
		infile.close()
	
		for ih in range(len(p.heights)):
			
			entity='ZOOM_'+str(ih)
	
			x2use=[]
			y2use=[]
			z2use=[]
			
			vh2use=[]
			iu2use=[]
			ecart2use=[]
			inc2use=[]
			v2use=[]
			vz2use=[]
			tke2use=[]
			eps2use=[]
			nut2use=[]
			p2use=[]
			
			vx2use=[]
			vy2use=[]
			vz2use=[]
	
			infile=open(workdir+'/postProcessing/sampleDict_'+entity+'/0/results_U.xy','r')
			lines_vel=infile.readlines()
			infile.close()
		
			infile=open(workdir+'/postProcessing/sampleDict_'+entity+'/0/results_p_nut_k_epsilon.xy','r')
			lines_tur=infile.readlines()
			infile.close()
	
			z2add=float(p.heights[ih])
			
			iline=-1
			iwritten=0
			iout=0
			for line in lines_res:
				iline+=1
				iline2use=iline-iout
				values=line.split()
				x=float(values[0])
				y=float(values[1])
				z=float(values[2])
				zp=-99.
				try:
					values=lines_vel[iline2use].split()
					zp=float(values[2])
				except: zp=-99
				if abs(zp-z-z2add)<=1e-2:
					vx=float(values[3])
					vy=float(values[4])
					vz=float(values[5])
					values=lines_tur[iline2use].split()
					pr=float(values[3])
					nut=float(values[4])
					k=float(values[5])
					eps=float(values[6])
					v=sqrt(vx*vx+vy*vy+vz*vz)
					vh=sqrt(vx*vx+vy*vy)
					if vh>0:	iu=sqrt(k)/vh
					else:		iu=10.
					direc,inc=Rect2Polar(vx,vy,vz)
					direc1=p.direcval
					direc2=direc
					if direc1<90. and direc2>270: direc1+=360.
					elif direc1>270. and direc2<90: direc2+=360.
					ecart=direc2-direc1
					if ecart>180: ecart-=360.
					elif ecart<-180: ecart+=360.
	
					iwritten+=1
					x2use.append(x)
					y2use.append(y)
					z2use.append(zp)
					vh2use.append(vh)
					iu2use.append(iu)
					ecart2use.append(ecart)
					inc2use.append(inc)
					v2use.append(v)
					vz2use.append(vz)
					tke2use.append(k)
					eps2use.append(eps)
					nut2use.append(nut)
					p2use.append(pr)
					vx2use.append(vx)
					vy2use.append(vy)
					vz2use.append(vz)
				else: iout+=1
	
			ntot=iwritten
			if iout>0: p.missing_entities.append(['zoom_'+str(ih),iout])
	
			outfile=open(p.folder+'RES/zoom_'+str(ih)+'.txt','w')
			
			head_cfd='X[m]'.rjust(20)+'\t'+'Y[m]'.rjust(20)+'\t'+'Elevation[m]'.rjust(20)+'\t'+'Vh[m/s]'.rjust(10)+'\t'+'Iu[-]'.rjust(10)+'\t'+'Dir[deg]'.rjust(10)+'\t'+'Inc[deg]'.rjust(10)+'\t'+'Vel[m/s]'.rjust(10)+'\t'+'Vz[m/s]'.rjust(10)+'\t'+'Tke[m2/s2]'.rjust(10)+'\t'+'Eps(m2/m3)'.rjust(10)+'\t'+'nut[m2/s]'.rjust(10)+'\t'+'p[Pa]'.rjust(10)+'\n'
			head_std='X[m]'.rjust(20)+'\t'+'Y[m]'.rjust(20)+'\t'+'Elevation[m]'.rjust(20)+'\t'+'Vh[m/s]'.rjust(10)+'\t'+'Iu[-]'.rjust(10)+'\t'+'Dir[deg]'.rjust(10)+'\t'+'Inc[deg]'.rjust(10)+'\n'
			if p.CFD: outfile.write(head_cfd)
			else: outfile.write(head_std)
			for i in range(ntot):
				if p.CFD:	outfile.write('%20.2f'%x2use[i]+'\t%20.2f'%y2use[i]+'\t%20.2f'%z2use[i]+'\t%10.5f'%vh2use[i]+'\t%10.5f'%iu2use[i]+'\t%10.5f'%ecart2use[i]+'\t%10.5f'%inc2use[i]+'\t%10.5f'%v2use[i]+'\t%10.5f'%vz2use[i]+'\t%10.5f'%tke2use[i]+'\t%10.5f'%eps2use[i]+'\t%10.5f'%nut2use[i]+'\t%10.5f\n'%p2use[i])
				else:			outfile.write('%20.2f'%x2use[i]+'\t%20.2f'%y2use[i]+'\t%20.2f'%z2use[i]+'\t%10.5f'%vh2use[i]+'\t%10.5f'%iu2use[i]+'\t%10.5f'%ecart2use[i]+'\t%10.5f\n'%inc2use[i])
			outfile.close()
			
			infile=open(p.projdir+'/DATA/res_zoom_facground','r')
			lines=infile.readlines()
			infile.close()
			facnum=[]
			for line in lines:
				values=line.split()
				facnum.append([int(values[0]),int(values[1]),int(values[2])])
			ncells=len(facnum)
			
			outfile=open(p.folder+'RES/zoom_'+str(ih)+'.vtk','w')
			text=''
			text+='# vtk DataFile Version 1.0\n'
			text+='2D Unstructured Grid of Linear Triangles\n'
			text+='ASCII\n'
			text+='\n'
			text+='DATASET UNSTRUCTURED_GRID\n'
			text+='POINTS '+str(ntot)+' float'+'\n'
			for i in range(ntot): text+='%.2f\t%.2f\t%.2f\n'%(x2use[i],y2use[i],z2use[i])
			text+='\n'
			text+='CELLS '+str(ncells)+' '+str(ncells*4)+'\n'
			for i in range(ncells): text+='3\t%i\t%i\t%i\n'%(facnum[i][0]-1,facnum[i][1]-1,facnum[i][2]-1)
			text+='\n'
			text+='CELL_TYPES '+str(ncells)+'\n'
			for i in range(ncells): text+='5\n'
			text+='\n'
			text+='POINT_DATA %i\n'%ntot
			text+='SCALARS pressure float\n'
			text+='LOOKUP_TABLE default\n'
			for i in range(ntot): text+='%.2f\n'%p2use[i]
			text+='\n'
			text+='SCALARS iu float\n'
			text+='LOOKUP_TABLE default\n'
			for i in range(ntot): text+='%.4f\n'%iu2use[i]
			text+='\n'
			text+='SCALARS ecart float\n'
			text+='LOOKUP_TABLE default\n'
			for i in range(ntot): text+='%.2f\n'%ecart2use[i]
			text+='\n'
			text+='SCALARS inc float\n'
			text+='LOOKUP_TABLE default\n'
			for i in range(ntot): text+='%.2f\n'%inc2use[i]
			text+='\n'
			text+='VECTORS velocity float\n'
			for i in range(ntot): text+='%.4f\t%.4f\t%.4f\n'%(vx2use[i],vy2use[i],vz2use[i])
			text+='\n'
	
			outfile.write(text)
			outfile.close()

def MakeLogs(folder,meshtype='FINE'):
	
	if meshtype not in ['COARSE','FINE']:
		raise ValueError("meshtype should be one of ['COARSE','FINE']")
	if meshtype=='COARSE':
		tag='init'
	elif meshtype=='FINE':
		tag='calc'
	
	workdir = os.path.join(folder,meshtype)
	
	xmlfile=folder+'/history.xml'
	root=xml.parse(xmlfile).getroot()
	
	liste=[]
	for bal in root:
		if bal.attrib['type']==tag:
			liste.append(os.path.join(workdir,'log_simpleFoam.'+bal.attrib['i']))
	if os.path.isfile(os.path.join(workdir,'log_simpleFoam')):
		liste.append(os.path.join(workdir,'log_simpleFoam'))
	if len (liste)>0:
		with open(os.path.join(workdir,'log2use'),'w') as outfile:
			for fname in liste:
				try:
					with open(fname) as infile:
						for line in infile: outfile.write(line)
				except: pass
		
		subprocess.call(['foamLog','-quiet','log2use'],cwd=workdir)#creates workdir/logs/ folder

def GetLastResidual(infile):
	
	res=1.
	infile=open(infile,'r')
	lines=infile.readlines()
	infile.close()
	nlines=len(lines)
	for i in range(nlines):
		try:
			values=lines[i].split()
			res=float(values[1])
		except: break
	return res

def GetCvg():
	
	workdir=p.folder+'FINE'
	
	res_p=GetLastResidual(workdir+'/logs/p_0')
	res_ux=GetLastResidual(workdir+'/logs/Ux_0')
	res_uy=GetLastResidual(workdir+'/logs/Uy_0')
	res_uz=GetLastResidual(workdir+'/logs/Uz_0')
	res_eps=GetLastResidual(workdir+'/logs/epsilon_0')
	res_k=GetLastResidual(workdir+'/logs/k_0')

	rapport_p= 	100*log10(res_p)/log10(float(p.cvg_p))
	rapport_ux=	100*log10(res_ux)/log10(float(p.cvg_u))
	rapport_uy=	100*log10(res_uy)/log10(float(p.cvg_u))
	rapport_uz=	100*log10(res_uz)/log10(float(p.cvg_u))
	rapport_k=	100*log10(res_k)/log10(float(p.cvg_k))
	rapport_eps=100*log10(res_eps)/log10(float(p.cvg_eps))
	
	rap_min=min(rapport_p,rapport_ux,rapport_uy,rapport_uz,rapport_k,rapport_eps)

	if rap_min==rapport_p:		p.varlim='p'
	elif rap_min==rapport_ux:	p.varlim='Ux'
	elif rap_min==rapport_uy:	p.varlim='Uy'
	elif rap_min==rapport_uz:	p.varlim='Uz'
	elif rap_min==rapport_k:	p.varlim='k'
	elif rap_min==rapport_eps:	p.varlim='eps'

	p.cvg_rate=min(100.,rap_min)

def GetCvgRes():
	
	lv,lk=[],[]

	xmlfile=os.path.join(p.folder,'history.xml')
	root=xml.parse(xmlfile).getroot()
	for bal in root:
		if bal.attrib['type']=='calc':
			with open(os.path.join(p.folder,'FINE','postProcessing','probes','U.%s'%bal.attrib['i']),'r') as f: lines=f.readlines()
			for line in lines:
				if line[0]!='#': lv.append(line)
			with open(os.path.join(p.folder,'FINE','postProcessing','probes','k.%s'%bal.attrib['i']),'r') as f: lines=f.readlines()
			for line in lines:
				if line[0]!='#': lk.append(line)

	with open(os.path.join(p.folder,'itstart_c'),'r') as f: it_prev=f.readline()
	fname=os.path.join(p.folder,'FINE','postProcessing','probes',it_prev,'U')
	if os.path.isfile(fname):
		with open(fname,'r') as f: lines=f.readlines()
		for line in lines:
			if line[0]!='#': lv.append(line)
		fname=os.path.join(p.folder,'FINE','postProcessing','probes',it_prev,'k')
		with open(fname,'r') as f: lines=f.readlines()
		for line in lines:
			if line[0]!='#': lk.append(line)
	
	if len(lv)>0:
		res_mt,res_wt,_=InvestigateConvergence(lv,lk,p.npoint,p.nmast,p.nlidar,p.nwt)
		if len(res_mt[0])>CVGRES_NTMIN:
			stdmax=0.
			for ip in range(p.nmast):
				std=np.array(res_mt[ip])[-CVGRES_NTMIN:].std()
				stdmax=max(std,stdmax)
			for ip in range(p.nwt):
				std=np.array(res_wt[ip])[-CVGRES_NTMIN:].std()
				stdmax=max(std,stdmax)
			p.cvg_rate_res=min(100.,100*log10(stdmax)/log10(p.cvg_alpha))
	
def RunPost():

	if os.path.isfile(p.folder+'paused'):
		p.PAUSED=True
		return
	
	if not p.VALID_RUN_FINE: return

	try:

		start=time.time()
		
		threads=[]
		workdir=p.folder+'REDUCED'
		for i in range(p.nmapping):
			entity='MAPPING_'+str(i)+'_down'
			command='postProcess -case '+workdir+' -func sampleDict_'+entity+' -time '+p.last_it_fine+ SHELL_REDIR +workdir+'/log_sample_'+entity
			message=(msg("Running postProcess")+' - res_'+entity)
			threads.append(THREAD_Command(command,message))
			threads[-1].start()
		for i in range(p.nmapping):
			entity='MAPPING_'+str(i)+'_up'
			command='postProcess -case '+workdir+' -func sampleDict_'+entity+' -time '+p.last_it_fine+ SHELL_REDIR +workdir+'/log_sample_'+entity
			message=(msg("Running postProcess")+' - res_'+entity)
			threads.append(THREAD_Command(command,message))
			threads[-1].start()
		for i in range(len(p.heights)):
			entity='SITE_'+str(i)
			command='postProcess -case '+workdir+' -func sampleDict_'+entity+' -time '+p.last_it_fine+ SHELL_REDIR +workdir+'/log_sample_'+entity
			message=(msg("Running postProcess")+' - res_'+entity)
			threads.append(THREAD_Command(command,message))
			threads[-1].start()

		for thread in threads:	thread.join()

		if p.EXTERN: print 'GetRes'
		
		logfile=open(p.logfile,'a')
		logfile.write('GetRes'+'\n')
		logfile.close()
		
		threads=[]
		threads.append(THREAD_GetRes('RESULTS'))
		threads.append(THREAD_GetRes('SITE'))
		for i in range(p.nmeso):	threads.append(THREAD_GetRes('MESO',str(i)))
		for i in range(p.nmapping):	threads.append(THREAD_GetRes('MAPPING',str(i)))
		threads.append(THREAD_GetRes('CVG'))
		threads.append(THREAD_GetRes('CVG_RES'))
		for thread in threads:	thread.start()
		for thread in threads:	thread.join()

		if p.nmeso>0:
			
			outfile=open(p.folder+'RES/mesos.txt','w')
			if p.CFD:		outfile.write('Name'.rjust(20)+'\tX[m]'.rjust(20)+'\tY[m]'.rjust(20)+'\th[m]'.rjust(10)+'\tdia[m]'.rjust(10)+'\tres[m]'.rjust(10)+'\tVh[m/s]'.rjust(10)+'\tIu[-]'.rjust(10)+'\tDir[deg]'.rjust(10)+'\tInc[deg]'.rjust(10)+'\tVel[m/s]'.rjust(10)+'\tVz[m/s]'.rjust(10)+'\tTke[m2/s2]'.rjust(10)+'\tEps(m2/m3)'.rjust(10)+'\tnut[m2/s]'.rjust(10)+'\tp[Pa]'.rjust(10)+'\n')
			else:			outfile.write('Name'.rjust(20)+'\tX[m]'.rjust(20)+'\tY[m]'.rjust(20)+'\th[m]'.rjust(10)+'\tdia[m]'.rjust(10)+'\tres[m]'.rjust(10)+'\tVh[m/s]'.rjust(10)+'\tIu[-]'.rjust(10)+'\tDir[deg]'.rjust(10)+'\tInc[deg]'.rjust(10)+'\n')
			p.text_meso=sorted(p.text_meso)
			for line in p.text_meso: outfile.write(line[1])
			outfile.close()
		
		p.duration_8+=time.time()-start
		
	except (KeyboardInterrupt, SystemExit): raise
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': RunPost')
		p.WriteLog(0)

def RunMapReduced():

	if os.path.isfile(p.folder+'paused'):
		p.PAUSED=True
		return
	
	if not p.VALID_RUN_FINE: return

	try:

		start=time.time()
		
		if p.EXTERN: print msg("Storing results on reduced mesh")
		
		threads=[]
		workdir=p.folder+'FINE'
		for i in range(p.nmeso):
			entity='MESO_'+str(i)
			command='postProcess -case '+workdir+' -func sampleDict_'+entity+' -time '+p.last_it_fine+ SHELL_REDIR +workdir+'/log_sample_'+entity
			message=(msg("Running postProcess")+' - res_'+entity)
			threads.append(THREAD_Command(command,message))
			threads[-1].start()

		entity='RESULTS'
		command='postProcess -case '+workdir+' -func sampleDict_'+entity+' -time '+p.last_it_fine+ SHELL_REDIR +workdir+'/log_sample_'+entity
		message=(msg("Running postProcess")+' - res_'+entity)
		threads.append(THREAD_Command(command,message))
		threads[-1].start()

		for i in range(p.nmapping):
			entity='MAPPING_'+str(i)
			command='postProcess -case '+workdir+' -func sampleDict_'+entity+' -time '+p.last_it_fine+ SHELL_REDIR +workdir+'/log_sample_'+entity
			message=(msg("Running postProcess")+' - res_'+entity)
			threads.append(THREAD_Command(command,message))
			threads[-1].start()

		logfile=open(p.logfile,'a')
		logfile.write(msg("Storing results on reduced mesh").encode('utf8')+'\n')
		logfile.close()
		
		workdir=p.folder+'REDUCED'

		os.system('cd '+workdir+'; mapFields -sourceTime latestTime ../FINE/'+ SHELL_REDIR +'log_mapFields_reduced')
		bin_path = os.path.join(OFPATH, 'openfoam8/platforms/linux64GccDPInt32Opt/bin/foamToVTK') 
		os.system('"'+bin_path+'" -constant -case '+p.folder+'REDUCED'+ SHELL_REDIR +p.folder+'REDUCED/log_foamToVTK')
		
		p.duration_9+=time.time()-start
		
	except (KeyboardInterrupt, SystemExit): raise
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': RunMapReduced')
		p.WriteLog(0)

if __name__ == '__main__':
	
	SetEnviron()
	
	time2use=basename(sys.argv[0])
	LOCAL = True
	if "CLOUD_WORKER" in os.environ and os.environ["CLOUD_WORKER"].strip() == "1":
		LOCAL = False
	elif os.path.isfile(os.path.join(PATH, '..', '..', '..', 'conf')):
		LOCAL = False
	itmax=20
	
	try:
		language=sys.argv[-1]
		if language not in LANGUAGES.codes: raise ValueError('bad language argument')
	except:	language='EN'
	
	time_START=time.time()
	
	if LOCAL:
		SHELL_REDIR = ' > '
	else:
		SHELL_REDIR = ' | tee '  # so we also output to stdout
	
	msg=GetUITranslator(language)
	
	p=PARAM(time2use,LOCAL)
	
	progressfile=PATH+'../../APPLI/TMP/logout_'+time2use+'.xml'
	if not os.path.isfile(progressfile):
		root=xml.Element('logout')
		xml.SubElement(root,'progress_text')
		xml.SubElement(root,'progress_frac').text='0'
		xml.ElementTree(root).write(progressfile)
		if not LOCAL:
			with open(PATH+'../../../progress.txt','w') as pf: pf.write('0.')

	istep=0.
	nstep=8
	
	ReadParam()
	CalcBC()
	SetCase()
	RunCase()
	RunMapReduced()
	RunPost()
	
	if not p.PAUSED:
	
		p.duration_tot+=time.time()-time_START
		
		xmlfile=p.folder+'info.xml'
		root=xml.Element('info')
		
		xml.SubElement(root,'machine').text				=p.machine
		xml.SubElement(root,'valid_run_coarse').text	=str(p.VALID_RUN_COARSE)
		xml.SubElement(root,'valid_run_fine').text		=str(p.VALID_RUN_FINE)
		xml.SubElement(root,'missing_entities').text	=str(p.missing_entities)
		balise=xml.SubElement(root,'durations')
		xml.SubElement(balise,'duration_tot').text		='%.1f'%p.duration_tot
		xml.SubElement(balise,'duration_1').text		='%.1f'%p.duration_1
		xml.SubElement(balise,'duration_2').text		='%.1f'%p.duration_2
		xml.SubElement(balise,'duration_3').text		='%.1f'%p.duration_3
		xml.SubElement(balise,'duration_4').text		='%.1f'%p.duration_4
		xml.SubElement(balise,'duration_5').text		='%.1f'%p.duration_5
		xml.SubElement(balise,'duration_6').text		='%.1f'%p.duration_6
		xml.SubElement(balise,'duration_7').text		='%.1f'%p.duration_7
		xml.SubElement(balise,'duration_8').text		='%.1f'%p.duration_8
		xml.SubElement(balise,'duration_9').text		='%.1f'%p.duration_9
		balise=xml.SubElement(root,'cvg')
		xml.SubElement(balise,'cvg_rate').text			='%.1f'%p.cvg_rate
		xml.SubElement(balise,'cvg_rate_res').text		='%.1f'%p.cvg_rate_res
		xml.SubElement(balise,'varlim').text			=p.varlim
		xml.SubElement(balise,'last_it_fine').text		=p.last_it_fine
		xml.SubElement(balise,'last_it_coarse').text	=p.last_it_coarse
		
		xml.ElementTree(root).write(xmlfile)
	
		if p.nproc2use>1:
			for i in range(p.nproc2use): 
				if p.INIT: subprocess.call(['rm','-rf',p.folder+'COARSE/processor'+str(i)])
				subprocess.call(['rm','-rf',p.folder+'FINE/processor'+str(i)])
	
		if p.LIGHT:
			coarse_dir=os.path.join(p.folder,'COARSE')
			fine_dir=os.path.join(p.folder,'FINE')
			for direc in [coarse_dir,fine_dir]:
				if not os.path.isdir(direc): continue
				subprocess.call(['rm','-rf',os.path.join(direc,'constant')])
				subprocess.call(['rm','-rf',os.path.join(direc,'system')])
				for o in os.listdir(direc):
					path=os.path.join(direc,o)
					if not os.path.isdir(path): continue
					try:
						int(o)
						subprocess.call(['rm','-rf',path])
					except ValueError:
						continue
	
		xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/CALC/'+p.codecalc+'/param.xml'
		root=xml.parse(xmlfile).getroot()
		root.find('n_it_max_init').text=p.last_it_coarse
		root.find('n_it_max').text=p.last_it_fine
		root.find('nproc').text=str(p.nproc2use)
		xml.ElementTree(root).write(xmlfile)
	
		xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/CALC/'+p.codecalc+'/actual.xml'
		root=xml.parse(xmlfile).getroot()
		root.find('n_it_max_init').text=p.last_it_coarse
		root.find('n_it_max').text=p.last_it_fine
		xml.ElementTree(root).write(xmlfile)
	
		open(p.folder+'terminated','w').close()
	
		subprocess.call(['rm',PATH+'../../APPLI/TMP/'+time2use])
		subprocess.call(['rm',PATH+'../../APPLI/TMP/'+time2use+'.xml'])
		
	size='%.1f'%(GetFolderSize(PATH+'../../PROJECTS_CFD/'+p.site+'/CALC/'+p.codecalc)/1.e+6)
	
	if p.EXTERN: ZipDir(PATH+'../../PROJECTS_CFD/'+p.site+'/CALC/'+p.codecalc,'RESULTS_'+p.codecalc+'.zip')
	
	if LOCAL:
		xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/CALC/calculations.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.text==p.codecalc:
				bal2use=bal
				bal2use.text=p.codecalc
				bal.attrib['nproc']='-'
				bal2use.attrib['size']=size
				bal2use.attrib['cvg']='%.1f'%p.cvg_rate_res
				if p.PAUSED:			bal2use.attrib['state']='Paused'
				elif p.VALID_RUN_FINE:	bal2use.attrib['state']='Ready'
				else:					bal2use.attrib['state']='Diverged'
				if p.LIGHT: 			bal2use.attrib['clean']='No restart'
				break
		root=SortXmlData(root)
		xml.ElementTree(root).write(xmlfile)
	
	if not p.PAUSED and LOCAL:
		root=xml.parse(xmlfileproc).getroot()
		for bal in root:
			if bal.attrib['code'] in ['cfd_calc01','cfd_calc02'] and bal.attrib['time']==time2use:
				root.remove(bal)
				break
		xml.ElementTree(root).write(xmlfileproc)
	
	if LOCAL:
		
		EXTRA_Q=False
		root=xml.parse(xmlfilequeue).getroot()
		for bal in root:
			if bal.attrib['code'] in ['cfd_calc01','cfd_calc02'] and bal.attrib['site']==p.site:
				EXTRA_Q=True
				break
		
		EXTRA_R=False
		root=xml.parse(xmlfileproc).getroot()
		for bal in root:
			if bal.attrib['code'] in ['cfd_calc01','cfd_calc02'] and bal.attrib['site']==p.site:
				EXTRA_R=True
				break
		
		newtext=''
		xmlfile=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.text==p.site:
				newtext='Yes'
				if EXTRA_Q: newtext+='-Queued'
				if EXTRA_R: newtext+='-Running'
				bal.attrib['calculated']=newtext
				xml.ElementTree(root).write(xmlfile)
				break
	
	if p.EXTERN: print 'CALCULATION ENDED\n'
	
	if os.path.isfile(p.folder+'paused'): p.PAUSED=True
	
	logfile=open(p.logfile,'a')
	if p.PAUSED:
		logfile.write('\nCALCULATION PAUSED\n')
		p.errors=[msg("Calculation is paused")+'.']
	else:
		logfile.write('\nCALCULATION ENDED\n')
		p.errors=[msg("Calculation is over")+'.']
	logfile.close()

	time_END=time.time()

	if not p.PAUSED and LOCAL:
	
		OK,it=False,0
		while not OK and it<50:
			it+=1
			try:
				root=xml.parse(xmlfileold).getroot()
				OK=True
			except: time.sleep(0.1)
		
		bal=xml.SubElement(root,'process')
		bal.attrib['username']=p.user
		bal.attrib['code']='cfd_calc01'
		bal.attrib['name']=p.name
		bal.attrib['codename']=p.name
		bal.attrib['site']=p.site
		bal.attrib['start']='%.2f'%time_START
		bal.attrib['end']='%.2f'%time_END
		bal.attrib['duration']='%.2f'%p.duration_tot
		bal.attrib['status']='ok'
		bal.attrib['time']=p.time2use
		
		OK=False
		it=0
		while not OK and it<50:
			it+=1
			try:
				xml.ElementTree(root).write(xmlfileold)
				OK=True
			except: time.sleep(0.1)

	if not LOCAL:
		
		with open('ok_CFD_CALC_01','w') as outfile: pass

	p.WriteLog(1)
