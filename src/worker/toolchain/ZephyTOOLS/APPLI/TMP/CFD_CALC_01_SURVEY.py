#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Investigates monitored results along a calculation and takes action accordingly
Usage:
	./CFD_CALC_01_SURVEY.py -i /path/to/work/dir
"""

from ZS_VARIABLES	import *
from ZS_COMMON	import KillCommand,InvestigateConvergence
import argparse,shutil
import traceback

LOCAL = True
if "CLOUD_WORKER" in os.environ and os.environ["CLOUD_WORKER"].strip() == "1":
	LOCAL = False
elif os.path.isfile(os.path.join(PATH, '..', '..', '..', 'conf')):
	LOCAL = False

DEBUG=LOCAL

wait1,wait2=90.,30.

if DEBUG: wait1,wait2=20.,20.

ddsuf={'COARSE':'i','FINE':'c'}

SetEnviron()

def cfd_calc_01_survey(src_folder):
	"""
	Investigates monitored results along a calculation and takes action accordingly
	
	:param src_folder:      The calculation folder where we will look for results to be monitored
	:type src_folder:       str
	"""

	suf=ddsuf[os.path.basename(src_folder)]
	
	codename=os.path.basename(os.path.abspath(os.path.join(src_folder,'..')))
	
	xmlfile=os.path.join(src_folder,'..','param.xml')
	root=xml.parse(xmlfile).getroot()
	
	time2use=root.find('time2use').text
	progressfile=PATH+'../../APPLI/TMP/logout_'+time2use+'.xml'
	
	extra=''
	if suf=='i': extra='_init'
	
	vlim=eval(root.find('vkill'+extra).text)
	ratio_mt=eval(root.find('tgmes'+extra).text)
	ratio_wt=eval(root.find('tgmach'+extra).text)
	crit_alpha=eval(root.find('cvg_alpha'+extra).text)
	
	IScontroled=root.find('survey'+extra).text=='True' and vlim>0.
	if not IScontroled: return 0
	
	xmlfile=os.path.join(src_folder,'..','..','..','DATA','data.xml')
	root=xml.parse(xmlfile).getroot()
	npt=int(root.find('n_point').text)
	nmt=int(root.find('n_mast').text)
	nwt=int(root.find('n_wt').text)
	nld=int(root.find('n_lidar').text)
	
	logof=os.path.join(src_folder,'log_simpleFoam')
	f1=os.path.join(src_folder,'paused')
	f2=os.path.join(src_folder,'terminated')
	tkf=os.path.join(src_folder,'to_be_killed')
	tsf=os.path.join(src_folder,'to_be_stopped')
	
	itry=0
	while not os.path.isfile(logof) and itry<100:

		if DEBUG: sys.stderr.write("Waiting for log_simpleFoam\n");sys.stderr.flush()
		
		time.sleep(2.5)
		itry+=1
	
	if not os.path.isfile(logof): return 1

	nsav=999
	perc_mt,perc_wt=0.,0.

	while True:
		
		time.sleep(wait1)
		
		if os.path.isfile(f1) or os.path.isfile(f2): return 0
		
		if not os.path.isfile(logof): return 1
		
		lv,lk=[],[]
		
		xmlfile=os.path.join(src_folder,'..','history.xml')
		root=xml.parse(xmlfile).getroot()
		for bal in root:
			if suf=='i':
				if bal.attrib['type']=='init':
					with open(os.path.join(src_folder,'postProcessing','probes','U.%s'%bal.attrib['i']),'r') as f: lines=f.readlines()
					for line in lines:
						if line[0]!='#': lv.append(line)
					with open(os.path.join(src_folder,'postProcessing','probes','k.%s'%bal.attrib['i']),'r') as f: lines=f.readlines()
					for line in lines:
						if line[0]!='#': lk.append(line)
			else:
				if bal.attrib['type']=='calc':
					with open(os.path.join(src_folder,'postProcessing','probes','U.%s'%bal.attrib['i']),'r') as f: lines=f.readlines()
					for line in lines:
						if line[0]!='#': lv.append(line)
					with open(os.path.join(src_folder,'postProcessing','probes','k.%s'%bal.attrib['i']),'r') as f: lines=f.readlines()
					for line in lines:
						if line[0]!='#': lk.append(line)
		
		it_prev=0
		with open(os.path.join(src_folder,'..','itstart_%s'%suf),'r') as f: it_prev=f.readline()
		fname=os.path.join(src_folder,'postProcessing','probes',it_prev,'U')
		if os.path.isfile(fname):
			with open(fname,'r') as f: lines=f.readlines()
			for line in lines:
				if line[0]!='#': lv.append(line)
			fname=os.path.join(src_folder,'postProcessing','probes',it_prev,'k')
			with open(fname,'r') as f: lines=f.readlines()
			for line in lines:
				if line[0]!='#': lk.append(line)
				
		if len(lv)==0: continue
		
		res_mt,res_wt=[],[]
		vmax=0.
		res_mt,res_wt,vmax=InvestigateConvergence(lv,lk,npt,nmt,nld,nwt)
		
		if len(res_mt[0])>CVGRES_NTMIN:
			cvgres_nt2use=min(len(res_mt[0]),CVGRES_NTMAX)
			istart,iend=len(res_mt[0])-cvgres_nt2use,len(res_mt[0])
			stdmax,nok=-1.,0
			for ip in range(nmt):
				std=np.array(res_mt[ip])[istart:iend].std()
				stdmax=max(std,stdmax)
				if std<crit_alpha: nok+=1
			if nmt>0: perc_mt=100*float(nok)/float(nmt)
			else: perc_mt=100.

			nok=0
			for ip in range(nwt):
				std=np.array(res_wt[ip])[istart:iend].std()
				stdmax=max(std,stdmax)
				if std<crit_alpha: nok+=1
			if nwt>0: perc_wt=100*float(nok)/float(nwt)
			else: perc_wt=100.
			
			if stdmax>=0.:
				cvg=min(1.,log10(stdmax)/log10(crit_alpha))
				if suf=='i': cvg2display=cvg/10.
				else: cvg2display=max(cvg,0.15)
			else:
				cvg=-1.
				cvg2display=0.
			
			if len(res_mt[0])!=nsav:
				
				nsav=len(res_mt[0])
	
				xmlfile=os.path.join(src_folder,'..','..','calculations.xml')
				if os.path.isfile(xmlfile):
					root=xml.parse(xmlfile).getroot()
					for bal in root:
						if bal.text==codename:
							bal2use=bal
							bal2use.attrib['cvg']='%.1f'%(100.*cvg2display)
							break
					xml.ElementTree(root).write(xmlfile)
				
				if not LOCAL:
					with open(PATH + '../../../progress.txt', 'w') as pf: pf.write('%.2f'%cvg2display)
				else:
					root=xml.Element('logout')
					xml.SubElement(root,'progress_text')
					xml.SubElement(root,'progress_frac').text='%.2f'%cvg2display
					xml.ElementTree(root).write(progressfile)

				text=os.path.basename(src_folder).lower()+'-It:%i'%(nsav*5)
				text+='|Cvg:%.1f%%'%(100.*cvg)
				text+='|Masts %.1f%%'%perc_mt
				text+=' '+str(perc_mt>=ratio_mt)[0]
				text+='|Turb %.1f%%'%perc_wt
				text+=' '+str(perc_wt>=ratio_wt)[0]
				text+='|vmax %.1f\n'%vmax
				
				try:
					with open(os.path.join(src_folder,'..','log'),'a') as f: f.write(text)
				except: sys.stderr.write(text);sys.stderr.flush()
		
		TO_KILL=os.path.isfile(tkf)
		if len(res_mt[0])>CVGRES_NTMIN: TO_STOP=os.path.isfile(tsf)
		else: TO_STOP=False
		
		if not TO_STOP:
			try: TO_STOP=perc_mt>=ratio_mt and perc_wt>=ratio_wt
			except: pass

		if TO_STOP:
			control_file=os.path.join(src_folder,'system','controlDict')
			with open(control_file,'r') as f: lines=f.readlines()
			lines[22]='stopAt writeNow;\n'
			with open(control_file+'_stop','w') as f: f.write("".join(lines))
			shutil.copy(control_file+'_stop',control_file)
			subprocess.call(['touch','-t','2412121212',control_file])
			with open(os.path.join(src_folder,'stopped'),"w") as f: f.write('\n')
			return 0

		if not TO_KILL:
			if vlim>0.: TO_KILL=vmax>vlim

		if TO_KILL:
			if DEBUG: sys.stderr.write('kill\n%s\n'%src_folder);sys.stderr.flush()
			KillCommand('simpleFoam')
			open(src_folder+'/terminated','w').close()
			return 0
		
		time.sleep(wait2)
	
	return 0


def main():
	"""
	Create a zip file from calculation status files

	:return:        0 in case of success, a positive int in case of error
	:rtype:         int
	"""
	
	try:
		parser = argparse.ArgumentParser(description='Launch monitor survey over a calculation')
		parser.add_argument('--input', '-i', help='The calculation input folder')
		args = parser.parse_args()
		if not args.input:
			sys.stderr.write("You should provide the --input argument\n");sys.stderr.flush()
			return 1
		calc_folder = os.path.abspath(args.input)
		if not os.path.exists(calc_folder) or not os.path.isdir(calc_folder):
			sys.stderr.write("Invalid input folder\n");sys.stderr.flush()
			return 1
		
		res=cfd_calc_01_survey(calc_folder)
		
		if res==1:
			sys.stderr.write("log_simpleFoam not found\n");sys.stderr.flush()
		elif res>0:
			sys.stderr.write('Unknown error %i'%res);sys.stderr.flush()
		return res
	except (KeyboardInterrupt, SystemExit):
		print("\nAborting...")
		return 0
	except Exception as e:
		sys.stderr.write("Error when surveying calculation:"+traceback.format_exc());sys.stderr.flush()
		return 1


if __name__ == '__main__':
	sys.exit(main())
