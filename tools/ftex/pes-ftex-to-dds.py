#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import ftex

def main(ftexFiles, ddsFilename, allowOverwrite):
	for ftexFile in ftexFiles:
		if ddsFilename is not None:
			outputFilename = ddsFilename
		elif ftexFile.lower().endswith('.ftex'):
			outputFilename = ftexFile[:-5] + '.dds'
		else:
			outputFilename = ftexFile + '.dds'
		
		if not allowOverwrite and os.path.exists(outputFilename):
			print("Output file '%s' already exists, not overwriting" % outputFilename)
			return
		
		ftex.ftexToDds(ftexFile, outputFilename)

def usage():
	print("pes-ftex-to-dds -- Convert a PES ftex image to dds format")
	print("Usage:")
	print("  pes-ftex-to-dds [OPTIONS] [ftex filename]...")
	print("  pes-ftex-to-dds [OPTIONS] <ftex filename> <dds filename>")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing packed files")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
ftexFiles = []
ddsFilename = None

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg[0:1] == '-':
		usage()
	else:
		ftexFiles.append(arg)

if len(ftexFiles) == 0:
	usage()

if len(ftexFiles) == 2 and ftexFiles[0].lower().endswith('.ftex') and ftexFiles[1].lower().endswith('.dds'):
	ddsFilename = ftexFiles[1]
	ftexFiles = [ftexFiles[0]]

main(ftexFiles, ddsFilename, allowOverwrite)
