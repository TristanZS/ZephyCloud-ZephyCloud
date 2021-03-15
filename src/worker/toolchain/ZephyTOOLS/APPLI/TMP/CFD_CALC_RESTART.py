#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Prepares file system to allow calculation restart
Usage:
	./CFD_CALC_RESTART.py /path/to/work/dir
"""


# Python core libs
from ZS_COMMON		import GetParamText,WriteFvSolution,WriteFvSchemes
from ZS_VARIABLES	import *
import argparse

def write_restart_calc_files(calc_path,nit):
	"""
	Signal to a running calculation it should restart

	:param calc_path: 		The path to the working directory of the calculation you want to abort
	:type calc_path:		str
	"""

	file1=PATH+'../../APPLI/TMP/CFD_CALC_01.py.xml'
	if os.path.isfile(file1): subprocess.call(['cp',file1,calc_path+'/param.xml',])

	tpsol		=GetParamText('calc01','psol')
	tssol		=GetParamText('calc01','ssol')
	tpsmoo		=GetParamText('calc01','psmoo')
	tssmoo		=GetParamText('calc01','ssmoo')
	tppred		=GetParamText('calc01','ppred')
	tspred		=GetParamText('calc01','spred')
	tgrad		=GetParamText('calc01','grad')
	tlap		=GetParamText('calc01','lap')
	tdivu		=GetParamText('calc01','divu')
	tdivk		=GetParamText('calc01','divk')
	tdiveps		=GetParamText('calc01','diveps')
	tsngrad=[]
	for elem in tlap: tsngrad.append(elem[13:])

	xmlfile=os.path.join(calc_path, 'param.xml')
	rootin=xml.parse(xmlfile).getroot()
	it_prev=rootin.find('n_it_max').text
	it_new=int(eval(it_prev)+nit)
	
	filename=calc_path+'/FINE/system/controlDict'
	
	subprocess.call(['cp',filename,filename+'_pause'])
	subprocess.call(['cp',filename,filename+'_restart'])

	startfile=calc_path+'/itstart_c'
	with open(startfile,'r') as infile: itstart_prev=infile.readline()
	subprocess.call(['rm',startfile])
	with open(startfile,'w') as outfile: outfile.write(it_prev)
	
	xmlfile=calc_path+'/history.xml'
	root=xml.parse(xmlfile).getroot()
	imax=0
	for bal in root: imax=max(imax,int(eval(bal.attrib['i'])))
	imax+=1
	newbal=xml.SubElement(root,'pause')
	newbal.attrib['i']=str(imax)
	newbal.attrib['type']='calc'

	param_xmlfile=calc_path+'/actual.xml'
	param_root=xml.parse(param_xmlfile).getroot()
	
	for v in ddParam['calc01'].keys(): xml.SubElement(newbal,v).text=param_root.find(v).text

	xml.ElementTree(root).write(xmlfile)

	xmlfile=calc_path+'/param.xml'
	root=xml.parse(xmlfile).getroot()
	root.find('n_it_max').text=str(it_new)
	xml.ElementTree(root).write(xmlfile)
	
	filename=calc_path+'/FINE/system/controlDict'

	subprocess.call(['cp',filename,filename+'_restart'])

	dd={}
	
	dd['grad']=tgrad[int(root.find('grad_init').text)]
	dd['lap']=tlap[int(root.find('lap_init').text)]
	dd['sngrad']=tsngrad[int(root.find('lap_init').text)]
	dd['psol']=tpsol[int(root.find('psol_init').text)]
	dd['tol_p']=root.find('tol_p_init').text
	dd['rtol_p']=root.find('rtol_p_init').text
	dd['psmoo']=tpsmoo[int(root.find('psmoo_init').text)]
	dd['ppred']=tppred[int(root.find('ppred_init').text)]
	dd['ssol']=tssol[int(root.find('ssol_init').text)]
	dd['tol_s']=root.find('tol_s_init').text
	dd['rtol_s']=root.find('rtol_s_init').text
	dd['ssmoo']=tssmoo[int(root.find('ssmoo_init').text)]
	dd['spred']=tspred[int(root.find('spred_init').text)]
	dd['npre']=root.find('npre_init').text
	dd['npost']=root.find('npost_init').text
	dd['ncor']=root.find('correctors_init').text
	dd['cvg_p']=root.find('cvg_p_init').text
	dd['cvg_u']=root.find('cvg_u_init').text
	dd['cvg_k']=root.find('cvg_k_init').text
	dd['cvg_eps']=root.find('cvg_eps_init').text
	dd['cvg_alpha']=root.find('cvg_alpha_init').text
	dd['relax_p']=root.find('relax_p_init').text
	dd['relax_u']=root.find('relax_u_init').text
	dd['relax_k']=root.find('relax_k_init').text
	dd['relax_eps']=root.find('relax_eps_init').text
	dd['simplec']=eval(root.find('simplec_init').text)
	dd['divu']=tdivu[int(root.find('divu_init').text)]
	dd['divk']=tdivk[int(root.find('divk_init').text)]
	dd['diveps']=tdiveps[int(root.find('diveps_init').text)]

	with open(calc_path+'/../../../../COMMON/foam/calc_openfoam/fvSolution','r') as infile: lines=infile.readlines()
	fvpth=calc_path+'/COARSE/system/fvSolution'
	if os.path.isfile(fvpth): subprocess.call(['mv',fvpth,fvpth+'_restart'])
	if os.path.isdir(calc_path+'/COARSE/system'): WriteFvSolution(fvpth,dd,lines)

	with open(calc_path+'/../../../../COMMON/foam/calc_openfoam/fvSchemes','r') as infile: lines=infile.readlines()
	fvpth=calc_path+'/COARSE/system/fvSchemes'
	if os.path.isfile(fvpth): subprocess.call(['mv',fvpth,fvpth+'_restart'])
	if os.path.isdir(calc_path+'/COARSE/system'): WriteFvSchemes(fvpth,dd,lines)

	dd={}
	dd['grad']=tgrad[int(root.find('grad').text)]
	dd['lap']=tlap[int(root.find('lap').text)]
	dd['sngrad']=tsngrad[int(root.find('lap').text)]
	dd['psol']=tpsol[int(root.find('psol').text)]
	dd['tol_p']=root.find('tol_p').text
	dd['rtol_p']=root.find('rtol_p').text
	dd['psmoo']=tpsmoo[int(root.find('psmoo').text)]
	dd['ppred']=tppred[int(root.find('ppred').text)]
	dd['ssol']=tssol[int(root.find('ssol').text)]
	dd['tol_s']=root.find('tol_s').text
	dd['rtol_s']=root.find('rtol_s').text
	dd['ssmoo']=tssmoo[int(root.find('ssmoo').text)]
	dd['spred']=tspred[int(root.find('spred').text)]
	dd['npre']=root.find('npre').text
	dd['npost']=root.find('npost').text
	dd['ncor']=root.find('correctors').text
	dd['cvg_p']=root.find('cvg_p').text
	dd['cvg_u']=root.find('cvg_u').text
	dd['cvg_k']=root.find('cvg_k').text
	dd['cvg_eps']=root.find('cvg_eps').text
	dd['cvg_alpha']=root.find('cvg_alpha').text
	dd['relax_p']=root.find('relax_p').text
	dd['relax_u']=root.find('relax_u').text
	dd['relax_k']=root.find('relax_k').text
	dd['relax_eps']=root.find('relax_eps').text
	dd['simplec']=eval(root.find('simplec').text)
	dd['divu']=tdivu[int(root.find('divu').text)]
	dd['divk']=tdivk[int(root.find('divk').text)]
	dd['diveps']=tdiveps[int(root.find('diveps').text)]

	with open(calc_path+'/../../../../COMMON/foam/calc_openfoam/fvSolution','r') as infile: lines=infile.readlines()
	fvpth=calc_path+'/FINE/system/fvSolution'
	if os.path.isfile(fvpth): subprocess.call(['mv',fvpth,fvpth+'_restart'])
	WriteFvSolution(fvpth,dd,lines)

	with open(calc_path+'/../../../../COMMON/foam/calc_openfoam/fvSchemes','r') as infile: lines=infile.readlines()
	fvpth=calc_path+'/FINE/system/fvSchemes'
	if os.path.isfile(fvpth): subprocess.call(['mv',fvpth,fvpth+'_restart'])
	WriteFvSchemes(fvpth,dd,lines)
	
	subprocess.call(['rm','-f',calc_path+'/FINE/stopped'])
	subprocess.call(['rm','-f',calc_path+'/FINE/terminated'])
	subprocess.call(['rm','-f',calc_path+'/FINE/paused'])

	with open(calc_path+'/itstart_c','r') as infile:  it_start=str(int(eval(infile.readline())))

	with open(calc_path+'/FINE/system/controlDict','r') as infile: lines=infile.readlines()
		
	with open(filename,'w') as outfile:
		n=len(lines)
		i=0
		while i<20:
			outfile.write(lines[i])
			i+=1
		outfile.write('startTime         '+it_start+';\n\n')
		outfile.write('stopAt	         endTime;\n\n')
		outfile.write('endTime         '+str(it_new)+';\n')
		outfile.write(lines[25])
		outfile.write(lines[26])
		outfile.write(lines[27])
		outfile.write(lines[28])
		outfile.write(lines[29])
		outfile.write('writeInterval   '+str(it_new)+';\n')
		i=31
		while i<n:
			outfile.write(lines[i])
			i+=1
	
	xmlfile=calc_path+'/history.xml'
	root=xml.parse(xmlfile).getroot()
	imax=0
	for bal in root: imax=max(imax,int(eval(bal.attrib['i'])))
	newbal=xml.SubElement(root,'pause')
	newbal.attrib['i']=str(imax)
	newbal.attrib['type']='calc'

	logfile=calc_path+'/FINE/log_simpleFoam'
	subprocess.call(['cp','-f',logfile,logfile+'.'+str(imax)])
	subprocess.call(['rm',logfile])
	
	infile=calc_path+'/FINE/postProcessing/probes/'+itstart_prev+'/U'
	outfile=calc_path+'/FINE/postProcessing/probes/U'+'.'+str(imax)
	subprocess.call(['cp','-f',infile,outfile])
	subprocess.call(['rm',infile])
	infile=calc_path+'/FINE/postProcessing/probes/'+itstart_prev+'/k'
	outfile=calc_path+'/FINE/postProcessing/probes/k'+'.'+str(imax)
	subprocess.call(['cp','-f',infile,outfile])
	subprocess.call(['rm',infile])

	open(calc_path+'/restarted','w').close()
	subprocess.call(['rm','-f',calc_path+'/terminated'])
	subprocess.call(['rm','-f',calc_path+'/FINE/terminated'])
	subprocess.call(['rm','-f',calc_path+'/FINE/paused'])
	
def main():
	"""
	Signal to a running calculation it should restart

	:return:        0 in case of success, a positive int in case of error
	:rtype:         int
	"""
	try:
		parser = argparse.ArgumentParser(description='Signal to a running calculation it should stop')
		parser.add_argument('WORKDIR', help="The calculation working directory")
		parser.add_argument('nit', help="The number of iterations")
		args = parser.parse_args()
		if not args.WORKDIR:
			sys.stderr.write("You should provide the WORKDIR argument\n")
			sys.stderr.flush()
			return 1
		if not args.nit:
			sys.stderr.write("You should provide the nit argument\n")
			sys.stderr.flush()
			return 1
		if not os.path.exists(args.WORKDIR) or not os.path.isdir(args.WORKDIR):
			sys.stderr.write(args.WORKDIR + " is not a valid directory\n")
			sys.stderr.flush()
			return 1
		write_restart_calc_files(args.WORKDIR,int(args.nit))
		return 0
	except (KeyboardInterrupt, SystemExit):
		print("\nAborting...")
		return 0
	except Exception as e:
		sys.stderr.write("Error in write_restart_calc_files(calc_path): "+str(e)+"\n")
		sys.stderr.flush()
		write_restart_calc_files(args.WORKDIR,int(args.nit))
		return 1

if __name__ == '__main__':
	sys.exit(main())
