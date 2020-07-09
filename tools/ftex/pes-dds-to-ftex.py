#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import ftex

def main(ddsFiles, ftexFilename, colorspace, allowOverwrite):
	for ddsFile in ddsFiles:
		if ftexFilename is not None:
			outputFilename = ftexFilename
		elif ddsFile.lower().endswith('.dds'):
			outputFilename = ddsFile[:-4] + '.ftex'
		else:
			outputFilename = ddsFile + '.ftex'
		
		if not allowOverwrite and os.path.exists(outputFilename):
			print("Output file '%s' already exists, not overwriting" % outputFilename)
			return
		
		ftex.ddsToFtex(ddsFile, outputFilename, colorspace)

def usage():
	print("pes-dds-to-ftex -- Convert a dds image to PES ftex format")
	print("Usage:")
	print("  pes-dds-to-ftex [OPTIONS] [dds filename]...")
	print("  pes-dds-to-ftex [OPTIONS] <dds filename> <ftex filename>")
	print("Options:")
	print("  -c, --colorspace <space>   Select ftex colorspace to use in ftex:")
	print("                               linear   ftex stores linear colors")
	print("                               sRGB     ftex stores sRGB colors")
	print("                               normal   ftex stores noncolor data [default]")
	print("  -r, --allow-replace        Allow overwriting existing packed files")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
ddsFiles = []
ftexFilename = None
colorspace = None

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg in ['-c', '--colorspace']:
		if index >= len(sys.argv):
			usage()
		if colorspace is not None:
			usage()
		colorspace = sys.argv[index].upper()
		index += 1
		if colorspace not in ['LINEAR', 'SRGB', 'NORMAL']:
			usage()
	elif arg[0:1] == '-':
		usage()
	else:
		ddsFiles.append(arg)

if len(ddsFiles) == 0:
	usage()

if len(ddsFiles) == 2 and ddsFiles[0].lower().endswith('.dds') and ddsFiles[1].lower().endswith('.ftex'):
	ftexFilename = ddsFiles[1]
	ddsFiles = [ddsFiles[0]]

main(ddsFiles, ftexFilename, colorspace, allowOverwrite)
