#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys,os
import xml.etree.ElementTree as xml
from math import sqrt,pi
import traceback
import numpy as NP

from ZS_COMMON import UpdateProgress

PATH=os.path.realpath(os.path.dirname(sys.argv[0]))+'/'

time2use=sys.argv[1]
ithread=sys.argv[2]
code=sys.argv[3]
folder=sys.argv[4]
message=sys.argv[5]
nsmoo=int(eval(sys.argv[6]))
smoocoef=eval(sys.argv[7])
insmoo=int(eval(sys.argv[8]))
diadom=eval(sys.argv[9])
diaref=eval(sys.argv[10])
istep=eval(sys.argv[11])
nstep=eval(sys.argv[12])

progressfile=PATH+'../../APPLI/TMP/logout_'+time2use+'.xml'

try:
	
	UpdateProgress(time2use,ithread,0.05,message+' - 1/4')
	
	xg,yg,zg=NP.loadtxt(folder+'/FILES/'+code+'_elevation',unpack=True)
	tri=NP.loadtxt(folder+'/FILES/'+code+'_elevation')
	
	n_ground_nodes=len(xg)

	tt=NP.loadtxt(folder+'/FILES/'+code+'_zsinfo',usecols=(2,3,4,5,6,7,8,9,10,11))
	
	UpdateProgress(time2use,ithread,1.0,' ')
	
	istep+=1
	
	try:
		rootprogress=xml.parse(progressfile).getroot()
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		xml.ElementTree(rootprogress).write(progressfile)
	except: pass
	
	UpdateProgress(time2use,ithread,0.05,message+' - 2/4')
	
	if smoocoef>1.e-2:
	
		pond=1.-smoocoef
		avancement=0.
		for ismooth in range(nsmoo):
			newz=[]
			i=-1
			for pt in tt:
				i+=1
				som,nsom=0.,0
				for ptt in pt:
					iptt=int(ptt)
					if iptt!=-1:
						som+=smoocoef*zg[iptt-1]
						nsom+=1
				newz.append(pond*zg[i]+som/nsom)
			zg=newz
	
	UpdateProgress(time2use,ithread,1.0,' ')
	
	istep+=1

	try:
		rootprogress=xml.parse(progressfile).getroot()
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		xml.ElementTree(rootprogress).write(progressfile)
	except: pass
	
	UpdateProgress(time2use,ithread,0.05,message+' - 3/4')
	
	limflat=diadom/2.-500.
	radflat=(diaref/2.+limflat)/2.
	zmoy,rescoarse=0.,0.
	newtri=NP.linalg.norm(tri,axis=1)
	
	if code!='reduced':

		filtri=NP.where(newtri>radflat)[0]
		for el in filtri: zmoy+=zg[el]
		zmoy/=len(filtri)
		rescoarse=(2*pi*diadom/2.)/len(NP.where(newtri>diadom/2.-1.)[0])

	else: insmoo=1
	
	UpdateProgress(time2use,ithread,0.55,message+' - 3/4')
	
	if insmoo==0:
		nsmoothinlet=10
		filtri1=NP.where(newtri>limflat)[0]
		filtri2=NP.where((newtri>radflat) & (newtri<=limflat))[0]
		for el in filtri1: zg[el]=zmoy
		for el in filtri2: zg[el]=zmoy*(newtri[el]-radflat)/(limflat-radflat)+zg[el]*(limflat-newtri[el])/(limflat-radflat)
	elif insmoo==1: nsmoothinlet=0
	else: nsmoothinlet=10
	
	UpdateProgress(time2use,ithread,1.0,' ')
	
	istep+=1

	try:
		rootprogress=xml.parse(progressfile).getroot()
		rootprogress.find('progress_text').text='%i'%(100.*istep/nstep)
		rootprogress.find('progress_frac').text=str(istep/nstep)
		xml.ElementTree(rootprogress).write(progressfile)
	except: pass

	UpdateProgress(time2use,ithread,0.05,message+' - 4/4')
	
	for ismooth in range(nsmoothinlet):

		newz=[]
		i=-1
		for pt in tt:
			i+=1
			som,nsom=0.,0
			x2use=xg[i]
			y2use=yg[i]
			d=sqrt(x2use**2+y2use**2)
			if d>limflat: newz.append(zg[i])
			elif d>radflat:
				for ptt in pt:
					iptt=int(ptt)
					if iptt!=-1:
						som+=smoocoef*zg[iptt-1]
						nsom+=1
				newz.append(pond*zg[i]+som/nsom)
			else: newz.append(zg[i])
		zg=newz
	
	with open(folder+'/FILES/'+code+'_elevation','w') as f: 
		for i in range(n_ground_nodes): f.write('%15.2f'%xg[i]+'\t'+'%15.2f'%yg[i]+'\t'+'%15.2f'%zg[i]+'\n')

	with open(folder+'/FILES/propagate_param_'+code,'w') as f:
		f.write('%.1f'%zmoy+'\n')
		f.write('%.1f'%rescoarse+'\n')
	
	UpdateProgress(time2use,ithread,1.0,' ')

except:
	print 'Error in CFD_MESH_01_PropaOro'
	print(traceback.format_exc())
