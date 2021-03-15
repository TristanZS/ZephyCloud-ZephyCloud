#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from zc_variables import *

from math import floor,ceil,sqrt,cos,sin,tan,pi,log,exp,log10,degrees,atan2,radians,acos,asin,atan,sinh
import os,sys,subprocess,gc,signal,time,multiprocessing,threading,psutil,sqlite3,string,urllib2,json,datetime,platform,osgeo
from os.path import splitext,basename,dirname,expanduser
from random import randint
from collections import OrderedDict
import copy
import getpass
import traceback

import xml.etree.ElementTree as xml

import numpy as np

os.environ['UBUNTU_MENUPROXY']='0'

#PATH=os.path.realpath(os.path.dirname(sys.argv[0]))+'/'
PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
HOME=os.getenv('HOME')

WDG=False
WDP=True
DEBUG = '-debug' in sys.argv or '--debug' in sys.argv
LOCCLOUD = '-local' in sys.argv or '--local' in sys.argv

if DEBUG:
	print 'Launching ZephyTOOLS'
	WDG=True
	WDP=True
if LOCCLOUD:
	print '  cloud emulation mode is activated'
	os.environ['ZEPHYCLOUD_API_VERSION']='1'
	os.environ['ZEPHYCLOUD_SERVER']='zephycloud.'+getpass.getuser()+'.local'
	os.environ['ZEPHYCLOUD_CA_ROOT']=os.path.abspath(PATH+'../../../ZephyCLOUD/tmp/certs/root_ca.pem')
if DEBUG:
	if LOCCLOUD:
		if os.path.isdir(PATH+'../../PROJECTS_CFD_cloud'):
			subprocess.call(['mv','-f',PATH+'../../PROJECTS_CFD',PATH+'../../PROJECTS_CFD_web'])
			subprocess.call(['mv','-f',PATH+'../../PROJECTS_CFD_cloud',PATH+'../../PROJECTS_CFD'])
			print '  Set projects from folder cloud'
	else:
		if os.path.isdir(PATH+'../../PROJECTS_CFD_web'):
			subprocess.call(['mv','-f',PATH+'../../PROJECTS_CFD',PATH+'../../PROJECTS_CFD_cloud'])
			subprocess.call(['mv','-f',PATH+'../../PROJECTS_CFD_web',PATH+'../../PROJECTS_CFD'])
			print '  Set projects from folder web'

APIs=OrderedDict()
APIs['Europe']='api.zephycloud.aziugo.com'
APIs['China']='apicn.zephycloud.aziugo.com'
APIs['Dev']='apidev.zephy-science.com'
APIs['Offline - local account']='None'#must be last

USER_STATUS=['bronze','silver','gold','root']


class WSL(object):
	""" Detect and cache WSL environment"""
	_is_detected = None

	@staticmethod
	def detected():
		"""
		:return:	Return true if we are in a WSL environment
		:rtype:		bool
		"""
		if WSL._is_detected is None:
			if platform.system().lower() != "linux":
				WSL._is_detected = False
			else:
				with open("/proc/version", "r") as fh:
					WSL._is_detected = "microsoft" in fh.read().lower()
		return WSL._is_detected


MEMMAX=psutil.virtual_memory()[0]/1024.
if WSL.detected():
	SWAPMAX = 0
	output = subprocess.check_output(["free", "-b"])
	for line in output.splitlines(False):
		if line.lower().startswith("swap"):
			SWAPMAX = float(line.split()[1])/1024.
else:
	SWAPMAX=psutil.swap_memory()[0]/1024.

nhighres=4

machine2proc=[8,16,36,64,128]

OSGEO3=int(osgeo.__version__.split('.')[0])>=3


latex_fonts=[]
latex_fonts.append('tiny')
latex_fonts.append('scriptsize')
latex_fonts.append('footnotesize')
latex_fonts.append('small')
latex_fonts.append('normalsize')
latex_fonts.append('large')
latex_fonts.append('Large')
latex_fonts.append('LARGE')
latex_fonts.append('huge')
latex_fonts.append('Huge')

styles=[':', '--', '-',':', '--', '-',':', '--', '-']
markers=[(5,1),(5,2),(5,3),(5,0)]

xmlfilecontrol=PATH+'../../APPLI/QUEUE/control.xml'
xmlfilecloud=PATH+'../../APPLI/QUEUE/cloud.xml'
xmlfileproc=PATH+'../../APPLI/QUEUE/processes.xml'		
xmlfilequeue=PATH+'../../APPLI/QUEUE/queue.xml'
xmlfileold=PATH+'../../APPLI/QUEUE/old.xml'
xmlfileended=PATH+'../../APPLI/QUEUE/ended.xml'
xmlfilecfdprojects=PATH+'../../PROJECTS_CFD/projects_cfd.xml'
xmlfilewdgprojects=PATH+'../../PROJECTS_WDG/projects_wdg.xml'
xmlfilewdpprojects=PATH+'../../PROJECTS_WDP/projects_wdp.xml'

AXES_BBOX			=[0.12,0.08,0.87,0.91]
AXES_CLIMATO		=[0.10,0.08,0.80,0.84]
AXES_CLIMATO_LEG	=[-0.1,-0.1,1.20,1.20]
AXES_GENERATOR		=[0.08,0.08,0.8,0.8]
AXES_CVG			=[0.1,0.10,0.80,0.85]
AXES_CONTROL		=[0.12,0.10,0.75,0.85]
AXES_DIAG			=[0.10,0.03,0.87,0.87]
AXES_DIAG_11		=[0.10,0.03,0.87,0.45]
AXES_DIAG_12		=[0.10,0.53,0.87,0.92]
AXES_HIST_2D		=[0.10,0.14,0.80,0.80]
AXES_HIST_3D		=[0.00,0.00,1.00,1.00]
AXES_EXTRA_RES		=[0.11,0.12,0.84,0.84]
AXES_ISOH			=[0.14,0.10,0.83,0.85]
AXES_ISOH_LEG1		=[0.14,0.95,0.83,0.05]
AXES_ISOH_LEG2		=[0.14,0.45,0.83,0.05]
AXES_ROSE_ROSE		=[0.08,0.16,0.82,0.80]
AXES_ROSE_CHART		=[0.08,0.15,0.88,0.80]

zix_elemax=[400.,850.,1300.,1.e+8]
zix_elestd=[75.,175.,275.,1.e+8]
zix_slomoy=[2.,5.,10.,1.e+8]
zix_slomax=[15.,21.,27.,1.e+8]

CVGRES_NTMIN=5
CVGRES_NTMAX=10

LIST_NSECT=[8,12,16,18,24,36,48,72,90,120,144,180,240,360]

NCPU=multiprocessing.cpu_count()

try:
	with open(os.path.join(PATH, '../../COMMON/version'),'r') as f: lines=f.readlines()
	VERSION=lines[0].rstrip()
except:
	try:
		with open(os.path.join(PATH, '../../../ZephyTOOLS/ZephyTOOLS/UPDATE/version'),'r') as f: lines=f.readlines()
		VERSION=lines[0].rstrip()
	except: VERSION='XX.YY'

try:	OFPATH=open(os.path.join(PATH, '../../COMMON/foam/path'),'r').readline()[:-1]
except: OFPATH=os.path.join(HOME, 'OpenFOAM')

OFPATH=OFPATH.strip().replace('~',HOME)

ofsource='source '+os.path.join(OFPATH, 'openfoam8/etc/bashrc')
xterm	=['xterm','-T','ZephyTOOLS CFD calculations are running in this window. Please DO NOT CLOSE IT.','-fg','light blue','-bg','dark blue','-geometry','120x10','-e',ofsource+';']
xterm2	=['xterm','-T','ZephyTOOLS','-fg','dark blue','-bg','light blue','-geometry','120x10','-e',ofsource+';']

VTKTURB=[]
VTKTURB.append([79.4,{}])
VTKTURB[-1][1]['rotor']=PATH+'/../../COMMON/modeles/WTF_080.vtk'
VTKTURB[-1][1]['tower']=PATH+'/../../COMMON/modeles/WTB_080.vtk'
VTKTURB.append([99.2,{}])
VTKTURB[-1][1]['rotor']=PATH+'/../../COMMON/modeles/WTF_100.vtk'
VTKTURB[-1][1]['tower']=PATH+'/../../COMMON/modeles/WTB_100.vtk'

USER_STATUS=['bronze','silver','gold','root']

THEMES=['ZephyTOOLS','ZephyScience','ZephyPole']

lim_heavy,lim_medium=200000,40000

bracks='    {\n'
bracke='    }\n'

class LANGUAGES: 
	def __init__(self):
		
		self.languages=[]
		self.codes=[]
		self.locales=[]
		
		try:
			infile=open(PATH+'../../COMMON/lang','r')
			lines=infile.readlines()
			infile.close()
			for line in lines:
				values=line[:-1].split('|')
				self.languages.append(values[0])
				self.codes.append(values[1])
				self.locales.append(values[2])
		except:
			if DEBUG: print 'error setting languages'
			self.languages=['English']
			self.codes=['EN']
			self.locales=['en']
LANGUAGES=LANGUAGES()

ddHelp={
				'dialog_MAIN':							'index.html',
				'dialog_MAIN_CFD':						['7_ZephyCFD/load.html',\
														'7_ZephyCFD/analysis.html',\
														'7_ZephyCFD/mesh.html',\
														'7_ZephyCFD/calc.html',\
														'7_ZephyCFD/rose.html',\
														'7_ZephyCFD/extra.html',\
														'7_ZephyCFD/assess.html'],
				'dialog_MAIN_WDP':						'6_ZephyWDP/zephywdp.html',
				'dialog_MAIN_WDG':						'6_ZephyWDP/zephywdg.html',
				'dialog_PARAM_CFD_LOAD':				'7_ZephyCFD/load.html#process-parameters',
				'dialog_PARAM_CFD_ANALYSE':				'7_ZephyCFD/analysis.html#process-parameters',
				'dialog_PARAM_CFD_MESH_01':				'7_ZephyCFD/mesh.html#process-parameters',
				'dialog_PARAM_CFD_CALC_01':				'7_ZephyCFD/calc.html#process-parameters',
				'dialog_PARAM_CFD_LAYOUT':				'7_ZephyCFD/assess.html#process-options',
				'dialog_PARAM_CFD_ENVIRON':				'7_ZephyCFD/assess.html#process-options',
				'dialog_LIST_FILES':					'4_Input_Files/files.html',	
				'dialog_LIST_PARAMETERS':				'2_Global/global.html#pre-processing',
				'dialog_LIST_DATABASE':					'3_Databases/databases.html',
				'dialog_LIST_CFD':						'7_ZephyCFD/zephycfd.html',
				'dialog_LIST_WDG':						'5_ZephyWDG/zephywdg.html',
				'dialog_LIST_WDP':						'6_ZephyWDP/zephywdp.html',
				'dialog_FILES_ORO':						'4_Input_Files/files.html#orography',
				'dialog_FILES_ROU':						'4_Input_Files/files.html#roughness',
				'dialog_FILES_MULTI':					'4_Input_Files/files.html#multi-data',
				'dialog_FILES_MAST':					'4_Input_Files/files.html#masts',
				'dialog_FILES_LIDAR':					'4_Input_Files/files.html#lidars',
				'dialog_FILES_WT':						'4_Input_Files/files.html#wind-turbines',
				'dialog_FILES_MAPPING':					'4_Input_Files/files.html#mappings',
				'dialog_FILES_POINT':					'4_Input_Files/files.html#result-points',
				'dialog_FILES_MESO':					'4_Input_Files/files.html#mesoscale-points',
				'dialog_FILES_PICTURE':					'4_Input_Files/files.html#picture',
				'dialog_OPTIONS_MACHINE':				'2_Global/global.html#software-configuration',
				'dialog_OPTIONS_GEOREF':				'2_Global/global.html#georeference-options',
				'dialog_OPTIONS_NEW_USER':				'2_Global/global.html#user-registration',
				'dialog_OPTIONS_PATH':					'2_Global/global.html#user-preferences',
				'dialog_OPTIONS_REPORT':				'2_Global/report.html#reports-options',
				'dialog_OPTIONS_USER':					'2_Global/global.html#general-options',
				'dialog_OPTIONS_VISU':					'2_Global/visu.html',
				'dialog_PROJECT_CFD':					'7_ZephyCFD/zephycfd.html',
				'dialog_PROJECT_WDG':					'5_ZephyWDG/zephywdg.html',
				'dialog_PROJECT_WDP':					'6_ZephyWDP/zephywdp.html',
				'dialog_VISU_CLIMATO':					'2_Global/visu.html#wind-roses',
				'dialog_VISU_GENERATOR':				'2_Global/visu.html',
				'dialog_VISU_FILES':					'2_Global/visu.html#maps',
				'dialog_VISU_CFD_ANAL_DIAG':			'7_ZephyCFD/analysis.html#visualizations',
				'dialog_VISU_CFD_ANAL_ISOH':			'7_ZephyCFD/analysis.html#visualizations',
				'dialog_VISU_CFD_ASSESS_DIAG':			'7_ZephyCFD/assess.html#visualizations',
				'dialog_VISU_CFD_CALC_CVG':				'7_ZephyCFD/calc.html#convergence-monitoring',
				'dialog_VISU_CFD_CALC_ISOH':			'7_ZephyCFD/calc.html#visualizations',
				'dialog_VISU_CFD_CALC_RES':				'7_ZephyCFD/calc.html#visualizations',
				'dialog_VISU_CFD_EXTRA_CLIMATO':		'7_ZephyCFD/extra.html#visualizations',
				'dialog_VISU_CFD_EXTRA_ISOH':			'7_ZephyCFD/extra.html#visualizations',
				'dialog_VISU_CFD_EXTRA_RES':			'7_ZephyCFD/extra.html#visualizations',
				'dialog_VISU_CFD_LOAD':					'7_ZephyCFD/load.html#visualizations',
				'dialog_VISU_CFD_MESH_3D':				'7_ZephyCFD/mesh.html#visualizations',
				'dialog_VISU_CFD_MESH_GROUND':			'7_ZephyCFD/mesh.html#visualizations',
				'dialog_VISU_CFD_ROSE_ROSE':			'7_ZephyCFD/rose.html#visualizations',
				'dialog_CFD_CALC_CONTROL':				'7_ZephyCFD/calc.html#convergence-monitoring',
				'dialog_CFD_CALC_DIRECTIONS':			'7_ZephyCFD/calc.html#direction-s',
				'dialog_ZT_QUEUE_CONTROL':				'2_Global/global.html#queuing-management',
				'dialog_SPECIAL_REPORT':				'2_Global/report.html',
				'dialog_VISUPOP_ANNOTATIONS':			'2_Global/visu.html#annotations',
				'dialog_VISUPOP_CONTOURS':				'7_ZephyCFD/analysis.html#visualizations',
				'dialog_VISUPOP_LABELS':				'2_Global/visu.html',
				'dialog_VISUPOP_SERIES':				'2_Global/visu.html#user-series',
				'dialog_CHOOSE_FILE':					'4_Input_Files/files.html',
				}

ddParam=OrderedDict()

ddParam['load']=OrderedDict()
ddParam['load']['filename']='ZS'
ddParam['load']['version']=VERSION
ddParam['load']['comments']='Default set of parameters for LOAD action.'
ddParam['load']['resvisu_crit']='1'
ddParam['load']['resclose_oro_crit']='4'
ddParam['load']['reslarge_oro_crit']='4'
ddParam['load']['resclose_rou_crit']='4'
ddParam['load']['reslarge_rou_crit']='4'
ddParam['load']['resvisu']='-1'
ddParam['load']['resclose_oro']='-1'
ddParam['load']['reslarge_oro']='-1'
ddParam['load']['resclose_rou']='-1'
ddParam['load']['reslarge_rou']='-1'
ddParam['load']['nvisu']='1'
ddParam['load']['hvisu1']='80.0'
ddParam['load']['hvisu2']='90.0'
ddParam['load']['hvisu3']='100.0'
ddParam['load']['hvisu4']='110.0'
ddParam['load']['hvisu5']='120.0'

ddParam['anal']=OrderedDict()
ddParam['anal']['filename']='ZS'
ddParam['anal']['version']=VERSION
ddParam['anal']['comments']='Default set of parameters for CFD ANALYSE action.'
ddParam['anal']['rixrad']='1500.0'
ddParam['anal']['rixres']='25.0'
ddParam['anal']['rixslope']='3.0'
ddParam['anal']['rixncalc']='4'
ddParam['anal']['rixnsect']='1'
ddParam['anal']['rixrad_site']='100.0'
ddParam['anal']['rixres_site']='100.0'
ddParam['anal']['rixncalc_site']='0'
ddParam['anal']['autocontour']='8.0'
ddParam['anal']['contourlimit']='5000.0'
ddParam['anal']['rixcalc']='True'

ddParam['anal.NoRIX']=copy.deepcopy(ddParam['anal'])
ddParam['anal.NoRIX']['filename']='ZS-NoRIX'
ddParam['anal.NoRIX']['comments']='Default set of parameters for CFD ANALYSE action with RIX analysis disactivated.'
ddParam['anal.NoRIX']['rixcalc']='False'

ddParam['mesh01']=OrderedDict()
ddParam['mesh01']['filename']='ZS'
ddParam['mesh01']['version']=VERSION
ddParam['mesh01']['mesher']='mesh01'
ddParam['mesh01']['comments']='User defined set of parameters.'
ddParam['mesh01']['diaref']='-1'
ddParam['mesh01']['diadom']='-1'
ddParam['mesh01']['resfine']='50.0'
ddParam['mesh01']['rescoarse']='-1'
ddParam['mesh01']['nsect']='7'
ddParam['mesh01']['htop']='-1'
ddParam['mesh01']['hturb']='220.0'
ddParam['mesh01']['hcanop']='30.'
ddParam['mesh01']['dztop']='500.0'
ddParam['mesh01']['dzturb']='5.0'
ddParam['mesh01']['dzcanop']='2.0'
ddParam['mesh01']['dzmin']='1.0'
ddParam['mesh01']['exptop']='1.20'
ddParam['mesh01']['expturb']='1.10'
ddParam['mesh01']['expcanop']='1.10'
ddParam['mesh01']['nsmoo']='1'
ddParam['mesh01']['smoocoef']='0.50'
ddParam['mesh01']['insmoo']='2'
ddParam['mesh01']['meshlim']='1.0'
ddParam['mesh01']['meshcrit']='0'
ddParam['mesh01']['resratio']='4'
ddParam['mesh01']['resdist']='250.0'
ddParam['mesh01']['multizone']='1'
ddParam['mesh01']['autocontour']='0'
ddParam['mesh01']['rou_disp']='0'
ddParam['mesh01']['rou_ratio']='30.'
ddParam['mesh01']['relax_distratio']='0.75'
ddParam['mesh01']['relax_resfactor']='8.'

ddParam['mesh01.Fine']=copy.deepcopy(ddParam['mesh01'])
ddParam['mesh01.Fine']['filename']='ZS-Fine'
ddParam['mesh01.Fine']['comments']='Default set of parameters for mesh generation (rotors not taken into account, accurate refinement).'
ddParam['mesh01.Fine']['resfine']='25.0'
ddParam['mesh01.Fine']['nsect']='11'

ddParam['mesh01.Coarse']=copy.deepcopy(ddParam['mesh01'])
ddParam['mesh01.Coarse']['filename']='ZS-Coarse'
ddParam['mesh01.Coarse']['comments']='Default set of parameters for mesh generation (rotors not taken into account, coarse refinement).'
ddParam['mesh01.Coarse']['resfine']='50.0'
ddParam['mesh01.Coarse']['nsect']='7'

ddParam['calc01']=OrderedDict()
ddParam['calc01']['filename']='ZS-Robust'
ddParam['calc01']['version']=VERSION
ddParam['calc01']['calculator']='calc01'
ddParam['calc01']['comments']='This is the default CFD calculation configuration. It uses k-epsilon turbulence model with modified constants.'
ddParam['calc01']['vref']='30.0'
ddParam['calc01']['href']='500.0'
ddParam['calc01']['vbc']='0'
ddParam['calc01']['kbc']='0'
ddParam['calc01']['rbc']='2'
ddParam['calc01']['kval']='0.00000001'
ddParam['calc01']['rval']='0.0100'
ddParam['calc01']['turb']='0'
ddParam['calc01']['cmu_keps']='0.03240000'
ddParam['calc01']['c1_keps']='1.44000000'
ddParam['calc01']['c2_keps']='1.92000000'
ddParam['calc01']['sigmaeps_keps']='1.85000000'
ddParam['calc01']['cmu_krea']='0.09000000'
ddParam['calc01']['a0_krea']='4.00000000'
ddParam['calc01']['c2_krea']='1.90000000'
ddParam['calc01']['sigmak_krea']='1.00000000'
ddParam['calc01']['sigmaeps_krea']='1.20000000'
ddParam['calc01']['cmu_krng']='0.08450000'
ddParam['calc01']['c1_krng']='1.42000000'
ddParam['calc01']['c2_krng']='1.68000000'
ddParam['calc01']['sigmak_krng']='0.71942000'
ddParam['calc01']['sigmaeps_krng']='0.71942000'
ddParam['calc01']['eta0_krng']='4.38000000'
ddParam['calc01']['beta_krng']='0.01200000'
ddParam['calc01']['nu']='1.40600e-05'
ddParam['calc01']['grad']='2'
ddParam['calc01']['lap']='4'
ddParam['calc01']['divu']='0'
ddParam['calc01']['divk']='0'
ddParam['calc01']['diveps']='0'
ddParam['calc01']['grad_init']='2'
ddParam['calc01']['lap_init']='4'
ddParam['calc01']['divu_init']='0'
ddParam['calc01']['divk_init']='0'
ddParam['calc01']['diveps_init']='0'
ddParam['calc01']['simplec']='True'
ddParam['calc01']['survey']='True'
ddParam['calc01']['n_it_max']='2000'
ddParam['calc01']['correctors']='0'
ddParam['calc01']['cvg_p']='5.00e-05'
ddParam['calc01']['cvg_u']='1.00e-06'
ddParam['calc01']['cvg_k']='1.00e-06'
ddParam['calc01']['cvg_eps']='1.00e-06'
ddParam['calc01']['relax_p']='1.00'
ddParam['calc01']['relax_u']='0.90'
ddParam['calc01']['relax_k']='0.90'
ddParam['calc01']['relax_eps']='0.90'
ddParam['calc01']['init_vel']='1'
ddParam['calc01']['init_k']='-1'
ddParam['calc01']['init_eps']='-1'
ddParam['calc01']['simplec_init']='True'
ddParam['calc01']['survey_init']='True'
ddParam['calc01']['n_it_max_init']='1500'
ddParam['calc01']['correctors_init']='0'
ddParam['calc01']['cvg_p_init']='5.00e-05'
ddParam['calc01']['cvg_u_init']='1.00e-06'
ddParam['calc01']['cvg_k_init']='1.00e-06'
ddParam['calc01']['cvg_eps_init']='1.00e-06'
ddParam['calc01']['relax_p_init']='1.00'
ddParam['calc01']['relax_u_init']='0.90'
ddParam['calc01']['relax_k_init']='0.90'
ddParam['calc01']['relax_eps_init']='0.90'
ddParam['calc01']['psol_init']='0'
ddParam['calc01']['ssol_init']='0'
ddParam['calc01']['ppred_init']='0'
ddParam['calc01']['spred_init']='0'
ddParam['calc01']['psmoo_init']='0'
ddParam['calc01']['ssmoo_init']='0'
ddParam['calc01']['psol']='0'
ddParam['calc01']['ssol']='0'
ddParam['calc01']['ppred']='0'
ddParam['calc01']['spred']='0'
ddParam['calc01']['psmoo']='0'
ddParam['calc01']['ssmoo']='0'
ddParam['calc01']['tol_p_init']='1.e-06'
ddParam['calc01']['tol_s_init']='1.e-06'
ddParam['calc01']['rtol_p_init']='1.e-02'
ddParam['calc01']['rtol_s_init']='1.e-02'
ddParam['calc01']['tol_p']='1.e-06'
ddParam['calc01']['tol_s']='1.e-06'
ddParam['calc01']['rtol_p']='1.e-02'
ddParam['calc01']['rtol_s']='1.e-02'
ddParam['calc01']['npre']='0'
ddParam['calc01']['npre_init']='0'
ddParam['calc01']['npost']='0'
ddParam['calc01']['npost_init']='0'
ddParam['calc01']['nfin']='1'
ddParam['calc01']['nfin_init']='1'
ddParam['calc01']['nsweep']='1'
ddParam['calc01']['nsweep_init']='1'
ddParam['calc01']['ncellmin']='50'
ddParam['calc01']['ncellmin_init']='50'
ddParam['calc01']['tgmes']='100.'
ddParam['calc01']['tgmach']='100.'
ddParam['calc01']['cvg_alpha']='1.e-5'
ddParam['calc01']['vkill']='150.'
ddParam['calc01']['tgmes_init']='100.'
ddParam['calc01']['tgmach_init']='100.'
ddParam['calc01']['cvg_alpha_init']='1.e-5'
ddParam['calc01']['vkill_init']='150.'

ddParam['calc01.Fast']=copy.deepcopy(ddParam['calc01'])
ddParam['calc01.Fast']['filename']='ZS-Fast'
ddParam['calc01.Fast']['comments']='This is the modified CFD calculation configuration with faster calculation settings. It uses k-epsilon turbulence model with modified constants.'
ddParam['calc01.Fast']['relax_u_init']='0.95'
ddParam['calc01.Fast']['relax_k_init']='0.95'
ddParam['calc01.Fast']['relax_eps_init']='0.95'
ddParam['calc01.Fast']['relax_u']='0.95'
ddParam['calc01.Fast']['relax_k']='0.95'
ddParam['calc01.Fast']['relax_eps']='0.95'

ddParam['calc01.Solid']=copy.deepcopy(ddParam['calc01'])
ddParam['calc01.Solid']['filename']='ZS-Solid'
ddParam['calc01.Solid']['comments']='This is the modified CFD calculation configuration with solid calculation settings. It uses k-epsilon turbulence model with modified constants.'
ddParam['calc01.Solid']['relax_u_init']='0.90'
ddParam['calc01.Solid']['relax_k_init']='0.90'
ddParam['calc01.Solid']['relax_eps_init']='0.90'
ddParam['calc01.Solid']['relax_u']='0.80'
ddParam['calc01.Solid']['relax_k']='0.80'
ddParam['calc01.Solid']['relax_eps']='0.80'
ddParam['calc01.Solid']['correctors']='1'

ddParam['calc01.Simple']=copy.deepcopy(ddParam['calc01'])
ddParam['calc01.Simple']['filename']='ZS-Simple'
ddParam['calc01.Simple']['comments']='This is the default set from previous version, using standard SIMPLE.'
ddParam['calc01.Simple']['simplec_init']='False'
ddParam['calc01.Simple']['n_it_max_init']='2000'
ddParam['calc01.Simple']['relax_p_init']='0.30'
ddParam['calc01.Simple']['relax_u_init']='0.70'
ddParam['calc01.Simple']['relax_k_init']='0.50'
ddParam['calc01.Simple']['relax_eps_init']='0.50'
ddParam['calc01.Simple']['simplec']='False'
ddParam['calc01.Simple']['n_it_max']='3000'
ddParam['calc01.Simple']['relax_p']='0.30'
ddParam['calc01.Simple']['relax_u']='0.70'
ddParam['calc01.Simple']['relax_k']='0.50'
ddParam['calc01.Simple']['relax_eps']='0.50'

ddParam['mcp_xgb']=OrderedDict()
ddParam['mcp_xgb']['filename']='ZS-WindSpeed'
ddParam['mcp_xgb']['comments']='Default set of parameters for MCP action, dedicated to Wind Speed.'
ddParam['mcp_xgb']['targdata']='True'
ddParam['mcp_xgb']['valid']='1'
ddParam['mcp_xgb']['kfold_nsplit']='3'
ddParam['mcp_xgb']['kfold_nrepeat']='5'
ddParam['mcp_xgb']['alter_nhour']='5'
ddParam['mcp_xgb']['opti']='0'
ddParam['mcp_xgb']['n_iter']='20'
ddParam['mcp_xgb']['n_split']='3'
ddParam['mcp_xgb']['max_depth']='10'
ddParam['mcp_xgb']['max_depth_min']='9'
ddParam['mcp_xgb']['max_depth_max']='12'
ddParam['mcp_xgb']['eta']='0.2'
ddParam['mcp_xgb']['eta_min']='0.05'
ddParam['mcp_xgb']['eta_max']='0.35'
ddParam['mcp_xgb']['n_estimators']='180'
ddParam['mcp_xgb']['n_estimators_min']='130'
ddParam['mcp_xgb']['n_estimators_max']='230'
ddParam['mcp_xgb']['gamma']='15'
ddParam['mcp_xgb']['gamma_min']='0'
ddParam['mcp_xgb']['gamma_max']='30'
ddParam['mcp_xgb']['min_child_weight']='50'
ddParam['mcp_xgb']['min_child_weight_min']='1'
ddParam['mcp_xgb']['min_child_weight_max']='100'
ddParam['mcp_xgb']['subsample']='0.75'
ddParam['mcp_xgb']['subsample_min']='0.5'
ddParam['mcp_xgb']['subsample_max']='1'
ddParam['mcp_xgb']['colsample_bytree']='0.75'
ddParam['mcp_xgb']['colsample_bytree_min']='0.5'
ddParam['mcp_xgb']['colsample_bytree_max']='1'
ddParam['mcp_xgb']['lambda']='15'
ddParam['mcp_xgb']['lambda_min']='0'
ddParam['mcp_xgb']['lambda_max']='30'

ddParam['mcp_xgb.T']=copy.deepcopy(ddParam['mcp_xgb'])
ddParam['mcp_xgb.T']['filename']='ZS-Temperature'
ddParam['mcp_xgb.T']['comments']='Modified set of parameters for MCP action, dedicated to Temperature.'
ddParam['mcp_xgb.T']['kfold_nsplit']='2'
ddParam['mcp_xgb.T']['n_iter']='5'
ddParam['mcp_xgb.T']['n_split']='2'
ddParam['mcp_xgb.T']['max_depth']='3'
ddParam['mcp_xgb.T']['max_depth_min']='3'
ddParam['mcp_xgb.T']['max_depth_max']='4'
ddParam['mcp_xgb.T']['n_estimators']='125'
ddParam['mcp_xgb.T']['n_estimators_min']='100'
ddParam['mcp_xgb.T']['n_estimators_max']='150'
ddParam['mcp_xgb.T']['gamma']='50'
ddParam['mcp_xgb.T']['gamma_min']='0'
ddParam['mcp_xgb.T']['gamma_max']='100'
ddParam['mcp_xgb.T']['min_child_weight']='75'
ddParam['mcp_xgb.T']['min_child_weight_min']='50'
ddParam['mcp_xgb.T']['min_child_weight_max']='100'
ddParam['mcp_xgb.T']['colsample_bytree']='0.8'
ddParam['mcp_xgb.T']['colsample_bytree_min']='0.6'
ddParam['mcp_xgb.T']['colsample_bytree_max']='1'
ddParam['mcp_xgb.T']['lambda']='50'
ddParam['mcp_xgb.T']['lambda_min']='0'
ddParam['mcp_xgb.T']['lambda_max']='100'

CVGo1,CVGc1='    {\n','    }\n'
CVGlll=[]
CVGlll.append('CvgResiduals')
CVGlll.append('Time')
CVGlll.append('clockTime')
CVGlll.append('executionTime')
CVGlll.append('contCumulative')
CVGlll.append('contGlobal')
CVGlll.append('contLocal')
CVGlll.append('pIters')
CVGlll.append('pFinalRes')
CVGlll.append('UxFinalRes')
CVGlll.append('UxIters')
CVGlll.append('UyFinalRes')
CVGlll.append('UyIters')
CVGlll.append('UzFinalRes')
CVGlll.append('UzIters')
CVGlll.append('kFinalRes')
CVGlll.append('kIters')
CVGlll.append('epsilonFinalRes')
CVGlll.append('epsilonIters')

CVGddd={}
CVGddd['CvgResiduals']=[0.,105.,'%',False,False]
CVGddd['Time']=[-1.,-1.,'-',False,False]
CVGddd['clockTime']=[-1.,-1.,'s',False,False]
CVGddd['contCumulative']=[-1.,-1.,'-',True,False]
CVGddd['contGlobal']=[-1.,-1.,'-',True,False]
CVGddd['contLocal']=[-1.,-1.,'-',True,True]
CVGddd['epsilonFinalRes']=[-1,-1.,'-',True,True]
CVGddd['epsilonIters']=[-1,-1.,'-',False,False]
CVGddd['executionTime']=[-1,-1.,'-',False,False]
CVGddd['kFinalRes']=[-1,-1.,'-',True,True]
CVGddd['kIters']=[-1,-1.,'-',False,False]
CVGddd['pFinalRes']=[-1,-1.,'-',True,True]
CVGddd['pIters']=[-1,-1.,'-',False,False]
CVGddd['UxFinalRes']=[-1,-1.,'-',True,True]
CVGddd['UxIters']=[-1,-1.,'-',False,False]
CVGddd['UyFinalRes']=[-1,-1.,'-',True,True]
CVGddd['UyIters']=[-1,-1.,'-',False,False]
CVGddd['UzFinalRes']=[-1,-1.,'-',True,True]
CVGddd['UzIters']=[-1,-1.,'-',False,False]

def SetEnviron():
	
	OFVERSPATH=os.path.join(OFPATH, "openfoam8")
	OF_ThirdParty=os.path.join(OFPATH, "ThirdParty-5.0")
	OF_SITE=os.path.join(OFPATH, "site", "5.0")
	OF_PARAVIEW=os.path.join(OFPATH, "paraviewopenfoam56")
	OF_USER_PATH=os.path.join(os.getenv('HOME'), 'OpenFOAM', os.getenv('USER')+"-5.0")

	os.environ['FOAM_APPBIN']=os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'bin')
	os.environ['FOAM_APP']=os.path.join(OFVERSPATH, 'applications')
	os.environ['FOAM_ETC']=os.path.join(OFVERSPATH, 'etc')
	os.environ['FOAM_EXT_LIBBIN']=os.path.join(OF_ThirdParty, 'platforms', 'linux64GccDPInt32', 'lib')
	os.environ['FOAM_INST_DIR']=OFPATH.rstrip('/')
	os.environ['FOAM_JOB_DIR']=os.path.join(OFPATH, 'jobControl')
	os.environ['FOAM_LIBBIN']=os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'lib')
	os.environ['FOAM_MPI']='openmpi-system'
	os.environ['FOAM_RUN']=os.path.join(OF_USER_PATH, 'run')
	os.environ['FOAM_SETTINGS']=''
	os.environ['FOAM_SIGFPE']=''
	os.environ['FOAM_SITE_APPBIN']=os.path.join(OF_SITE, 'platforms', 'linux64GccDPInt32Opt', 'bin')
	os.environ['FOAM_SITE_LIBBIN']=os.path.join(OF_SITE, 'platforms', 'linux64GccDPInt32Opt', 'lib')
	os.environ['FOAM_SOLVERS']=os.path.join(OFVERSPATH, 'applications', 'solvers')
	os.environ['FOAM_SRC']=os.path.join(OFVERSPATH, 'src')
	os.environ['FOAM_TUTORIALS']=os.path.join(OFVERSPATH, 'tutorials')
	os.environ['FOAM_USER_APPBIN']=os.path.join(OF_USER_PATH, 'platforms', 'linux64GccDPInt32Opt', 'bin')
	os.environ['FOAM_USER_LIBBIN']=os.path.join(OF_USER_PATH, 'platforms', 'linux64GccDPInt32Opt', 'lib')
	os.environ['FOAM_UTILITIES']=os.path.join(OFVERSPATH, 'applications', 'utilities')

	if 'LD_LIBRARY_PATH' in os.environ:
		old_ld_path=os.pathsep+os.environ['LD_LIBRARY_PATH']
	else:
		old_ld_path=""
	os.environ['LD_LIBRARY_PATH']=os.path.join(OF_ThirdParty, 'platforms', 'linux64Gcc', 'gperftools-svn', 'lib')+os.pathsep+ \
		os.path.join(OF_PARAVIEW, 'lib', 'paraview-5.6') + os.pathsep + \
		os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'lib', 'openmpi-system') + os.pathsep + \
		os.path.join(OF_ThirdParty, 'platforms', 'linux64GccDPInt32', 'lib', 'openmpi-system') + os.pathsep + \
		"/usr/lib/openmpi/lib" + os.pathsep + \
		os.path.join(OF_USER_PATH, 'platforms', 'linux64GccDPInt32Opt', 'lib') + os.pathsep + \
		os.path.join(OF_SITE, 'platforms', 'linux64GccDPInt32Opt', 'lib') + os.pathsep + \
		os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'lib') + os.pathsep + \
		os.path.join(OF_ThirdParty, 'platforms', 'linux64GccDPInt32', 'lib') + os.pathsep + \
		os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'lib', 'dummy') + \
		old_ld_path

	os.environ['MPI_ARCH_PATH']='/usr/lib/openmpi'
	os.environ['MPI_BUFFER_SIZE']='20000000'
	os.environ['ParaView_DIR']=OF_PARAVIEW.rstrip('/')
	os.environ['ParaView_INCLUDE_DIR']=os.path.join('OF_PARAVIEW', 'include', 'paraview-5.6')
	os.environ['ParaView_MAJOR']='5.6'
	os.environ['ParaView_VERSION']='5.6.0'

	if 'LD_LIBRARY_PATH' in os.environ:
		old_path=os.pathsep+os.environ['PATH']
	else:
		old_path=""
	os.environ['PATH']=os.path.join(OF_ThirdParty, 'platforms', 'linux64Gcc', 'gperftools-svn', 'bin')+os.pathsep+ \
		os.path.join(OF_PARAVIEW, 'bin') + os.pathsep + \
		os.path.join(OF_USER_PATH, 'platforms', 'linux64GccDPInt32Opt', 'bin') + os.pathsep + \
		os.path.join(OF_SITE, 'platforms', 'linux64GccDPInt32Opt', 'bin') + os.pathsep + \
		os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'bin') + os.pathsep + \
		os.path.join(OFVERSPATH, 'bin') + os.pathsep + \
		os.path.join(OFVERSPATH, 'wmake') + os.pathsep + \
		old_path

	os.environ['PV_PLUGIN_PATH']=os.path.join(OFVERSPATH, 'platforms', 'linux64GccDPInt32Opt', 'lib', 'paraview-5.6')
	os.environ['WM_ARCH']='linux64'
	os.environ['WM_ARCH_OPTION']='64'
	os.environ['WM_CC']='gcc'
	os.environ['WM_CFLAGS']='-m64 -fPIC'
	os.environ['WM_COMPILE_OPTION']='Opt'
	os.environ['WM_COMPILER']='Gcc'
	os.environ['WM_COMPILER_LIB_ARCH']='64'
	os.environ['WM_COMPILER_TYPE']='system'
	os.environ['WM_CXXFLAGS']='-m64 -fPIC -std=c++0x'
	os.environ['WM_CXX']='g++'
	os.environ['WM_DIR']=os.path.join(OFVERSPATH, 'wmake')
	os.environ['WM_LABEL_OPTION']='Int32'
	os.environ['WM_LABEL_SIZE']='32'
	os.environ['WM_LDFLAGS']='-m64'
	os.environ['WM_LINK_LANGUAGE']='c++'
	os.environ['WM_MPLIB']='SYSTEMOPENMPI'
	os.environ['WM_OPTIONS']='linux64GccDPInt32Opt'
	os.environ['WM_OSTYPE']='POSIX'
	os.environ['WM_PRECISION_OPTION']='DP'
	os.environ['WM_PROJECT_DIR']=OFVERSPATH.rstrip('/')
	os.environ['WM_PROJECT_INST_DIR']=OFPATH.rstrip('/')
	os.environ['WM_PROJECT']='OpenFOAM'
	os.environ['WM_PROJECT_USER_DIR']=OF_USER_PATH.rstrip('/')
	os.environ['WM_PROJECT_VERSION']='5.0'
	os.environ['WM_THIRD_PARTY_DIR']=OF_ThirdParty.rstrip('/')
	return True

