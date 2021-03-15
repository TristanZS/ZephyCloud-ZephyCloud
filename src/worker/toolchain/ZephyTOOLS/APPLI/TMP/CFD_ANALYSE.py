#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from matplotlib.figure import Figure

from ZS_VARIABLES	import *
from ZS_COMMON		import FORTRAN_FILE,P_THREAD,CFD_PARAM,GetUITranslator
from ZS_COMMON		import GetFolderSize,GetDirect,UpdateProgress,GetMachine,SortXmlData,SubprocessCall

class PARAM(CFD_PARAM):
	
	def __init__(self,time2use,LOCAL):
		
		CFD_PARAM.__init__(self, '', time2use,LOCAL)
		self.type					='CFD_ANAL'
		self.code					='cfd_anal'
		
		self.liste_map				=[]
		self.liste_mapnum			=[]
		self.version				=''
		self.fileformat_oro			=''
		self.fileformat_rou			=''
		self.climato				=''
		self.rixcalc				=True
		self.rixrad					=-1.
		self.rixslope				=-1.
		self.rixres					=-1.
		self.rixncalc				=-1
		self.rixnsect				=-1
		self.autocontour			=-1
		self.contourlimit			=-1
		self.n_wt					=0
		self.n_mast					=0
		self.n_lidar				=0
		self.n_meso					=0
		self.n_mapping				=0
		self.n_usermap				=0
		self.n_point				=0
		self.iwt					=-1
		self.xref					=0.
		self.yref					=0.
		self.rix_mes				=0.
		self.rix_mach				=0.
		self.rixclim_mes			=0.
		self.rixclim_mach			=0.
		self.elevation_moy			=0.
		self.elevation_deltamax		=0.
		self.elevation_std			=0.
		self.slope_moy				=0.
		self.slope_max				=0.
		self.duration_tot			=0.
		self.duration_1				=0.
		self.duration_2				=0.
		
		self.RIX					=False
		self.ANALYZED				=False

time2use=basename(sys.argv[0])
LOCAL = True
if "CLOUD_WORKER" in os.environ and os.environ["CLOUD_WORKER"].strip() == "1":
	LOCAL = False
elif os.path.isfile(os.path.join(PATH, '..', '..', '..', 'conf')):
	LOCAL = False
itmax=20

try:
	language=sys.argv[-1]
	if language not in LANGUAGES.codes:	raise ValueError('bad language argument')
except:	language='EN'

time_START=time.time()

msg=GetUITranslator(language)

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

NCALC=[360,180,120,90,72]
NCALC2=[8,12,18,24,36]

figure=None
subplot=None
contour=None

class THREAD_CalcOro(P_THREAD):
	
	def __init__(self,num):
		
		self.num=num
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		CalcOro(ithread+1,self.num)
		
		self.postrun(ithread)

class THREAD_CalcSlope(P_THREAD):
	
	def __init__(self,num):
		
		P_THREAD.__init__(self,p.p_pool,p.nproc)
		self.num=num
	
	def run(self):
		
		ithread=self.prerun()
		
		CalcSlope(ithread+1,self.num)
		
		self.postrun(ithread)

class THREAD_CalcRix(P_THREAD):
	
	def __init__(self,num):
		
		P_THREAD.__init__(self,p.p_pool,p.nproc)
		self.num=num
	
	def run(self):
		
		ithread=self.prerun()
		
		CalcRix(ithread+1,self.num)
		
		self.postrun(ithread)

class THREAD_ReconstructOro(P_THREAD):
	
	def __init__(self):
		
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):
		
		ithread=self.prerun()
		
		ReconstructOro(ithread+1)
		
		self.postrun(ithread)

class THREAD_EvaluateSlopes(P_THREAD):
	
	def __init__(self):
		
		P_THREAD.__init__(self,p.p_pool,p.nproc)
	
	def run(self):

		ithread=self.prerun()
		
		EvaluateSlopes(ithread+1)
		
		self.postrun(ithread)
		
def ReadParam():
	"""
	Reads the process input parameters
	"""
	
	try:
		
		xmlfile=PATH+'../../APPLI/TMP/'+time2use+'.xml'
		root=xml.parse(xmlfile).getroot()
	
		p.site	=root.find('sitename').text
		p.name	=root.find('name').text
	
		p.lname		=p.site+'_'+p.name
		p.projdir	=PATH+'../../PROJECTS_CFD/'+p.site
		p.folder	=p.projdir+'/ANALYSE/'+p.lname
		
		if not os.path.isdir(p.projdir): subprocess.call(['mkdir', '-p', p.projdir])
		if not os.path.isdir(p.folder): subprocess.call(['mkdir', '-p', p.folder])
				
		if LOCAL:
			
			EXTRA_Q=False
			rootqueue=xml.parse(xmlfilequeue).getroot()
			for bal in rootqueue:
				if bal.attrib['code']=='cfd_anal' and bal.attrib['site']==p.site:
					EXTRA_Q=True
					break
	
			xmlfilecfd=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
	
			rootcfd=xml.parse(xmlfilecfd).getroot()
			
			for balcfd in rootcfd:
				
				if balcfd.text==p.site:
						
					newtext=''
					if 'Yes' in balcfd.attrib['analysed']:	newtext='Yes'
					else:									newtext='No'
					if EXTRA_Q: newtext+='-Queued'
					newtext+='-Running'
					balcfd.attrib['analysed']=newtext
					xml.ElementTree(rootcfd).write(xmlfilecfd)
					break 
	
			xmlfilelist=p.projdir+'/ANALYSE/analyses.xml'
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
		p.rixcalc		=eval(root.find('rixcalc').text)
		p.rixrad		=eval(root.find('rixrad').text)
		p.rixslope		=eval(root.find('rixslope').text)
		p.rixres		=eval(root.find('rixres').text)
		p.rixncalc		=NCALC[int(eval(root.find('rixncalc').text))]
		p.rixnsect		=LIST_NSECT[int(eval(root.find('rixnsect').text))]
		p.autocontour	=eval(root.find('autocontour').text)
		p.contourlimit	=eval(root.find('contourlimit').text)
		p.climato		=root.find('climato').text
		p.nproc			=int(eval(root.find('nproc').text))
		p.rixrad_site	=eval(root.find('rixrad_site').text)
		p.rixres_site	=eval(root.find('rixres_site').text)
		p.rixncalc_site	=NCALC2[int(eval(root.find('rixncalc_site').text))]
		
		for i in range(p.nproc):
			xmlfile=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(i+1)+'.xml'
			if not os.path.isfile(xmlfile):
				root=xml.Element('logout')
				xml.SubElement(root,'progress_text').text=''
				xml.SubElement(root,'progress_frac').text=str(0)
				xml.ElementTree(root).write(xmlfile)
	
		p.npl		=int(p.rixrad/p.rixres)
		p.npl_site	=int(p.rixrad_site/p.rixres_site)
	
		p.fd=np.zeros(p.rixnsect)
		p.fd_site=np.zeros(p.rixncalc_site)
		
		if p.climato!='no':
			
			name=os.path.splitext(p.climato)[0].strip()
			dirname=p.projdir+'/INPUT_FILES/CLIMATO/'+name+'/'
	
			ih=0
	
			infile=FORTRAN_FILE(dirname+'fdd_'+str(ih))
			fdd=infile.readReals(prec='d')
			infile.close()
		
			sect=360./p.rixnsect
		
			for idirec in range(p.rixnsect):
				dir1=sect*(idirec-0.5)
				dir2=dir1+sect
				idir1=int(dir1)
				idir2=int(dir2)+1
				for idir in range(idir1,idir2):
					idd=idir
					if idd<0: idd+=360
					if idd>=360: idd -= 360
					if idirec==0 and idir==idir1: ifirst=idd
					if idirec==p.rixnsect-1 and idir==idir2-1: ilast=idd
					else: ilast=ifirst
					if idir==idir1 or idir==idir2-1: p.fd[idirec]+=fdd[idd]/2.
					else: p.fd[idirec]+=fdd[idd]
				if ifirst!=ilast: p.fd[idirec]+=fdd[idd]/2.+fdd[idd+1]/2.
	
			sect=360./p.rixncalc_site
			for idirec in range(p.rixncalc_site):
				dir1=sect*(idirec-0.5)
				dir2=dir1+sect
				idir1=int(dir1)
				idir2=int(dir2)+1
				for idir in range(idir1,idir2):
					idd=idir
					if idd<0: idd+=360
					if idd>=360: idd -= 360
					if idirec==0 and idir==idir1: ifirst=idd
					if idirec==p.rixncalc_site-1 and idir==idir2-1: ilast=idd
					else: ilast=ifirst
					if idir==idir1 or idir==idir2-1: p.fd_site[idirec]+=fdd[idd]/2.
					else: p.fd_site[idirec]+=fdd[idd]
				if ifirst!=ilast: p.fd_site[idirec]+=fdd[idd]/2.+fdd[idd+1]/2.
	
		xmlfile=p.projdir+'/DATA/data.xml'
		root=xml.parse(xmlfile).getroot()
		p.fileformat_oro	=root.find('fileformat_oro').text
		p.fileformat_rou	=root.find('fileformat_rou').text
		p.n_wt				=int(eval(root.find('n_wt').text))
		p.n_mast			=int(eval(root.find('n_mast').text))
		p.n_lidar			=int(eval(root.find('n_lidar').text))
		p.n_meso			=int(eval(root.find('n_meso').text))
		p.n_mapping			=int(eval(root.find('n_mapping').text))
		p.n_usermap			=int(eval(root.find('n_usermap').text))
		p.n_point			=int(eval(root.find('n_point').text))
		p.n_line			=int(eval(root.find('n_line').text))
		p.np_data			=eval(root.find('np_data').text)
	
		xmlfile=p.projdir+'/site.xml'
		root=xml.parse(xmlfile).getroot()
		p.diamin=eval(root.find('diamin').text)
		
		if LOCAL:
			
			xmlfile=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
			root=xml.parse(xmlfile).getroot()
			for site in root:
				if site.text==p.site:
					if 'Yes' in site.attrib['analysed']:
						p.ANALYZED=True
						break
	
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

def CalcOro(ithread,num):
	"""
	Evaluates elevation data
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
		
		UpdateProgress(time2use,ithread,0.,msg("Evaluating Elevations on Result Points")+' - %s'%(num.split('_')[-1]))
		
		extra='_'
		
		appli=PATH+'../../APPLI/TMP/'+extra+time2use
		
		xmlfile			=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'
		elevationfile	=p.projdir+'/DATA/zsoro'
		
		infile=p.projdir+'/DATA/'+num
		outfile=infile+'_z'
		
		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text='Evaluating Elevations'
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(appli,infile,elevationfile,outfile,xmlfile)
			RES=eval(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES: print 'retry CalcOro',num,it
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcOro(%s) (itmax)'%(num))
			p.WriteLog(0,print_exc=False)

		UpdateProgress(time2use,ithread,1.,' ')

	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcOro(%s)'%(num))
		p.WriteLog(0)

def CalcSlope(ithread,num):
	"""
	Evaluates elevation data over the points related to slope calculation
	"""
	
	global istep
	
	istep+=1
	rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
	rootprogress.find('progress_frac').text=str(istep/nstep)
	if not LOCAL:
		try:
			with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
		except: pass
	
	UpdateProgress(time2use,ithread,0.0,msg("Slope calculation process - Elevations")+' - '+num.split('_')[-1])

	try:

		extra='____'
		appli			=PATH+'../../APPLI/TMP/'+extra+time2use
		xmlfile			=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'
		elevationfile	=p.projdir+'/DATA/zsoro'
		infile			=p.folder+'/'+num
		outfile			=p.folder+'/'+num+'_z'

		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text='Evaluating Slopes'
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(appli,infile,elevationfile,outfile,xmlfile)
			RES=eval(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if RES:
				with open(infile,'r') as inpfile: lines1=inpfile.readlines()
				with open(outfile,'r') as inpfile: lines2=inpfile.readlines()
				if len(lines1)!=len(lines2): RES=False
			if not RES: print 'retry CalcSlope',num,it
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcSlope (itmax)')
			p.WriteLog(0,print_exc=False)
	
		UpdateProgress(time2use,ithread,1.,' ')
	
	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcSlope')
		p.WriteLog(0)

def CalcRix(ithread,num):
	"""
	Evaluates elevation data over the points related to rix calculation
	"""
	
	global istep
	
	istep+=1
	rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
	rootprogress.find('progress_frac').text=str(istep/nstep)
	try: xml.ElementTree(rootprogress).write(progressfile)
	except: pass
	if not LOCAL:
		try:
			with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
		except: pass
	
	UpdateProgress(time2use,ithread,0.0,msg("RIX calculation process - Elevations")+' - '+num.split('_')[-1])

	try:

		extra='____'
		appli			=PATH+'../../APPLI/TMP/'+extra+time2use
		xmlfile			=PATH+'../../APPLI/TMP/logout_'+time2use+'_'+str(ithread)+'.xml'
		elevationfile	=p.projdir+'/DATA/zsoro'
		infile			=p.folder+'/'+num
		outfile			=p.folder+'/'+num+'_z'

		it=0
		RES=False
		while not RES and it<=itmax:
			root=xml.Element('logout')
			xml.SubElement(root,'progress_text').text='Evaluating RIX'
			xml.SubElement(root,'progress_frac').text=str(0)
			xml.ElementTree(root).write(xmlfile)
			it+=1
			SubprocessCall(appli,infile,elevationfile,outfile,xmlfile)
			RES=eval(xml.parse(xmlfile).getroot().find('progress_frac').text)==1.0
			if not RES: print 'retry CalcRix',num,it
		if not RES:
			p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcRix (itmax)')
			p.WriteLog(0,print_exc=False)
	
		UpdateProgress(time2use,ithread,1.,' ')
	
	except:
		traceback.print_exc()
		p.errors.append(msg("ERROR")+' '+msg("within process")+': CalcRix')
		p.WriteLog(0)

def ReconstructOro(ithread):

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
		
		UpdateProgress(time2use,ithread,0.,'ReconstructOro')
		
		x,y,z=[],[],[]
		
		for idiv in range(100):
			
			UpdateProgress(time2use,ithread,float(idiv+1)/100,'ReconstructOro')
			
			with open(p.projdir+'/DATA/loc_'+str(idiv).zfill(2)+'_z','r') as infile: lines=infile.readlines()
			subprocess.call(['mv',p.projdir+'/DATA/loc_'+str(idiv).zfill(2)+'_z',p.projdir+'/DATA/loc_'+str(idiv).zfill(2)])
			for line in lines:
				vals=line.split()
				x.append(eval(vals[0]))
				y.append(eval(vals[1]))
				z.append(eval(vals[2]))
		
		locdata=[]
		itot=-1
		for elem in p.np_data:
			name=elem[0]
			npp=elem[1]
			if npp>0:
				with open(p.projdir+'/DATA/elevations_'+name,'w') as outfile:
					for _ in range(npp):
						itot+=1
						outfile.write('%20.2f%20.2f%20.2f\n'%(x[itot],y[itot],z[itot]))
						if name=='complex_glob': locdata.append(z[itot])
		itot+=1
		
		locdata=np.array(locdata)
		p.elevation_moy=np.average(locdata)
		p.elevation_deltamax=np.max(locdata)-np.min(locdata)
		p.elevation_std=np.std(locdata)
		
		with open(p.projdir+'/centre','w') as outfile: outfile.write(str(p.elevation_moy))
		
		UpdateProgress(time2use,ithread,1.,' ')
	
	except:
		
		p.errors.append(msg("ERROR")+' '+msg("within process")+': ReconstructOro')
		p.WriteLog(0)

def EvaluateSlopes(ithread):

	global istep,figure,subplot,contour
	
	istep+=1
	rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
	rootprogress.find('progress_frac').text=str(istep/nstep)
	try: xml.ElementTree(rootprogress).write(progressfile)
	except: pass
	if not LOCAL:
		try:
			with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
		except: pass
	
	UpdateProgress(time2use,ithread,0.05,msg("Slope calculation process - Construction"))

	try:

		with open(p.folder+'/slope_points_z','w') as outfile:
			for idiv in range(p.nproc):
				infile=open(p.folder+'/slope_points_'+str(idiv)+'_z','r')
				lines=infile.readlines()
				infile.close()
				subprocess.call(['rm',p.folder+'/slope_points_'+str(idiv)])
				subprocess.call(['rm',p.folder+'/slope_points_'+str(idiv)+'_z'])
				for line in lines: outfile.write(line)
		
		UpdateProgress(time2use,ithread,0.15,msg("Slope calculation process - Construction"))
	
		zf=[]
		with open(p.folder+'/slope_points_z','r') as infile: lines=infile.readlines()
		
		for line in lines: zf.append(eval(line.split()[2]))
	
		UpdateProgress(time2use,ithread,0.20,msg("Slope calculation process - Construction"))
		
		itot=-1
		slopes=[]
		for _ in range(p.nsite):
			slopes.append([])
			for __ in range(p.rixncalc_site):
				slopes[-1].append([])
				for iseg in range(p.npl_site+1):
					itot+=1
					if iseg>0:
						slope=(zf[itot]-zf[itot-1])/p.rixres_site
						slopes[-1][-1].append(np.arctan((slope))*180./np.pi)
	
		UpdateProgress(time2use,ithread,0.40,msg("Slope calculation process - Construction"))
	
		res=[]
		for slope_point in slopes:
			res.append([0.]*(p.rixncalc_site+1))
			idir=-1
			for slope_dir in slope_point:
				idir+=1
				direc=idir*360./p.rixncalc_site
				idirec=GetDirect(p.rixncalc_site,direc)
				for slope in slope_dir: res[-1][idirec]+=abs(slope)
			for idir in range(p.rixncalc_site): res[-1][idir]=res[-1][idir]/p.npl_site
			res[-1][-1]=np.average(res[-1][0:p.rixncalc_site])
	
		UpdateProgress(time2use,ithread,0.60,msg("Slope calculation process - Construction"))
			
		resslopes=[]
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/slope_site','w') as f:
			ip=-1
			for result in res:
				ip+=1
				if abs(np.sqrt(p.xsite[ip]**2+p.ysite[ip]**2)-(p.diamin+1000.)/2.)>5.:	f.write('%15.2f%15.2f%15.2f\n'%(p.xsite[ip],p.ysite[ip],result[-1]))
				else:																		f.write('%15.2f%15.2f%15.2f\n'%(p.xsite[ip],p.ysite[ip],0.))
				resslopes.append(result[-1])
		
		resslopes=np.array(resslopes)
		p.slope_moy=np.average(resslopes)
		p.slope_max=np.max(resslopes)
	
		subprocess.call(['rm',p.folder+'/slope_points'])
		subprocess.call(['rm',p.folder+'/slope_points_z'])
	
		x,y,z=np.loadtxt(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/slope_site',unpack=True)
		
		autocontour=p.autocontour
		contourlimit=p.contourlimit
		results=[]
		step=0.1
		val=autocontour-step

		zmin,zmax=min(z),max(z)
		
		if zmin<val and val<zmax:

			VALID=False
			contour=None
		
			while not VALID:
				val+=step
				if figure is not None:
					Figure.clear(figure)
					subplot.clear()
					if contour!=None: del contour
			
				figure=Figure()
				subplot=figure.add_axes([0.,0.,1.,1.])
				
				contour=subplot.tricontour(x,y,z,[val])
				disttot=0
				results=[]
				for collec in contour.collections:
					contours=collec.get_paths()
					for path in contours:
						results.append([])
						v=path.vertices
						xx=v[:,0]
						yy=v[:,1]
						dist=0
						for i in range(len(xx)-1): dist+=np.sqrt((xx[i+1]-xx[i])**2+(yy[i+1]-yy[i])**2)
						for i in range(len(xx)): results[-1].append((xx[i],yy[i]))
						disttot+=dist
				VALID=disttot<contourlimit
		
		xmlfile=p.projdir+'/contours.xml'
		root=xml.parse(xmlfile).getroot()
		bal=xml.SubElement(root,'contour')
		bal.text=str(results)
		bal.attrib['name']='Slope:Auto'
		bal.attrib['type']='anal'
		bal.attrib['inp']='auto'
		bal.attrib['variable']='auto'
		bal.attrib['value']='%.1f'%val
		bal.attrib['comments']='Automatically generated'
		bal.attrib['usedby']='[]'
		xml.ElementTree(root).write(xmlfile)
	
		UpdateProgress(time2use,ithread,1.0,msg("Slope calculation process - Construction"))

	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': EvaluateSlopes')
		p.WriteLog(0)

def EvaluateRix():

	global istep
	
	istep+=1
	rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
	rootprogress.find('progress_frac').text=str(istep/nstep)
	try: xml.ElementTree(rootprogress).write(progressfile)
	except: pass
	if not LOCAL:
		try:
			with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
		except: pass
	
	UpdateProgress(time2use,1,0.05,msg("RIX calculation process - Construction"))

	try:
	
		with open(p.folder+'/rix_points_z','w') as outfile:
			for idiv in range(p.nproc):
				infile=open(p.folder+'/rix_points_'+str(idiv)+'_z','r')
				lines=infile.readlines()
				infile.close()
				subprocess.call(['rm',p.folder+'/rix_points_'+str(idiv)])
				subprocess.call(['rm',p.folder+'/rix_points_'+str(idiv)+'_z'])
				for line in lines: outfile.write(line)
		
		zf=[]
		with open(p.folder+'/rix_points_z','r') as infile: lines=infile.readlines()
		
		for line in lines: zf.append(eval(line.split()[2]))
		
		itot=-1
		slopes=[]
		for _ in range(p.nloc):
			slopes.append([])
			for _ in range(p.rixncalc):
				slopes[-1].append([])
				for iseg in range(p.npl):
					itot+=1
					if iseg>0:
						slope=(zf[itot]-zf[itot-1])/p.rixres
						slopes[-1][-1].append(np.arctan((slope))*180./np.pi)
		
		res=[]
		for slope_point in slopes:
			res.append([0.]*(p.rixnsect+2))
			nres=[0]*p.rixnsect
			idir=-1
			for slope_dir in slope_point:
				idir+=1
				direc=idir*360./p.rixncalc
				idirec=GetDirect(p.rixnsect,direc)
				nres[idirec]+=1
				for slope in slope_dir:
					if abs(slope)>p.rixslope: res[-1][idirec]+=1
			for idir in range(p.rixnsect):
				if nres[idir]>0: res[-1][idir]=res[-1][idir]/nres[idir]
			
			res[-1][-2]=np.average(res[-1][0:p.rixnsect])
			if p.climato!='no': res[-1][-1]=np.sum((np.array(res[-1][0:p.rixnsect]))*np.array(p.fd))
		
		ip=-1
		if p.n_mast>0:
			with open(p.folder+'/rix_mast','w') as f:
				for _ in range(p.n_mast):
					ip+=1
					resline=''
					for elem in res[ip]: resline+=('%.1f'%elem).rjust(10)
					f.write(resline+"\n")
					p.rix_mes+=res[ip][-2]
					p.rixclim_mes+=res[ip][-1]
		if  p.n_lidar>0:
			with open(p.folder+'/rix_lidar','w') as f:
				for _ in range(p.n_lidar):
					ip+=1
					resline=''
					for elem in res[ip]: resline+=('%.1f'%elem).rjust(10)
					f.write(resline+'\n')
					p.rix_mes+=res[ip][-2]
					p.rixclim_mes+=res[ip][-1]
		if p.n_mast+p.n_lidar>0:
			p.rix_mes/=(p.n_mast+p.n_lidar)
			p.rixclim_mes/=(p.n_mast+p.n_lidar)
		
		if p.n_wt>0:
			with open(p.folder+'/rix_wt','w') as f:
				for _ in range(p.n_wt):
					ip+=1
					resline=''
					for elem in res[ip]: resline+=('%.1f'%elem).rjust(10)
					f.write(resline+'\n')
					p.rix_mach+=res[ip][-2]
					p.rixclim_mach+=res[ip][-1]
			p.rix_mach/=p.n_wt
			p.rixclim_mach/=p.n_wt
		
		subprocess.call(['rm',p.folder+'/rix_points'])
		subprocess.call(['rm',p.folder+'/rix_points_z'])

	except:
		p.errors.append(msg("ERROR")+' '+msg("within process")+': EvaluateRix')
		p.WriteLog(0)
		
istep=0.
nstep=102

ReadParam()

nstep+=p.nproc
if not p.ANALYZED: nstep+=2*p.nproc

start=time.time()

threads=[]

if not p.ANALYZED:

	lines=[]
	for idiv in range(100):
		num='loc_%s'%(str(idiv).zfill(2))
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/'+num,'r') as infile: lines+=infile.readlines()
		threads.append(THREAD_CalcOro(num))
		threads[-1].start()
	
	tot=0
	for data in p.np_data:
		n=data[1]
		if data[0]!='complex_loc': tot+=n
		else:
			lines=lines[tot:tot+n]
			break

	p.xf=[]
	p.yf=[]
	
	p.xsite=[]
	p.ysite=[]
	for iline in range(len(lines)):
		values=lines[iline].split()
		p.xsite.append(eval(values[0]))
		p.ysite.append(eval(values[1]))
		for i in range(p.rixncalc_site):
			angle=360*i/p.rixncalc_site
			for j in range(p.npl_site+1):
				p.xf.append(p.xsite[-1]+j*p.rixres_site*np.cos(angle*np.pi/180))
				p.yf.append(p.ysite[-1]+j*p.rixres_site*np.sin(angle*np.pi/180))

	p.nsite=len(p.xsite)
	p.npts_site=len(p.xf)
	
	lines=[]
	with open(p.folder+'/slope_points','w') as outfile:
		for ip in range(p.npts_site):
			lines.append(str(p.xf[ip])+'\t'+str(p.yf[ip])+'\n')
			outfile.write(lines[-1])

	np_first=p.npts_site/p.nproc
	np_then=p.npts_site-(p.nproc-1)*np_first
	for idiv in range(p.nproc):
		num='slope_points_%i'%idiv
		with open(p.folder+'/'+num,'w') as outfile:
			ifirst=idiv*np_first
			if idiv!=p.nproc-1: ilast=(idiv+1)*np_first
			else: ilast=idiv*np_first+np_then
			for il in range(ifirst,ilast): outfile.write(lines[il])
		
		threads.append(THREAD_CalcSlope(num))
		threads[-1].start()
	
	for thread in threads: thread.join()

	threads=[]
	threads.append(THREAD_ReconstructOro())
	threads.append(THREAD_EvaluateSlopes())
	for thread in threads: thread.start()
	for thread in threads: thread.join()
	
	p.duration_1+=time.time()-start

	xmlfile=p.projdir+'/DATA/data.xml'
	root=xml.parse(xmlfile).getroot()

	xml.SubElement(root,'anal_rixrad_site').text		='%.1f'%p.rixrad_site
	xml.SubElement(root,'anal_rixres_site').text		='%.1f'%p.rixres_site
	xml.SubElement(root,'anal_rixncalc_site').text		=str(p.rixncalc_site)
	xml.SubElement(root,'anal_autocontour').text		='%.1f'%p.autocontour
	xml.SubElement(root,'anal_contourlimit').text		='%.1f'%p.contourlimit
	xml.SubElement(root,'anal_elevation_deltamax').text	='%.1f'%p.elevation_deltamax
	xml.SubElement(root,'anal_elevation_moy').text		='%.1f'%p.elevation_moy
	xml.SubElement(root,'anal_elevation_std').text		='%.1f'%p.elevation_std
	xml.SubElement(root,'anal_slope_moy').text			='%.1f'%p.slope_moy
	xml.SubElement(root,'anal_slope_max').text			='%.1f'%p.slope_max
	xml.SubElement(root,'anal_duration').text			='%.2f'%p.duration_1
	xml.SubElement(root,'anal_nproc').text				=str(p.nproc)
	xml.ElementTree(root).write(xmlfile)

	if LOCAL:
		
		xmlfile=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if bal.text==p.site:
				bal.attrib['analysed']='Yes-Running'
				xml.ElementTree(root).write(xmlfile)
				break
	
		if p.rixcalc:
			xmlfile=p.projdir+'/messages.xml'
			try:	root=xml.parse(xmlfile).getroot()
			except:	root=xml.Element('messages')
			bal=xml.SubElement(root,'message')
			bal.text='Project has been analysed.'
			bal.text+=' RIX analysis is going on'+'...'
			bal.attrib['num']='x'
			bal.attrib['code']='cfd_anal'
			bal.attrib['name']=p.name
			bal.attrib['time']=time2use
			xml.ElementTree(root).write(xmlfile)

start=time.time()

threads=[]

istep+=1
rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
rootprogress.find('progress_frac').text=str(istep/nstep)
try: xml.ElementTree(rootprogress).write(progressfile)
except: pass
if not LOCAL:
	try:
		with open(PATH+'../../../progress.txt','w') as pf: pf.write(str(istep/nstep))
	except: pass

UpdateProgress(time2use,1,0.15,msg("RIX calculation process - Preparation"))

if p.rixcalc:

	p.xf=[]
	p.yf=[]
	
	xloc=[]
	yloc=[]
	
	if p.n_mast>0:
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zsmast','r') as infile:
			lines=infile.readlines()
			for line in lines:
				vals=line.rstrip().split()
				xloc.append(eval(vals[0]))
				yloc.append(eval(vals[1]))
				for i in range(p.rixncalc):
					angle=360*i/p.rixncalc
					for j in range(p.npl):
						p.xf.append(xloc[-1]+(j+1)*p.rixres*np.cos(angle*np.pi/180))
						p.yf.append(yloc[-1]+(j+1)*p.rixres*np.sin(angle*np.pi/180))
	if p.n_wt>0:
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zswt','r') as infile:
			lines=infile.readlines()
			for line in lines:
				vals=line.rstrip().split()
				xloc.append(eval(vals[0]))
				yloc.append(eval(vals[1]))
				for i in range(p.rixncalc):
					angle=360*i/p.rixncalc
					for j in range(p.npl):
						p.xf.append(xloc[-1]+(j+1)*p.rixres*np.cos(angle*np.pi/180))
						p.yf.append(yloc[-1]+(j+1)*p.rixres*np.sin(angle*np.pi/180))

	if p.n_lidar>0:
		with open(PATH+'../../PROJECTS_CFD/'+p.site+'/DATA/zslidar','r') as infile:
			lines=infile.readlines()
			for line in lines:
				vals=line.rstrip().split()
				xloc.append(eval(vals[0]))
				yloc.append(eval(vals[1]))
				for i in range(p.rixncalc):
					angle=360*i/p.rixncalc
					for j in range(p.npl):
						p.xf.append(xloc[-1]+(j+1)*p.rixres*np.cos(angle*np.pi/180))
						p.yf.append(yloc[-1]+(j+1)*p.rixres*np.sin(angle*np.pi/180))
						
	UpdateProgress(time2use,1,0.35,msg("RIX calculation process - Preparation"))
	
	p.nloc=len(xloc)
	p.npts=len(p.xf)
		
	UpdateProgress(time2use,1,0.65,msg("RIX calculation process - Preparation"))
	
	lines=[]
	with open(p.folder+'/rix_points','w') as outfile:
		for ip in range(p.npts):
			lines.append(str(p.xf[ip])+'\t'+str(p.yf[ip])+'\n')
			outfile.write(lines[-1])
	
	UpdateProgress(time2use,1,1.0,' ')
	
	np_first=p.npts/p.nproc
	np_then=p.npts-(p.nproc-1)*np_first
	for idiv in range(p.nproc):
		num='rix_points_%i'%idiv
		with open(p.folder+'/'+num,'w') as outfile:
			ifirst=idiv*np_first
			if idiv!=p.nproc-1: ilast=(idiv+1)*np_first
			else: ilast=idiv*np_first+np_then
			for il in range(ifirst,ilast): outfile.write(lines[il])
		threads.append(THREAD_CalcRix(num))
		threads[-1].start()
	
	for thread in threads: thread.join()
	
	EvaluateRix()

p.duration_2+=time.time()-start

time_END=time.time()
p.duration_tot=time_END-time_START

xmlfile=p.folder+'/param.xml'
root=xml.Element('analysis')
xml.SubElement(root,'rix_mes').text			='%.2f'%p.rix_mes
xml.SubElement(root,'rix_mach').text		='%.2f'%p.rix_mach
xml.SubElement(root,'rixclim_mes').text		='%.2f'%p.rixclim_mes
xml.SubElement(root,'rixclim_mach').text	='%.2f'%p.rixclim_mach
xml.SubElement(root,'nproc').text			=str(p.nproc)
xml.SubElement(root,'rixcalc').text			='%.1f'%p.rixcalc
xml.SubElement(root,'rixrad').text			='%.1f'%p.rixrad
xml.SubElement(root,'rixslope').text		='%.1f'%p.rixslope
xml.SubElement(root,'rixres').text			='%.1f'%p.rixres
xml.SubElement(root,'rixncalc').text		=str(p.rixncalc)
xml.SubElement(root,'rixnsect').text		=str(p.rixnsect)
xml.SubElement(root,'climato').text			=str(p.climato)
xml.SubElement(root,'machine').text			=p.machine
xml.SubElement(root,'version').text			=p.version
balise=xml.SubElement(root,'durations')
xml.SubElement(balise,'duration_tot').text	='%.2f'%p.duration_tot
xml.SubElement(balise,'duration_1').text	='%.2f'%p.duration_1
xml.SubElement(balise,'duration_2').text	='%.2f'%p.duration_2
xml.ElementTree(root).write(xmlfile)

if LOCAL:
	xmlfile=p.projdir+'/ANALYSE/analyses.xml'
	OK,it=False,0
	while not OK and it<50:
		it+=1
		try:
			root=xml.parse(xmlfile).getroot()
			bal2use=None
			for bal in root:
				if bal.text==p.lname:
					size='%.3f'%(GetFolderSize(p.folder)/1.e+6)
					bal.attrib['name']=p.name
					bal.attrib['size']=size
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
				if bal.attrib['code']=='cfd_anal' and bal.attrib['time']==time2use:
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
				if bal.attrib['code']=='cfd_anal' and bal.attrib['site']==p.site:
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
				if bal.attrib['code']=='cfd_anal' and bal.attrib['site']==p.site:
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
	bal.attrib['code']='cfd_anal'
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
	
	OK=False
	it=0
	while not OK and it<50:
		it+=1
		try:
			newtext=''
			root=xml.parse(xmlfilecfdprojects).getroot()
			for bal in root:
				if bal.text==p.site:
					if 'Yes' in bal.attrib['analysed']:	newtext='Yes'
					else:								newtext='No'
					if EXTRA_Q: newtext+='-Queued'
					if EXTRA_R: newtext+='-Running'
					bal.attrib['analysed']=newtext
					xml.ElementTree(root).write(xmlfilecfdprojects)
					OK=True
					break
		except: time.sleep(0.1)

else:
	
	with open('ok_CFD_ANALYSE','w') as outfile: pass

xmlfile=p.projdir+'/messages.xml'
try:	root=xml.parse(xmlfile).getroot()
except:	root=xml.Element('messages')
for bal in root:
	if bal.attrib['time']==time2use:
		root.remove(bal)
		break
xml.ElementTree(root).write(xmlfile)

p.errors=['"'+p.site+'" '+msg("has been analysed")+'.']
p.WriteLog(1)
