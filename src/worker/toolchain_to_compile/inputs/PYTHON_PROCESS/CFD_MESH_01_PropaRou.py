#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys,os
import traceback

from ZS_COMMON import UpdateProgress

PATH=os.path.realpath(os.path.dirname(sys.argv[0]))+'/'

time2use=sys.argv[1]
ithread=sys.argv[2]
code=sys.argv[3]
folder=sys.argv[4]
message=sys.argv[5]

try:
	
	UpdateProgress(time2use,ithread,0.0,message)
		
	liste=[]
	infile=open(folder+'/FILES/'+code+'_roughness','r')
	lines=infile.readlines()
	infile.close()
	for line in lines:
		liste.append(round(eval(line.split()[-1]),5))
	liste.sort()
	liste_rough=[]
	valprec=-1.0
	for val in liste:
		if val!=valprec: liste_rough.append(val)
		valprec=val
				
	UpdateProgress(time2use,ithread,0.05,message)
		
	infile=open(folder+'/FILES/'+code+'.msh2','r')
	lines=infile.readlines()
	infile.close()
	
	infile=open(folder+'/FILES/'+code+'_roughness','r')
	linesrou=infile.readlines()
	infile.close()
		
	outfile=open(folder+'/FILES/'+code+'_rough.msh2','w')
		
	groundlist		=[]
	groundlistnum	=[]
	ngroups			=int(eval(lines[4]))
	npts			=int(eval(lines[7+ngroups]))
	nele			=int(eval(lines[10+ngroups+npts]))
	nngroups		=ngroups-1+2*len(liste_rough)
	ninout			=ngroups-3
			
	for i in range(4): outfile.write(lines[i])
	outfile.write(str(nngroups)+'\n')
	outfile.write(lines[5])
	for i in range(ninout): outfile.write(lines[i+7])
	
	for i in range(len(liste_rough)):
		char='%7.5f'%liste_rough[i]
		groundlist.append(char)
		groundlistnum.append(1001+i)
		outfile.write('2 '+str(1001+i)+' "ground_'+char+'"\n')
	for i in range(len(liste_rough)):
		char='%7.5f'%liste_rough[i]
		outfile.write('3 '+str(2001+i)+' "canopy_'+char+'"\n')
	
	for i in range(7+npts): outfile.write(lines[i+4+ngroups])
	
	UpdateProgress(time2use,ithread,0.5,message)
		
	for i in range(nele):
		if i%10000==0:
			avancement=min(1.,0.5+float(i)/(2*nele))
			UpdateProgress(time2use,ithread,avancement,message)
		ii=i+11+ngroups+npts
		values=lines[ii].split()
		if values[1]=='2' and values[3]=='3':
			inum=int(eval(values[0]))
			b0=int(eval(values[1]))
			b1=int(eval(values[2]))
			rouvalues=linesrou[inum-1].split()
			rouval=round(eval(rouvalues[-1]),5)
			char='%7.5f'%rouval
			n=groundlistnum[groundlist.index(char)]
			b2=int(eval(values[4]))
			i1=int(eval(values[5]))
			i2=int(eval(values[6]))
			i3=int(eval(values[7]))
			outfile.write(str(inum)+' '+str(b0)+' '+str(b1)+' '+str(n)+' '+str(b2)+' '+str(i1)+' '+str(i2)+' '+str(i3)+'\n')
		else: outfile.write(lines[ii])
	
	outfile.write(lines[ii+1])
	outfile.close()
	
	outfile=open(folder+'/FILES/'+code+'_ground_bc','w')
	for i in range(len(groundlist)): outfile.write(groundlist[i]+'\n')
	outfile.close()
	
	UpdateProgress(time2use,ithread,1.0,' ')

except:
	print 'Error in CFD_MESH_01_PropaRou'
	print(traceback.format_exc())
