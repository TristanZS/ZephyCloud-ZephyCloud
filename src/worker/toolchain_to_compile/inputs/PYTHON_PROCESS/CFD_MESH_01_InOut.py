#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys,os
from math import sqrt,log,exp
import traceback

from ZS_COMMON import UpdateProgress

PATH=os.path.realpath(os.path.dirname(sys.argv[0]))+'/'

time2use=sys.argv[1]
ithread=sys.argv[2]
code=sys.argv[3]
folder=sys.argv[4]
message=sys.argv[5]
nsect=int(eval(sys.argv[6]))
diaref=eval(sys.argv[7])

try:
		
	UpdateProgress(time2use,ithread,0.0,message)
		
	infile=open(folder+'/FILES/'+code+'_roughness','r')
	lines=infile.readlines()
	infile.close()
	xgr=[]
	ygr=[]
	rgr=[]
	for i in range(len(lines)):
		values=lines[i].split()
		xgr.append(eval(values[4]))
		ygr.append(eval(values[5]))
		rgr.append(eval(values[6]))
	ngr=len(xgr)
	
	UpdateProgress(time2use,ithread,0.3,message)
	
	nint=0
	lim=(diaref/sqrt(2.))/2.
	rmoy_tot=0.
	rmoy_int=0.
	for i in range(ngr):
		rmoy_tot=rmoy_tot+1./(log(10./rgr[i]))**2 
		dx=abs(xgr[i])
		dy=abs(ygr[i])
		if dx<lim and dy<lim:
			try:
				rmoy_int+=1./(log(10./rgr[i]))**2
				nint+=1
			except: pass
	
	rmoy_tot/=ngr
	rmoy_int/=nint
	rmoy_tot=10.*exp(-1/sqrt(rmoy_tot)) 
	rmoy_int=10.*exp(-1/sqrt(rmoy_int))
	
	UpdateProgress(time2use,ithread,0.6,message)
	
	infile=open(folder+'/FILES/'+code+'_elevation.msh2','r')
	lines=infile.readlines()
	infile.close()
	
	ngroups=int(eval(lines[4]))
	npts=int(eval(lines[7+ngroups]))
	nele=int(eval(lines[10+ngroups+npts]))
	
	bcnums=[]
	bcnames=[]
	
	for i in range(nsect*2):
		ii=6+i
		bcnums.append(eval(lines[ii].split()[1]))
		bcnames.append(lines[ii].split()[2][1:-1])
	
	numinout=[]
	inout=[]
	iinout=-1
	for i in range(nele):
		if i%100==0:
			avancement=min(1.,0.5+float(i)/(2*nele))
			UpdateProgress(time2use,ithread,avancement,message)
		values=lines[i+11+ngroups+npts].split()
		if values[1]=='3':
			num=eval(values[3])
			try:
				inum=numinout.index(num)
				i1=int(eval(values[5]))
				i2=int(eval(values[6]))
				i3=int(eval(values[7]))
				i4=int(eval(values[8]))
				ip1=i1+ngroups+7
				ip2=i2+ngroups+7
				ip3=i3+ngroups+7
				ip4=i4+ngroups+7
				z1=eval(lines[ip1].split()[3])
				z2=eval(lines[ip2].split()[3])
				z3=eval(lines[ip3].split()[3])
				z4=eval(lines[ip4].split()[3])
				zp=min(z1,z2,z3,z4)
				inout[inum][3]=min(inout[inum][3],zp)
			except:
				numinout.append(num)
				inout.append([])
				iinout+=1
				i1=int(eval(values[5]))
				i2=int(eval(values[6]))
				i3=int(eval(values[7]))
				i4=int(eval(values[8]))
				ip1=i1+ngroups+7
				ip2=i2+ngroups+7
				ip3=i3+ngroups+7
				ip4=i4+ngroups+7
				x1=eval(lines[ip1].split()[1])
				y1=eval(lines[ip1].split()[2])
				z1=eval(lines[ip1].split()[3])
				x2=eval(lines[ip2].split()[1])
				y2=eval(lines[ip2].split()[2])
				z2=eval(lines[ip2].split()[3])
				x3=eval(lines[ip3].split()[1])
				y3=eval(lines[ip3].split()[2])
				z3=eval(lines[ip3].split()[3])
				x4=eval(lines[ip4].split()[1])
				y4=eval(lines[ip4].split()[2])
				z4=eval(lines[ip4].split()[3])
				xp=(x1+x2+x3+x4)/4.
				yp=(y1+y2+y3+y4)/4.
				zp=min(z1,z2,z3,z4)
				inew=bcnums.index(num)
				inout[iinout].append(num)
				inout[iinout].append(xp)
				inout[iinout].append(yp)
				inout[iinout].append(zp)
				inout[iinout].append(bcnames[inew])
	
	outfile=open(folder+'/FILES/'+code+'_inout_bc','w')
	for i in range(len(inout)):
		xi=inout[i][1]
		yi=inout[i][2]
		zi=inout[i][3]
		ci=inout[i][4]
		dmin1=1e+8
		for ii in range(ngr):
			d=sqrt((xi-xgr[ii])**2+(yi-ygr[ii])**2)
			if d<dmin1:
				dmin1=d
				r1i=rgr[ii]
				#ZTDEV
				#add calculation for inlet upwind sector average roughness
		r2i=r1i
		outfile.write(ci+'%15.2f'%zi+'\t'+'%15.4f'%r1i+'\t'+'%15.4f'%r2i+'\n')
	
	outfile.close()
	
	outfile=open(folder+'/FILES/inout_param_'+code,'w')
	outfile.write(str(nint)+'\n')
	outfile.write(str(rmoy_tot)+'\n')
	outfile.write(str(rmoy_int)+'\n')
	outfile.close()

except:
	print 'Error in CFD_MESH_01_InOut'
	print(traceback.format_exc())

