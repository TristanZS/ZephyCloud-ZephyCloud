#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Create a zip file from calculation status files
Usage:
	./CFD_CALC_ZIP_STATUS.py -i /path/to/calc -o output.zcp
"""

# Python core libs
import sys
import os
import shutil
import argparse
from distutils.dir_util import copy_tree

# Third party libs
import xml.etree.ElementTree as xml

# Project specific libs
from ZS_COMMON import ZipDir


def zip_calc_status(src_folder, output_file):
	"""
	Create a zip file from calculation status files

	:param src_folder:      The calculation folder where we will look for files to zip
	:type src_folder:       str
	:param output_file:     The output zip file we will generate
	:type output_file:      str
	"""
	
	dest_folder = os.path.abspath(os.path.join(src_folder, 'CVG'))
	os.system('rm -rf %s'%dest_folder)
	os.system('mkdir -p %s'%dest_folder)

	for filename in ['actual.xml', 'history.xml', 'info.xml', 'itstart_c', 'itstart_i', 'param.xml', 'terminated',
					 'log']:
		if os.path.isfile(os.path.join(src_folder, filename)):
			shutil.copy(os.path.join(src_folder, filename), os.path.join(dest_folder, filename))

	for calc_type in ['FINE', 'COARSE']:
		if not os.path.exists(os.path.join(dest_folder, calc_type, 'postProcessing')):
			os.makedirs(os.path.join(dest_folder, calc_type, 'postProcessing'))
		if os.path.isdir(os.path.join(src_folder, calc_type, 'logs')):
			copy_tree(os.path.join(src_folder, calc_type, 'logs'), os.path.join(dest_folder, calc_type, 'logs'))
		if os.path.isdir(os.path.join(src_folder, calc_type, 'postProcessing', 'probes')):
			copy_tree(os.path.join(src_folder, calc_type, 'postProcessing', 'probes'),
					  os.path.join(dest_folder, calc_type, 'postProcessing', 'probes'))
		for filename in ['launched', 'terminated', 'log_simpleFoam']:
			if os.path.isfile(os.path.join(src_folder, calc_type, filename)):
				shutil.copy(os.path.join(src_folder, calc_type, filename),
							os.path.join(dest_folder, calc_type, filename))

	if os.path.exists(os.path.join(src_folder, 'history.xml')):
		root = xml.parse(os.path.join(src_folder, "history.xml")).getroot()
		for calc_type in ['FINE', 'COARSE']:
			for bal in root:
				if bal.attrib['type'] == 'init':
					filename = 'log_simpleFoam.' + bal.attrib['i']
					shutil.copy(os.path.join(src_folder, 'COARSE', filename),
								os.path.join(dest_folder, calc_type, filename))
				elif bal.attrib['type'] == 'calc':
					filename = 'log_simpleFoam.' + bal.attrib['i']
					shutil.copy(os.path.join(src_folder, 'FINE', filename),
								os.path.join(dest_folder, calc_type, filename))

	if os.path.exists(output_file):
		os.remove(output_file)
	ZipDir(os.path.join(src_folder, 'CVG'), output_file)


def main():
	"""
	Create a zip file from calculation status files

	:return:        0 in case of success, a positive int in case of error
	:rtype:         int
	"""
	try:
		parser = argparse.ArgumentParser(description='Zip all the files about a calculation status')
		parser.add_argument('--input', '-i', help='The calculation input folder')
		parser.add_argument('--output', '-o', help="The file to generate")
		args = parser.parse_args()
		if not args.input:
			sys.stderr.write("You should provide the --input argument\n")
			sys.stderr.flush()
			return 1
		calc_folder = os.path.abspath(args.input)
		if not os.path.exists(calc_folder) or not os.path.isdir(calc_folder):
			sys.stderr.write("Invalid input folder\n")
			sys.stderr.flush()
			return 1
		if not args.output:
			sys.stderr.write("You should provide the --output argument\n")
			sys.stderr.flush()
			return 1
		output_file = os.path.abspath(args.output)
		zip_calc_status(calc_folder, output_file)
		return 0
	except (KeyboardInterrupt, SystemExit):
		print("\nAborting...")
		return 0
	except Exception as e:
		sys.stderr.write("Error while packaging calculation status: " + str(e) + "\n")
		sys.stderr.flush()
		return 1


if __name__ == '__main__':
	sys.exit(main())
