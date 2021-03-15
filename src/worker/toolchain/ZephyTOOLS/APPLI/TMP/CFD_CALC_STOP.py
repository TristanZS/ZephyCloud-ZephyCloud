#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Sets a calculation file system to stop the calculation
Usage:
	./CFD_CALC_STOP.py /path/to/work/dir
"""


# Python core libs
import sys
import os
import shutil
import argparse
import subprocess

# Third party libs
import xml.etree.ElementTree as xml


def write_stop_calc_file(calc_path):
	"""
	Signal to a running calculation it should stop

	:param calc_path: 		The path to the working directory of the calculation you want to abort
	:type calc_path:		str
	"""
	xmlfile = os.path.join(calc_path, 'param.xml')
	root = xml.parse(xmlfile).getroot()
	NO_INIT=int(root.find('n_it_max_init').text)==0
	PROBLEM = os.path.isfile(os.path.join(calc_path, 'corrupted'))
	OVER_INIT = False
	for f in ('terminated', 'paused', 'stopped'):
		if os.path.isfile(os.path.join(calc_path, 'COARSE', f)):
			OVER_INIT = True
	LAUNCHED = os.path.isfile(os.path.join(calc_path, 'COARSE', 'launched'))
	RUNNING_INIT = not NO_INIT and not PROBLEM and not OVER_INIT and LAUNCHED

	if RUNNING_INIT:
		control_file = os.path.join(calc_path, 'COARSE', 'system', 'controlDict')
		stopped_file = os.path.join(calc_path, 'COARSE', 'stopped')
	else: 
		control_file = os.path.join(calc_path, 'FINE', 'system', 'controlDict')
		stopped_file = os.path.join(calc_path, 'FINE', 'stopped')
	with open(control_file, 'r') as infile:
		lines = infile.readlines()
	lines[22] = "stopAt          writeNow;\n"
	with open(control_file + "_stop", 'w') as outfile:
		outfile.write("".join(lines))
	shutil.copy(control_file+"_stop", control_file)
	subprocess.call(['touch', '-t', '2412121212', control_file])

	with open(stopped_file, "w") as outfile:
		outfile.write("\n")


def main():
	"""
	Signal to a running calculation it should stop

	:return:        0 in case of success, a positive int in case of error
	:rtype:         int
	"""
	try:
		parser = argparse.ArgumentParser(description='Signal to a running calculation it should stop')
		parser.add_argument('WORKDIR', help="The calculation working directory")
		args = parser.parse_args()
		if not args.WORKDIR:
			sys.stderr.write("You should provide the WORKDIR argument\n")
			sys.stderr.flush()
			return 1
		if not os.path.exists(args.WORKDIR) or not os.path.isdir(args.WORKDIR):
			sys.stderr.write(args.WORKDIR + " is not a valid directory\n")
			sys.stderr.flush()
			return 1
		write_stop_calc_file(args.WORKDIR)
		return 0
	except (KeyboardInterrupt, SystemExit):
		print("\nAborting...")
		return 0
	except Exception as e:
		sys.stderr.write("Error in write_stop_calc_file(calc_path): "+str(e)+"\n")
		sys.stderr.flush()
		return 1


if __name__ == '__main__':
	sys.exit(main())
