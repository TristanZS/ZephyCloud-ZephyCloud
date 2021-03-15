#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ZS_VARIABLES	import *
from ZS_COMMON		import FORTRAN_FILE,P_THREAD,CFD_PARAM,GetUITranslator
from ZS_COMMON		import SortXmlData,UpdateProgress,GetMachine,GetFolderSize,SubprocessCall
from ZS_COMMON		import GenerateLines,WriteGeo
from shapely.geometry import Polygon

NEED_MEM=False

class PARAM(CFD_PARAM):
	
	def __init__(self,time2use,LOCAL):
		
		CFD_PARAM.__init__(self,'',time2use,LOCAL)
		self.type					='CFD_MESH'
		self.code					='cfd_mesh01'
		
		self.reflines				=[]
		self.contours				=[]
		self.z						=[]
		self.version				=''
		self.zline					=''
		self.fileformat_oro			=''
		self.fileformat_rou			=''
		self.meshcrit				=''
		self.contcrit				=''
		self.diaref					=-1.
		self.diadom					=-1.
		self.resfine				=-1.
		self.rescoarse				=-1.
		self.nsect					=-1
		self.meshlim				=-1.
		self.htop					=-1.
		self.hturb					=-1.
		self.hcanop					=-1.
		self.dztop					=-1.
		self.dzturb					=-1.
		self.dzcanop				=-1.
		self.dzmin					=-1.
		self.exptop					=-1.
		self.expturb				=-1.
		self.expcanop				=-1.
		self.nsmoo					=-1
		self.smoocoef				=-1.
		self.insmoo					=-1
		self.relax_distratio		=-1.
		self.relax_resfactor		=-1.
		self.nz						=-1
		self.nzcst					=-1
		self.nzprof					=-1
		self.ncells					=-1
		self.resdist				=-1.
		self.resratio				=1
		self.multizone				=-1
		self.rmoy_tot				=0.
		self.rmoy_int				=0.
		self.zmoy					=0.
		self.resfine_init			=-1.
		self.rescoarse_init			=-1.
		self.ncells_fine			='0'
		self.ncells_coarse			='---'
		self.ncells_reduced			='---'
		self.ratiomax_coarse		='---'
		self.ratiomax_fine			='---'
		self.ratiomax_reduced		='---'
		self.ortomax_coarse			='---'
		self.ortomax_fine			='---'
		self.ortomax_reduced		='---'
		self.ortomoy_coarse			='---'
		self.ortomoy_fine			='---'
		self.ortomoy_reduced		='---'
		self.skewmax_coarse			='---'
		self.skewmax_fine			='---'
		self.skewmax_reduced		='---'
		self.duration_tot			=0.
		self.duration_1				=0.
		self.duration_2				=0.
		self.duration_3				=0.
		self.duration_4				=0.
		self.duration_5				=0.
		self.duration_6				=0.
		self.duration_7				=0.
		self.duration_8				=0.
		self.duration_9				=0.
		self.duration_10			=0.
		self.duration_11			=0.
		self.duration_12			=0.
		self.duration_13			=0.
		self.duration_14			=0.
		self.duration_15			=0.
		self.duration_16			=0.
		self.duration_17			=0.
		self.duration_18			=0.
		self.duration_19			=0.
		self.duration_20			=0.
		self.duration_21			=0.
		self.duration_22			=0.
		self.duration_23			=0.
		self.duration_24			=0.
		self.duration_25			=0.
		self.duration_26			=0.
		self.duration_27			=0.

		self.WARN_COARSE		=False
		self.WARN_REDUCED		=False
		self.WARN_FINE			=False

		self.OK_coarse			=False
		self.OK_fine			=False
		self.OK_reduced			=False
		self.OK					=True

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

msg=GetUITranslator(language)

if LOCAL:
	SHELL_REDIR = ' > '
else:
	SHELL_REDIR = ' | tee '  # so we also output to stdout

p=PARAM(time2use,LOCAL)

progressfile=PATH+'../../APPLI/TMP/logout_'+time2use+'.xml'
if not os.path.isfile(progressfile):
	root=xml.Element('logout')
	xml.SubElement(root,'progress_text')
	xml.SubElement(root,'progress_frac').text='0'
	xml.ElementTree(root).write(progressfile)
	if not LOCAL:
		with open(PATH+'../../../progress.txt','w') as pf: pf.write('0')

rootprogress=xml.parse(progressfile).getroot()
	
class THREAD_Prepa(P_THREAD):
	
	def __init__(self,code):
		
		self.code=code
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		Mesh(ithread+1,self.code)
		
		AnalyseMesh(ithread+1,self.code)
		CalcRou(ithread+1,self.code)
		PropaRou(ithread+1,self.code)

		infile=open(p.folder+'/FILES/'+self.code+'_ground_pts','r')
		lines=infile.readlines()
		npts=len(lines)
		np_first=npts/p.nproc
		np_then=npts-(p.nproc-1)*np_first
		for idiv in range(p.nproc):
			num=self.code+'_ground_pts_%i'%idiv
			outfile=open(p.folder+'/FILES/'+num,'w')
			ifirst=idiv*np_first
			if idiv!=p.nproc-1: ilast=(idiv+1)*np_first
			else: ilast=idiv*np_first+np_then
			for il in range(ifirst,ilast): outfile.write(lines[il])
			outfile.close()
		
		self.postrun(ithread)
		
		if self.code=='coarse':		p.OK_coarse=True
		elif self.code=='fine':		p.OK_fine=True
		elif self.code=='reduced':	p.OK_reduced=True

class THREAD_Oro(P_THREAD):
	
	def __init__(self,code,num):
		
		self.code=code
		self.num=num
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		CalcOro(ithread+1,self.code,self.num)
		
		self.postrun(ithread)

class THREAD_PropaOro(P_THREAD):
	
	def __init__(self,code):
		
		self.code=code
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		PropaOro(ithread+1,self.code)
		
		self.postrun(ithread)

class THREAD_Inout(P_THREAD):
	
	def __init__(self,code):
		
		self.code=code
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		InOut(ithread+1,self.code)
		
		self.postrun(ithread)

class THREAD_Foam(P_THREAD):
	
	def __init__(self,code):
		
		self.code=code
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		Foam(ithread+1,self.code)
		
		self.postrun(ithread)

def ReadParam():
	"""
	Reads the process input parameters
	"""
	
	try:
		
		xmlfile=PATH+'../../APPLI/TMP/'+time2use+'.xml'
		root=xml.parse(xmlfile).getroot()
		
		p.site		=root.find('sitename').text
		p.name			=root.find('name').text
	
		p.lname=p.site+'_'+p.name
		p.projdir	=PATH+'../../PROJECTS_CFD/'+p.site
		p.folder	=p.projdir+'/MESH/'+p.lname
	
		if LOCAL:
		
			EXTRA_Q=False
			rootqueue=xml.parse(xmlfilequeue).getroot()
			for bal in rootqueue:
				if bal.attrib['code'] in ['cfd_mesh01','cfd_mesh02'] and bal.attrib['site']==p.site:
					EXTRA_Q=True
					break
		
			xmlfilecfd=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
			rootcfd=xml.parse(xmlfilecfd).getroot()
			
			for balcfd in rootcfd:
				
				if balcfd.text==p.site:
						
					newtext=''
					if 'Yes' in balcfd.attrib['meshed']:	newtext='Yes'
					else:									newtext='No'
					if EXTRA_Q: newtext+='-Queued'
					newtext+='-Running'
					balcfd.attrib['meshed']=newtext
					xml.ElementTree(rootcfd).write(xmlfilecfd)
					break 
		
			xmlfilelist=p.projdir+'/MESH/meshes.xml'
			rootlist=xml.parse(xmlfilelist).getroot()
			for bal in rootlist:
				if bal.text==p.lname:
					bal.attrib['state']='Running'
					bal.attrib['time2use']=time2use
					bal.attrib['nproc']=root.find('nproc').text
					rootlist=SortXmlData(rootlist)
					xml.ElementTree(rootlist).write(xmlfilelist)
					break
	
		p.version		=root.find('version').text
		p.username		=root.find('username').text
		p.meshcrit		=root.find('meshcrit').text
		p.meshlim_i		=float(root.find('meshlim_i').text)
		p.diaref_i		=float(root.find('diaref_i').text)
		p.diadom_i		=float(root.find('diadom_i').text)
		p.resfine_i		=float(root.find('resfine_i').text)
		p.rescoarse_i	=float(root.find('rescoarse_i').text)
		p.htop_i		=float(root.find('htop_i').text)
		p.hcanop_i		=float(root.find('hcanop_i').text)
		p.hturb			=float(root.find('hturb').text)
		p.dztop			=float(root.find('dztop').text)
		p.dzturb		=float(root.find('dzturb').text)
		p.dzcanop		=float(root.find('dzcanop').text)
		p.dzmin			=float(root.find('dzmin').text)
		p.exptop		=float(root.find('exptop').text)
		p.expturb		=float(root.find('expturb').text)
		p.expcanop		=float(root.find('expcanop').text)
		p.smoocoef		=float(root.find('smoocoef').text)
		p.relax_distratio	=float(root.find('relax_distratio').text)
		p.relax_resfactor	=float(root.find('relax_resfactor').text)
		
		p.resdist		=float(root.find('resdist').text)
		p.resratio		=int(float(root.find('resratio').text))
		p.insmoo		=int(float(root.find('insmoo').text))
		p.nsmoo			=int(float(root.find('nsmoo').text))
		p.multizone		=int(float(root.find('multizone').text))
		p.nproc			=int(float(root.find('nproc').text))
		p.nsect			=LIST_NSECT[int(float(root.find('nsect').text))]
	
		p.contcrit		=root.find('contcrit').text
		
		p.diaref		=p.diaref_i
		p.diadom		=p.diadom_i
		p.resfine		=p.resfine_i
		p.rescoarse		=p.rescoarse_i
		p.htop			=p.htop_i
		p.hcanop		=p.hcanop_i
		p.meshlim		=p.meshlim_i
	
		if p.meshlim<0.: p.meshlim=int(MEMMAX-0.1*MEMMAX)
		else: p.meshlim=int(p.meshlim*1e+6)
		
		p.nz			=0
		p.z				=[]
	
		xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/site.xml'
		root=xml.parse(xmlfile).getroot()
		diamin=float(root.find('diamin').text)
		if p.diaref<0.: p.diaref=diamin+2000.
		else:
			if p.diaref<diamin+100.:
				p.errors.append(msg("ERROR")+': '+msg("mesh condition requires diaref>diamin+100. to allow meshing")+'. ')
				p.WriteLog(0,print_exc=False)
	
		if p.diadom>=0. and p.diadom<diamin+11000.:
			p.errors.append(msg("ERROR")+': '+msg("project configuration condition requires diadom>=%s to allow meshing")%str(diamin+11000.)+'. ')
			p.WriteLog(0,print_exc=False)
		elif p.diadom<0: p.diadom=p.diaref+20000.

		for i in range(p.nproc):
			xmlfile=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(i+1)+'.xml'
			if not os.path.isfile(xmlfile):
				root=xml.Element('logout')
				xml.SubElement(root,'progress_text').text=''
				xml.SubElement(root,'progress_frac').text=str(0)
				xml.ElementTree(root).write(xmlfile)
	
		if LOCAL:
	
			xmlfile=PATH+'../../USERS/machine.xml'
			root=xml.parse(xmlfile).getroot()
			bal=root.find('machine')
			if bal.text is not None: p.machine=bal.text
			else:
				p.machine=GetMachine()
				bal.text=p.machine
				xml.ElementTree(root).write(xmlfile)
		
		else: p.machine=GetMachine()

	except:

		p.errors.append(msg("ERROR")+' '+msg("within process")+': ReadParam')
		p.WriteLog(0)

def EvaluateParam():
	
	global istep

	try:

		start=time.time()
		
		if p.resratio>1:
		
			istep+=1
		
			rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
			rootprogress.find('progress_frac').text=str(istep/nstep)
			try: xml.ElementTree(rootprogress).write(progressfile)
			except: pass
			if not LOCAL:
				try:
					with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
				except: pass
		
			message=msg("Evaluating automatic parameters")
			UpdateProgress(time2use,1,0.05,message)
			
			refloc=[]
			
			xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/data.xml'
			root=xml.parse(xmlfile).getroot()
			
			n_point	=int(float(root.find('n_point').text))
			n_wt	=int(float(root.find('n_wt').text))
			n_mast	=int(float(root.find('n_mast').text))
			n_lidar	=int(float(root.find('n_lidar').text))
			
			if n_point>0:
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zspoint','r')
				lines=infile.readlines()
				infile.close()
				for line in lines:
					values=line.rstrip().split()
					x=float(values[0])
					y=float(values[1])
					refloc.append([x,y])
			if n_mast>0:
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmast','r')
				lines=infile.readlines()
				infile.close()
				for line in lines:
					values=line.rstrip().split()
					x=float(values[0])
					y=float(values[1])
					refloc.append([x,y])
			if n_lidar>0:
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zslidar','r')
				lines=infile.readlines()
				infile.close()
				for line in lines:
					values=line.rstrip().split()
					x=float(values[0])
					y=float(values[1])
					refloc.append([x,y])
			if n_wt>0:
				infile=open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zswt','r')
				lines=infile.readlines()
				infile.close()
				for line in lines:
					values=line.rstrip().split()
					x=float(values[0])
					y=float(values[1])
					refloc.append([x,y])
			
			if len(refloc)==0: refloc.append([0.,0.])
		
			if p.contcrit!='no contour':
				xmlfile=PATH+'../../PROJECTS_CFD/'+p.site+'/contours.xml'
				root=xml.parse(xmlfile).getroot()
				for bal in root:
					if bal.attrib['name']==p.contcrit:
						p.contours=eval(bal.text)
						break
		
			for contour in p.contours:
				
				if len(contour)>=3:
					polygon=Polygon(contour)
					if not polygon.is_valid: 
						try: print 'Polygon not valid:',contour
						except: pass
					if polygon.length<p.resdist: refloc.append([polygon.centroid.x,polygon.centroid.y])
					else:
						xprev=0
						yprev=0
						for elem in contour:
							x=elem[0]
							y=elem[1]
							dd=sqrt((x-xprev)**2+(y-yprev)**2)
							if dd>p.resdist/2.:
								refloc.append([x,y])
								xprev=x
								yprev=y
				
			p.reflines=GenerateLines(p.multizone,refloc,p.resdist,p.diaref,100.,time2use,1,message)
			if len(p.reflines)==0: p.resratio=1
		
			if not os.path.isdir(p.folder+'/FILES/'): subprocess.call(['mkdir','-p',p.folder+'/FILES/'])
			outfile=open(p.folder+'/FILES/reflines','w')
			outfile.write(str(len(p.reflines))+'\n')
			for line in p.reflines: outfile.write(str(line)+'\n')
			outfile.close()
		
		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		UpdateProgress(time2use,1,0.,msg("Mesh resolution loop process")+' - 1/2')
		
		dia2=p.diadom**2
		if p.hcanop<0 :
			rmax=0
			file1=PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsrou'
			with open(file1+'.info','r') as f:
				p.fileformat_rou=f.readline().rstrip()
				p.n_rou=int(f.readline())

			infile=FORTRAN_FILE(file1,mode='r')
			
			xx=infile.readReals()
			yy=infile.readReals()
			zz=infile.readReals()
			for i in range(p.n_rou):
				if i%200==0: UpdateProgress(time2use,1,float(i)/(p.n_rou),msg("Mesh resolution loop process")+' - 1/2')
				x=xx[i]
				y=yy[i]
				r=zz[i]
				d2=x*x+y*y
				if d2<=dia2: rmax=max(rmax,r)
				
			p.hcanop=max(10.,30*rmax)
		
		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		UpdateProgress(time2use,1,0.,msg("Mesh resolution loop process")+' - 2/2')
		
		if p.htop>=0. and p.htop<p.hturb:
			p.errors.append(msg("ERROR")+': '+msg("mesh condition requires htop>%s to allow meshing")%str(p.hturb)+'. ')
			p.WriteLog(0,print_exc=False)
		if p.hturb<=p.hcanop:
			p.errors.append(msg("ERROR")+': '+msg("mesh condition requires hturb>hcanop to allow meshing")+'. ')
			p.WriteLog(0,print_exc=False)
		
		zmin=1e+8
		zmax=0
		file1=PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsoro'
		
		with open(file1+'.info','r') as f:
			p.fileformat_oro=f.readline().rstrip()
			p.n_oro=int(f.readline())

		infile=FORTRAN_FILE(file1,mode='r')
		
		xx=infile.readReals()
		yy=infile.readReals()
		zz=infile.readReals()
		
		for i in range(p.n_oro):
			if i%100==0: UpdateProgress(time2use,1,float(i)/(2*p.n_oro),msg("Vertical discretization parameters"))
			x=xx[i]
			y=yy[i]
			z=zz[i]
			d2=x*x+y*y
			if d2<=dia2:
				zmin=min(zmin,z)
				zmax=max(zmax,z)
		
		htopmin=5*(zmax-zmin)
		
		if p.htop>0 and p.htop<htopmin:
			p.errors.append(msg("ERROR")+': '+msg("mesh condition requires htop>=%s to allow meshing")%str(htopmin)+'. ')
			p.WriteLog(0,print_exc=False)
		elif p.htop<0.: p.htop=max(htopmin,2500.)
		
		z=[]
		z.append(0.)
		z.append(p.dzmin)
		OVER=False
		i=1
		while not OVER:
			dz=z[i]-z[i-1]
			i+=1 
			dz=min(dz*p.expcanop,p.dzcanop)
			z.append(z[i-1]+dz)
			if z[i]>p.hcanop: OVER=True
		OVER=False
		while not OVER:
			dz=z[i]-z[i-1]
			i+=1
			dz=min(dz*p.expturb,p.dzturb)
			z.append(z[i-1]+dz)
			if z[i]>p.hturb: OVER=True
		OVER=False
		nzcst=i 
		while not OVER:
			dz=z[i]-z[i-1]
			i+=1
			dz=min(dz*p.exptop,p.dztop)
			z.append(z[i-1]+dz)
			if z[i]>p.htop: OVER=True
		
		nz=i
		zline=''
		for i in range(nz+1): zline+=str(round(z[i],2))+' '
		
		for zval in z:
			if zval<220: p.nzprof+=1
		p.nzprof+=1
		
		p.z=z
		p.nz=nz
		p.zline=zline
		p.nzcst=nzcst
		
		p.duration_1=time.time()-start
		
		UpdateProgress(time2use,1,1.,msg("Mesh resolution loop process")+' - 2/2')
		
		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if p.meshcrit=='1':
			
			UpdateProgress(time2use,1,0.,msg("Evaluating number of cells"))
		
			start=time.time()
			CalcRes()#sets p.resfine and p.ncells
		
		else:
		
			UpdateProgress(time2use,1,0.35,msg("Mesh resolution loop process"))
			
			start=time.time()

			file1=p.folder+'/FILES/tmp.geo'
			file2=p.folder+'/FILES/tmp.msh2'
			
			WriteGeo(p,file1,'fine',False)
			SubprocessCall("/usr/local/bin/gmsh4",'-v','0','-2',file1,'-o',file2)
			
			with open(p.folder+'/FILES/tmp.msh2','r') as f: lines=f.readlines()
			nnodes=int(lines[4])
			nother=0
			WRONG=True
			while WRONG :
				line=lines[8+nnodes+nother]
				values=line.split()
				val=int(values[1])
				if val!=2:	nother+=1
				else:		WRONG=False
			p.ncells=(int(lines[7+nnodes])-nother)*p.nz
			
			p.duration_2=time.time()-start
		
		if p.rescoarse<0:
			if p.resratio==1:		p.rescoarse=4*p.resfine
			else:					p.rescoarse=p.resratio*p.resfine
		if p.rescoarse<=p.resfine:	p.rescoarse=2*p.resfine
			
		subprocess.call(['rm','-f',p.folder+'/FILES/tmp.msh2'])
		subprocess.call(['rm','-f',p.folder+'/FILES/tmp.geo'])

	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': EvaluateParam')
		p.WriteLog(0)

def CalcRes():
	"""
	Calculate p.resfine and p.ncells according to p.meshlim criterion
	"""
	
	nloop=15
	p.ncells=0
	p.resfine=500.
	ecart=250.
	DIVIDE=True
	iloop=0
	iextra=0
	
	while iloop<nloop:
		
		iloop+=1
		
		if iextra==0:
			avancement=float(iloop)/nloop
			UpdateProgress(p.time2use,1,avancement,msg("Mesh resolution loop process"))
		else:
			avancement=float(iextra)/nloop
			UpdateProgress(p.time2use,1,avancement,msg("Mesh resolution loop process")+' - extra loops')
			
		if DIVIDE:	p.resfine=p.resfine-ecart
		else:		p.resfine=p.resfine+ecart

		file1=p.folder+'/FILES/tmp.geo'
		file2=p.folder+'/FILES/tmp.msh2'

		WriteGeo(p,file1,'fine',False)
		
		SubprocessCall("/usr/local/bin/gmsh4",'-v','0','-2',file1,'-o',file2)
		
		with open(file2,'r') as f: lines=f.readlines()
		
		nnodes=int(lines[4])
		nother=0
		WRONG=True
		while WRONG :
			line=lines[8+nnodes+nother]
			values=line.split()
			val=int(values[1])
			if val!=2: nother+=1
			else: WRONG=False
		p.ncells=(int(lines[7+nnodes])-nother)*p.nz
		DIVIDE=p.ncells<=p.meshlim
		
		ecart=ecart/2.
		ratio=float(p.ncells)/p.meshlim
		if iloop==nloop:
			if (ratio<0.95 or ratio>1.) and iextra<nloop:
				iextra+=1
				iloop-=1

def Mesh(ithread,code):
	"""
	Generates the ground meshes
	"""
	
	global istep

	try:

		istep+=1
	
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
				
		if code=='coarse':		message=msg("Generating ground mesh")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Generating ground mesh")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Generating ground mesh")+' ('+msg("reduced version")+')'
	
		start=time.time()
	
		UpdateProgress(time2use,ithread,0.05,message)
			
		WriteGeo(p,p.folder+'/FILES/'+code+'.geo',code)

		UpdateProgress(time2use,ithread,0.45,message)
		time.sleep(5.)
		
		file1=p.folder+'/FILES/'+code+'.geo'
		file2=p.folder+'/FILES/'+code+'.msh2'
	
		SubprocessCall("/usr/local/bin/gmsh4",'-v','0','-3',file1,'-o',file2)
		
		UpdateProgress(time2use,ithread,0.8,message)
	
		infile=open(p.folder+'/FILES/'+code+'.msh2','r')
		lines=infile.readlines()
		infile.close()
		
		ngroups=int(float(lines[4]))
		npts=int(float(lines[7+ngroups]))
			
		outfile=open(p.folder+'/FILES/'+code+'_ground_pts','w')
		for i in range(npts):
			values=lines[i+8+ngroups].split()
			if float(values[3])<1e-6: outfile.write('%20.2f'%float(values[1])+'\t'+'%20.2f'%float(values[2])+'\t'+'%15i'%float(values[0])+'\n')
		outfile.close()
	
		if code=='fine':
			p.resfine_coarse=p.rescoarse
			if LOCAL:
				xmlfile=p.projdir+'/MESH/meshes.xml'
				root=xml.parse(xmlfile).getroot()
				for bal in root:
					if bal.text==p.lname:
						bal.attrib['ncells']=str(p.ncells)
						xml.ElementTree(root).write(xmlfile)
						break
				outfile=open(PATH+'../../APPLI/TMP/'+time2use+'_new_message','w')
				outfile.write('%.2f Millions of Cells - Reso: %.1f meters'%(p.ncells/1000000.,p.resfine))
				outfile.close()
	
				xmlfile=p.folder+'/param.xml'
				root=xml.parse(xmlfile).getroot()
				root.find('resfine').text						='%.1f'%p.resfine
				root.find('rescoarse').text						='%.1f'%-1.0
				root.find('diadom').text						='%.1f'%p.diadom
				root.find('diaref').text						='%.1f'%p.diaref
				root.find('resratio').text						='%.1f'%p.resratio
				xml.SubElement(root,'resfine_coarse').text		='%.1f'%p.resfine_coarse
				xml.ElementTree(root).write(xmlfile)
			
			else:

				xmlfile=p.folder+'/param_cloud.xml'
				root=xml.Element('param')
				xml.SubElement(root,'resfine').text			='%.1f'%p.resfine
				xml.SubElement(root,'rescoarse').text		='%.1f'%-1.0
				xml.SubElement(root,'diadom').text			='%.1f'%p.diadom
				xml.SubElement(root,'diaref').text			='%.1f'%p.diaref
				xml.SubElement(root,'resratio').text		='%.1f'%p.resratio
				xml.SubElement(root,'resfine_coarse').text	='%.1f'%p.resfine_coarse
				xml.ElementTree(root).write(xmlfile)
	
		UpdateProgress(time2use,ithread,1.,' ')
	
		if code=='coarse':		p.duration_3=time.time()-start
		elif code=='reduced':	p.duration_4=time.time()-start
		elif code=='fine':		p.duration_5=time.time()-start

	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': Mesh(%s)'%code)
		p.WriteLog(0)

def AnalyseMesh(ithread,code):
	"""
	Analyses the ground meshes
	"""
	
	global istep

	try:

		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if code=='coarse':		message=msg("Analysing ground nodes")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Analysing ground nodes")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Analysing ground nodes")+' ('+msg("reduced version")+')'
		
		UpdateProgress(time2use,ithread,0.0,message)
		
		start=time.time()
		
		appli=PATH+'../../APPLI/TMP/./____'+time2use
		xmlfile=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'

		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text=message
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(appli,code,p.folder,xmlfile,str(ithread))
			RES=float(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES:
				try: print 'retry AnalyseMesh',code,it
				except: pass
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': AnalyseMesh(%s) (itmax)'%code)
			p.WriteLog(0,print_exc=False)

		istep+=1
		
		if code=='coarse':		p.duration_6=time.time()-start
		elif code=='reduced':	p.duration_7=time.time()-start
		elif code=='fine':		p.duration_8=time.time()-start

	except:

		p.errors.append(msg("ERROR")+' '+msg("within process")+': AnalyseMesh(%s)'%code)
		p.WriteLog(0)

def CalcRou(ithread,code):
	"""
	Evaluates roughness data on ground meshes
	"""
	
	global istep

	try:
	
		istep+=1
	
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if code=='coarse':		message=msg("Evaluating ground roughness")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Evaluating ground roughness")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Evaluating ground roughness")+' ('+msg("reduced version")+')'
		
		UpdateProgress(time2use,ithread,0.0,message)
		
		start=time.time()

		extra='___'
		
		appli=PATH+'../../APPLI/TMP/'+extra+time2use
		
		infile			=p.folder+'/FILES/'+code+'_facground'
		roufile			=PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsrou'
		outfile			=p.folder+'/FILES/'+code+'_roughness'
		xmlfile			=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'

		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text=message
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(appli,infile,roufile,outfile,xmlfile)
			RES=float(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES:
				try: print 'retry CalcRou',code,it
				except: pass
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcRou(%s) (itmax)'%code)
			p.WriteLog(0,print_exc=False)
		
		if code=='coarse':		p.duration_9=time.time()-start
		elif code=='reduced':	p.duration_10=time.time()-start
		elif code=='fine':		p.duration_11=time.time()-start
		
		UpdateProgress(time2use,ithread,1.,' ')

	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcRou(%s)'%code)
		p.WriteLog(0)

def PropaRou(ithread,code):
	"""
	Propagates the roughness information over the mesh
	"""
	
	global istep
	
	try:

		istep+=1
	
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if code=='coarse':		message=msg("Propagating ground roughness")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Propagating ground roughness")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Propagating ground roughness")+' ('+msg("reduced version")+')'
		
		UpdateProgress(time2use,ithread,0.0,message)
	
		start=time.time()
		
		
		args=[PATH+'../../APPLI/TMP/./______'+time2use]
	
		args.append(str(time2use))
		args.append(str(ithread))
		args.append(code)
		args.append(p.folder)
		args.append(message)
		
		xmlfile=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'
		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text=message
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(args)
			RES=float(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES:
				try: print 'retry PropaRou',code,it
				except: pass
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': PropaRou(%s) (itmax)'%code)
			p.WriteLog(0,print_exc=False)
	
		if code=='coarse':		p.duration_12=time.time()-start
		elif code=='reduced':	p.duration_13=time.time()-start
		elif code=='fine':		p.duration_14=time.time()-start
		
	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': PropaRou(%s)'%code)
		p.WriteLog(0)

def CalcOro(ithread,code,num):
	"""
	Evaluates elevation data on ground meshes
	"""
	
	global istep

	try:

		istep+=1
	
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if code=='coarse':		message=msg("Evaluating ground elevations")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Evaluating ground elevations")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Evaluating ground elevations")+' ('+msg("reduced version")+')'
		
		message+=' - '+num.split('_')[-1]
		
		UpdateProgress(time2use,ithread,0.0,message)
	
		start=time.time()

		extra='_'
		
		appli=PATH+'../../APPLI/TMP/'+extra+time2use

		infile			=p.folder+'/FILES/'+num
		orofile			=PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsoro'
		outfile			=p.folder+'/FILES/'+code+'_elevation_'+num.split('_')[-1]
		xmlfile			=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'

		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text=message
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall([appli,infile,orofile,outfile,xmlfile])
			RES=float(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES:
				try: print 'retry CalcOro',code,it
				except: pass
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcOro(%s) (itmax)'%code)
			p.WriteLog(0,print_exc=False)
		
		if code=='coarse':		p.duration_15=time.time()-start
		elif code=='reduced':	p.duration_16=time.time()-start
		elif code=='fine':		p.duration_17=time.time()-start
		
		UpdateProgress(time2use,ithread,1.,' ')

	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcOro(%s)'%code)
		p.WriteLog(0)

def PropaOro(ithread,code):
	"""
	Propagating the elevation data
	"""
	
	global istep
	
	try:

		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if code=='coarse':		message=msg("Propagating ground elevations")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Propagating ground elevations")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Propagating ground elevations")+' ('+msg("reduced version")+')'
		
		UpdateProgress(time2use,ithread,0.0,message)
		
		start=time.time()
		
		args=[PATH+'../../APPLI/TMP/./_____'+time2use]
		args.append(str(time2use))
		args.append(str(ithread))
		args.append(code)
		args.append(p.folder)
		args.append(message)
		args.append(str(p.nsmoo))
		args.append(str(p.smoocoef))
		args.append(str(p.insmoo))
		args.append(str(p.diadom))
		args.append(str(p.diaref))
		args.append(str(istep))
		args.append(str(nstep))

		SubprocessCall(args)
		
		istep+=3
		
		if code=='coarse':		message=msg("Elevating nodes")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Elevating nodes")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Elevating nodes")+' ('+msg("reduced version")+')'
		
		UpdateProgress(time2use,ithread,0.0,message)
		
		extra='________'
		appli=PATH+'../../APPLI/TMP/'+extra+time2use
		
		infile0			=p.folder+'/FILES/'+code+'_param'
		infile1			=p.folder+'/FILES/'+code+'_elevation'
		infile2			=p.folder+'/FILES/'+code+'_rough.msh2'
		outfile			=p.folder+'/FILES/'+code+'_elevation.msh2'
		xmlfile			=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'
		
		paramfile=open(infile0,'w')
		paramfile.write(str(p.htop)+'\n')
		paramfile.write(str(p.nzcst)+'\n')
		paramfile.write(str(len(p.z))+'\n')
		for z in p.z: paramfile.write(str(z)+'\n')
		paramfile.close()

		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text=message
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(appli,infile0,infile1,infile2,outfile,xmlfile)
			RES=float(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES:
				try: print 'retry PropaOro',code,it
				except: pass
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': PropaOro(%s) (itmax)'%code)
			p.WriteLog(0,print_exc=False)

		UpdateProgress(time2use,ithread,1.0,' ')
		
		istep+=1
		
		if code=='fine':
		
			infile=open(p.folder+'/FILES/propagate_param_'+code,'r')
			p.zmoy=float(infile.readline().rstrip())
			p.rescoarse=float(infile.readline().rstrip())
			infile.close()
		
		if code=='coarse':		p.duration_18=time.time()-start
		elif code=='reduced':	p.duration_19=time.time()-start
		elif code=='fine':		p.duration_20=time.time()-start
		
	except:

		p.errors.append(msg("ERROR")+' '+msg("within process")+': PropaOro(%s)'%code)
		p.WriteLog(0)

def InOut(ithread,code):
	"""
	Defines boundary conditions
	"""
	
	global istep
	
	try:

		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass

		if code=='coarse':		message=msg("Evaluating Boundary Conditions")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Evaluating Boundary Conditions")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Evaluating Boundary Conditions")+' ('+msg("reduced version")+')'

		UpdateProgress(time2use,ithread,0.0,message)
	
		start=time.time()
		
		args=[PATH+'../../APPLI/TMP/./_______'+time2use]
		args.append(str(time2use))
		args.append(str(ithread))
		args.append(code)
		args.append(p.folder)
		args.append(message)
		if code!='reduced': args.append(str(p.nsect))
		else: args.append(str(2))
		args.append(str(p.diaref))
		
		SubprocessCall(*args)

		infile=open(p.folder+'/FILES/inout_param_'+code,'r')
		_=int(float(infile.readline().rstrip()))
		rmoy_tot=float(infile.readline().rstrip())
		rmoy_int=float(infile.readline().rstrip())
		infile.close()
		
		if code=='fine':
			p.rmoy_tot=rmoy_tot
			p.rmoy_int=rmoy_int
		
		if code=='coarse':		p.duration_21=time.time()-start
		elif code=='reduced':	p.duration_22=time.time()-start
		elif code=='fine':		p.duration_23=time.time()-start
		
		UpdateProgress(time2use,ithread,1.,' ')

	except:

		p.errors.append(msg("ERROR")+' '+msg("within process")+': InOut(%s)'%code)
		p.WriteLog(0)

def Foam(ithread,code):

	global istep

	try:

		istep+=1
		
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		try: xml.ElementTree(rootprogress).write(progressfile)
		except: pass
		if not LOCAL:
			try:
				with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
			except: pass
		
		if code=='coarse':		message=msg("Generating OpenFOAM mesh files")+' ('+msg("coarse version")+')'
		elif code=='fine':		message=msg("Generating OpenFOAM mesh files")+' ('+msg("fine version")+')'
		elif code=='reduced':	message=msg("Generating OpenFOAM mesh files")+' ('+msg("reduced version")+')'
		
		UpdateProgress(time2use,ithread,0.1,message+' - gmshToFoam')
		
		start=time.time()
		
		initdir=PATH+'../../COMMON/foam/mesh_openfoam'
		targdir=p.folder+'/MESH_'+code.upper()
		subprocess.call(['mkdir', "-p", targdir])
		subprocess.call(['mkdir', "-p", targdir+'/0'])
		subprocess.call(['mkdir', "-p", targdir+'/0/include'])
		subprocess.call(['mkdir', "-p", targdir+'/constant'])
		subprocess.call(['mkdir', "-p", targdir+'/constant/polyMesh'])
		subprocess.call(['mkdir', "-p", targdir+'/system'])
		subprocess.call(['cp','-r',initdir+'/controlDict',targdir+'/system/'])
		subprocess.call(['cp','-r',initdir+'/fvSchemes',targdir+'/system/'])
		subprocess.call(['cp','-r',initdir+'/fvSolution',targdir+'/system/'])
		meshfile=p.folder+'/FILES/'+code+'_elevation.msh2'
		
		bin_path = os.path.join(OFPATH, "openfoam8/platforms/linux64GccDPInt32Opt/bin/gmshToFoam") 
		os.system('"'+bin_path+'" -case '+targdir+' '+meshfile+ SHELL_REDIR +targdir+'/log_gmshToFoam')
		OK=False
		with open(targdir+'/log_gmshToFoam','r') as infile:
			lines=infile.readlines()
			if lines[-2].rstrip()=='End': OK=True

		if not OK:
			p.OK=False
			p.errors.append(msg("ERROR")+' '+msg("within process")+': Foam(%s) - gmshToFoam'%code)
			p.WriteLog(0,print_exc=False)
		
		UpdateProgress(time2use,ithread,0.45,message+' - renumberMesh')
		
		bin_path = os.path.join(OFPATH, 'openfoam8/platforms/linux64GccDPInt32Opt/bin/renumberMesh') 
		os.system('"'+bin_path+'" -case '+targdir+ SHELL_REDIR +targdir+'/log_renumberMesh')
		OK=True
		if not OK:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': Foam(%s) - renumberMesh'%code)
			p.WriteLog(0,print_exc=False)
		
		subprocess.call(['cp','-rf',targdir+'/1/polyMesh',targdir+'/constant'])
		subprocess.call(['rm','-rf',targdir+'/1'])
		
		UpdateProgress(time2use,ithread,0.7,message+' - checkMesh')
		
		casedir=p.folder+'/MESH_'+code.upper()+'/'
		logfile=casedir+'log_checkMesh'
		
		bin_path = os.path.join(OFPATH, "openfoam8/platforms/linux64GccDPInt32Opt/bin/checkMesh") 
		os.system('"'+bin_path+'" -case '+casedir+' -constant'+ SHELL_REDIR + logfile)
		
		infile=open(logfile,'r')
		lines=infile.readlines()
		infile.close()
		
		nmax=30
		i=-1
		text=''
		valeur=-99.
		try:
			while i<nmax and text!='    Max aspect ratio ':
				i+=1
				line=lines[-i]
				text=line.split('=')[0]
			if line.split('=')[1][-4:-1]!='OK.': p.WARN_FINE=True
			try:	valeur=float(line.split('=')[1].split()[0])
			except:	p.WARN_FINE=True
		except:
			p.WARN_FINE=True
			i=-1
			while i<nmax and text!=' ***High aspect ratio cells found':
				i+=1
				line=lines[-i]
				text=line.split(',')[0]
			try:	valeur=float(line.split(':')[1].split()[0])[0]
			except:	p.WARN_FINE=True
		
		if code=='coarse':		p.ratiomax_coarse=valeur
		elif code=='reduced':	p.ratiomax_reduced=valeur
		elif code=='fine':		p.ratiomax_fine=valeur
		
		i=-1
		text=''
		valeur=-99.
		try:
			while i<nmax and text!='    Max skewness ' and text!=' ***Max skewness ':
				i+=1
				line=lines[-i]
				text=line.split('=')[0]
			if line.split('=')[1][-4:-1]!='OK.':
				if code=='coarse':		p.WARN_COARSE=True
				elif code=='fine':		p.WARN_FINE=True
				elif code=='reduced':	p.WARN_REDUCED=True
			try:	valeur=float(line.split('=')[1].split()[0])
			except:
				if code=='coarse':		p.WARN_COARSE=True
				elif code=='fine':		p.WARN_FINE=True
				elif code=='reduced':	p.WARN_REDUCED=True
		except: pass
		
		if code=='coarse':		p.skewmax_coarse=valeur
		elif code=='fine':		p.skewmax_fine=valeur
		elif code=='reduced':	p.skewmax_reduced=valeur
		
		i=-1
		text=''
		valeur=-99.
		try:
			while i<nmax and text!='    Mesh non-orthogonality':
				i+=1
				line=lines[-i]
				text=line[0:26]
			try: valeur=float(line.split()[3])
			except:
				if code=='coarse':		p.WARN_COARSE=True
				elif code=='fine':		p.WARN_FINE=True
				elif code=='reduced':	p.WARN_REDUCED=True
			if code=='coarse':		p.ortomax_coarse=valeur
			elif code=='fine':		p.ortomax_fine=valeur
			elif code=='reduced':	p.ortomax_reduced=valeur
			valeur=-99.
			try:	valeur=float(line.split()[-1])
			except:
				if code=='coarse':		p.WARN_COARSE=True
				elif code=='fine':		p.WARN_FINE=True
				elif code=='reduced':	p.WARN_REDUCED=True
		except: pass
		if code=='coarse':		p.ortomoy_coarse=valeur
		elif code=='fine':		p.ortomoy_fine=valeur
		elif code=='reduced':	p.ortomoy_reduced=valeur
		
		i=-1
		text=''
		valeur=-99.
		try:
			while i<nmax and text!='    Min volume':
				i+=1
				line=lines[-i]
				text=line[0:14]
			try:	valeur=float(line.split()[11][:-1])
			except:
				if code=='coarse':		p.WARN_COARSE=True
				elif code=='fine':		p.WARN_FINE=True
				elif code=='reduced':	p.WARN_REDUCED=True
		except: pass
		
		i=0
		FOUND=False
		while not FOUND and i<50:
			try:
				if lines[i][0:10]=='    cells:':
					FOUND=True
					ncells=int(float(lines[i].split()[-1]))
			except: pass
			i+=1
		
		if code=='coarse':		p.ncells_coarse		=ncells
		elif code=='fine':		p.ncells_fine		=ncells
		elif code=='reduced':	p.ncells_reduced	=ncells
	
		message+=' - foamToVTK'
		UpdateProgress(time2use,ithread,0.9,message)
		bin_path = os.path.join(OFPATH, 'openfoam8/platforms/linux64GccDPInt32Opt/bin/foamToVTK')
		os.system('"'+bin_path+'" -constant -case '+p.folder+'/MESH_%s'%code.upper()+ SHELL_REDIR + p.folder+'/MESH_%s/log_foamToVTK'%code.upper())
		
		if code=='coarse':		p.duration_24=time.time()-start
		elif code=='reduced':	p.duration_25=time.time()-start
		elif code=='fine':		p.duration_26=time.time()-start
		
		UpdateProgress(time2use,ithread,1.,' ')
		
	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': Foam(%s)'%code)
		p.WriteLog(0)

istep=0.
	
ReadParam()

nstep=44.+3*p.nproc
if p.resfine<0:		nstep+=1
if p.resratio>1.:	nstep+=1

EvaluateParam()

threads=[]
threads.append(THREAD_Prepa('coarse'))
threads.append(THREAD_Prepa('reduced'))
threads.append(THREAD_Prepa('fine'))
for thread in threads: thread.start()

threads=[]
code='coarse'
while not p.OK_coarse: time.sleep(0.33)
for idiv in range(p.nproc):
	num=code+'_ground_pts_%i'%idiv
	threads.append(THREAD_Oro(code,num))
	threads[-1].start()
code='reduced'
while not p.OK_reduced: time.sleep(0.33)
for idiv in range(p.nproc):
	num=code+'_ground_pts_%i'%idiv
	threads.append(THREAD_Oro(code,num))
	threads[-1].start()
code='fine'
while not p.OK_fine: time.sleep(0.33)
for idiv in range(p.nproc):
	num=code+'_ground_pts_%i'%idiv
	threads.append(THREAD_Oro(code,num))
	threads[-1].start()

for thread in threads: thread.join()

if p.nproc>3 and LOCAL:
	root=xml.parse(xmlfileproc).getroot()
	for bal in root:
		if bal.attrib['name']==p.name:
			bal.attrib['nproc']=str(3)
			xml.ElementTree(root).write(xmlfileproc)

for code in ['fine','reduced','coarse']:
	outfile=open(p.folder+'/FILES/'+code+'_elevation','w')
	for idiv in range(p.nproc):
		infile=open(p.folder+'/FILES/'+code+'_elevation_'+str(idiv),'r')
		lines=infile.readlines()
		infile.close()
		subprocess.call(['rm',p.folder+'/FILES/'+code+'_elevation_%i'%idiv])
		subprocess.call(['rm',p.folder+'/FILES/'+code+'_ground_pts_%i'%idiv])
		for line in lines: outfile.write(line)
	outfile.close()

threads=[]
threads.append(THREAD_PropaOro('fine'))
threads.append(THREAD_PropaOro('reduced'))
threads.append(THREAD_PropaOro('coarse'))

for thread in threads: thread.start()
for thread in threads: thread.join()

threads=[]
threads.append(THREAD_Inout('fine'))
threads.append(THREAD_Inout('reduced'))
threads.append(THREAD_Inout('coarse'))
for thread in threads: thread.start()
for thread in threads: thread.join()

threads=[]
threads.append(THREAD_Foam('reduced'))
threads.append(THREAD_Foam('coarse'))
if NEED_MEM:
	for thread in threads: thread.start()
	for thread in threads: thread.join()
	threads=[]
threads.append(THREAD_Foam('fine'))
for thread in threads: thread.start()
for thread in threads: thread.join()

threads=[]

for code in ['fine','reduced','coarse']:
	subprocess.call(['rm','-rf',p.folder+'/FILES/'+code+'.msh2'])
	subprocess.call(['rm','-rf',p.folder+'/FILES/'+code+'_elevation.msh2'])
	subprocess.call(['rm','-rf',p.folder+'/FILES/'+code+'_rough.msh2'])
	subprocess.call(['rm','-rf',p.folder+'/FILES/'+code+'_facground'])
	subprocess.call(['rm','-rf',p.folder+'/FILES/'+code+'_ground_pts'])

if not p.OK:
	p.errors.append('Probable Memory Failure')
	p.WriteLog(0)

directions=[]
step=360./p.nsect
direc=-step
isect=0
while isect<p.nsect:
	direc+=step
	directions.append(direc)
	isect+=1

time_END=time.time()
p.duration_tot=time_END-time_START

xmlfile=p.folder+'/param.xml'
root=xml.Element('param')
xml.SubElement(root,'nsect').text				=str(p.nsect)
xml.SubElement(root,'meshlim_i').text			='%.1f'%p.meshlim_i
xml.SubElement(root,'diadom_i').text			='%.1f'%p.diadom_i
xml.SubElement(root,'diaref_i').text			='%.1f'%p.diaref_i
xml.SubElement(root,'resfine_i').text			='%.1f'%p.resfine_i
xml.SubElement(root,'rescoarse_i').text			='%.1f'%p.rescoarse_i
xml.SubElement(root,'htop_i').text				='%.1f'%p.htop_i
xml.SubElement(root,'hcanop_i').text			='%.1f'%p.hcanop_i
xml.SubElement(root,'meshlim').text				='%.1f'%p.meshlim
xml.SubElement(root,'diadom').text				='%.1f'%p.diadom
xml.SubElement(root,'diaref').text				='%.1f'%p.diaref
xml.SubElement(root,'resfine').text				='%.1f'%p.resfine
xml.SubElement(root,'rescoarse').text			='%.1f'%p.rescoarse
xml.SubElement(root,'htop').text				='%.1f'%p.htop
xml.SubElement(root,'hcanop').text				='%.1f'%p.hcanop
xml.SubElement(root,'hturb').text				='%.1f'%p.hturb
xml.SubElement(root,'dztop').text				='%.1f'%p.dztop
xml.SubElement(root,'dzturb').text				='%.1f'%p.dzturb
xml.SubElement(root,'dzcanop').text				='%.1f'%p.dzcanop
xml.SubElement(root,'dzmin').text				='%.1f'%p.dzmin
xml.SubElement(root,'exptop').text				='%.2f'%p.exptop
xml.SubElement(root,'expturb').text				='%.2f'%p.expturb
xml.SubElement(root,'expcanop').text			='%.2f'%p.expcanop
xml.SubElement(root,'relax_distratio').text		='%.2f'%p.relax_distratio
xml.SubElement(root,'relax_resfactor').text		='%.2f'%p.relax_resfactor
xml.SubElement(root,'insmoo').text				=str(p.insmoo)
xml.SubElement(root,'nsmoo').text				=str(p.nsmoo)
xml.SubElement(root,'multizone').text			=str(p.multizone)
xml.SubElement(root,'nproc').text				=str(p.nproc)
xml.SubElement(root,'smoocoef').text			='%.1f'%p.smoocoef
xml.SubElement(root,'resdist').text				='%.1f'%p.resdist
xml.SubElement(root,'resratio').text			='%.1f'%p.resratio
xml.SubElement(root,'contcrit').text			=p.contcrit
xml.SubElement(root,'meshcrit').text			=p.meshcrit
xml.SubElement(root,'directions').text			=str(directions)
xml.SubElement(root,'z').text					=p.zline
xml.SubElement(root,'nzcst').text				=str(p.nzcst)
xml.SubElement(root,'resfine').text				='%.1f'%p.resfine
xml.SubElement(root,'resfine_coarse').text		='%.1f'%p.resfine_coarse
xml.SubElement(root,'rescoarse').text			='%.1f'%p.rescoarse
xml.SubElement(root,'rmoy_int').text			='%.4f'%p.rmoy_int
xml.SubElement(root,'rmoy_tot').text			='%.4f'%p.rmoy_tot
xml.SubElement(root,'zmoy').text				='%.1f'%p.zmoy
xml.SubElement(root,'diadom').text				='%.1f'%p.diadom
xml.SubElement(root,'diaref').text				='%.1f'%p.diaref
xml.SubElement(root,'resratio').text			='%.1f'%p.resratio
xml.SubElement(root,'ncells_coarse').text		=str(p.ncells_coarse)
xml.SubElement(root,'ncells_fine').text			=str(p.ncells_fine)
xml.SubElement(root,'ncells_reduced').text		=str(p.ncells_reduced)
xml.SubElement(root,'ratiomax_coarse').text		=str(p.ratiomax_coarse)
xml.SubElement(root,'ratiomax_fine').text		=str(p.ratiomax_fine)
xml.SubElement(root,'ratiomax_reduced').text	=str(p.ratiomax_reduced)
xml.SubElement(root,'ortomax_coarse').text		=str(p.ortomax_coarse)
xml.SubElement(root,'ortomax_fine').text		=str(p.ortomax_fine)
xml.SubElement(root,'ortomax_reduced').text		=str(p.ortomax_reduced)
xml.SubElement(root,'ortomoy_coarse').text		=str(p.ortomoy_coarse)
xml.SubElement(root,'ortomoy_fine').text		=str(p.ortomoy_fine)
xml.SubElement(root,'ortomoy_reduced').text		=str(p.ortomoy_reduced)
xml.SubElement(root,'skewmax_coarse').text		=str(p.skewmax_coarse)
xml.SubElement(root,'skewmax_fine').text		=str(p.skewmax_fine)
xml.SubElement(root,'skewmax_reduced').text		=str(p.skewmax_reduced)
xml.SubElement(root,'nproc').text				=str(p.nproc)
xml.SubElement(root,'warning_coarse').text		=str(p.WARN_COARSE)
xml.SubElement(root,'warning_fine').text		=str(p.WARN_FINE)
xml.SubElement(root,'warning_reduced').text		=str(p.WARN_REDUCED)
xml.SubElement(root,'machine').text				=p.machine
xml.SubElement(root,'version').text				=p.version
balise=xml.SubElement(root,'durations')
xml.SubElement(balise,'duration_tot').text		='%.2f'%p.duration_tot
xml.SubElement(balise,'duration_1').text		='%.2f'%p.duration_1
xml.SubElement(balise,'duration_2').text		='%.2f'%p.duration_2
xml.SubElement(balise,'duration_3').text		='%.2f'%p.duration_3
xml.SubElement(balise,'duration_4').text		='%.2f'%p.duration_4
xml.SubElement(balise,'duration_5').text		='%.2f'%p.duration_5
xml.SubElement(balise,'duration_6').text		='%.2f'%p.duration_6
xml.SubElement(balise,'duration_7').text		='%.2f'%p.duration_7
xml.SubElement(balise,'duration_8').text		='%.2f'%p.duration_8
xml.SubElement(balise,'duration_9').text		='%.2f'%p.duration_9
xml.SubElement(balise,'duration_10').text		='%.2f'%p.duration_10
xml.SubElement(balise,'duration_11').text		='%.2f'%p.duration_11
xml.SubElement(balise,'duration_12').text		='%.2f'%p.duration_12
xml.SubElement(balise,'duration_13').text		='%.2f'%p.duration_13
xml.SubElement(balise,'duration_14').text		='%.2f'%p.duration_14
xml.SubElement(balise,'duration_15').text		='%.2f'%p.duration_15
xml.SubElement(balise,'duration_16').text		='%.2f'%p.duration_16
xml.SubElement(balise,'duration_17').text		='%.2f'%p.duration_17
xml.SubElement(balise,'duration_18').text		='%.2f'%p.duration_18
xml.SubElement(balise,'duration_19').text		='%.2f'%p.duration_19
xml.SubElement(balise,'duration_20').text		='%.2f'%p.duration_20
xml.SubElement(balise,'duration_21').text		='%.2f'%p.duration_21
xml.SubElement(balise,'duration_22').text		='%.2f'%p.duration_22
xml.SubElement(balise,'duration_23').text		='%.2f'%p.duration_23
xml.SubElement(balise,'duration_24').text		='%.2f'%p.duration_24
xml.SubElement(balise,'duration_25').text		='%.2f'%p.duration_25
xml.SubElement(balise,'duration_26').text		='%.2f'%p.duration_26
xml.ElementTree(root).write(xmlfile)

subprocess.call(['rm','-f',PATH+'../../APPLI/TMP/'+time2use+'_new_message'])

if LOCAL:
	xmlfile=p.projdir+'/MESH/meshes.xml'
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			root=xml.parse(xmlfile).getroot()
			for bal in root:
				if bal.text==p.lname:
					size='%.1f'%(GetFolderSize(p.folder)/1.e+6)
					bal.attrib['name']=p.name
					bal.attrib['size']=size
					bal.attrib['used']='No'
					bal.attrib['ncells']=str(p.ncells_fine)
					bal.attrib['ndir']=str(p.nsect)
					bal.attrib['state']='Ready'
					bal.attrib['nproc']='-'
					bal.attrib['time2use']=time2use
					break
			root=SortXmlData(root)
			xml.ElementTree(root).write(xmlfile)
			OK=True
		except: time.sleep(0.1)

	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			root=xml.parse(xmlfileproc).getroot()
			for bal in root:
				if bal.attrib['code'] in ['cfd_mesh01','cfd_mesh02'] and bal.attrib['time']==time2use:
					root.remove(bal)
					break
			xml.ElementTree(root).write(xmlfileproc)
			OK=True
		except: time.sleep(0.1)

	EXTRA_Q=False
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			root=xml.parse(xmlfilequeue).getroot()
			for bal in root:
				if bal.attrib['code'] in ['cfd_mesh01','cfd_mesh02'] and bal.attrib['site']==p.site:
					EXTRA_Q=True
					break
			OK=True
		except: time.sleep(0.1)
	
	EXTRA_R=False
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			root=xml.parse(xmlfileproc).getroot()
			for bal in root:
				if bal.attrib['code'] in ['cfd_mesh01','cfd_mesh02'] and bal.attrib['site']==p.site:
					EXTRA_R=True
					break
			OK=True
		except: time.sleep(0.1)
	
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			root=xml.parse(xmlfileold).getroot()
			OK=True
		except: time.sleep(0.1)

	bal=xml.SubElement(root,'process')
	bal.attrib['username']=p.username
	bal.attrib['code']='cfd_mesh01'
	bal.attrib['name']=p.name
	bal.attrib['codename']=p.lname
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

	OK=False
	it=0
	while not OK and it<50:
		it+=1
		try:
			newtext=''
			root=xml.parse(xmlfilecfdprojects).getroot()
			for bal in root:
				if bal.text==p.site:
					newtext='Yes'
					if EXTRA_Q: newtext+='-Queued'
					if EXTRA_R: newtext+='-Running'
					bal.attrib['meshed']=newtext
					xml.ElementTree(root).write(xmlfilecfdprojects)
					OK=True
					break
		except: time.sleep(0.1)

else:
	
	with open('ok_CFD_MESH_01','w') as outfile: pass

p.errors=['"'+p.name+'" '+msg("has been generated")+'.']
p.WriteLog(1)
