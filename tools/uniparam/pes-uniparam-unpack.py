#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import uniparam, zlib

def main(
	uniparamFile,
	packedFiles,
	listMode,
	allowOverwrite,
):
	inputFile = uniparam.UniformParameterFile()
	try:
		inputFile.readFile(uniparamFile)
	except Exception as e:
		print("Error reading UniformParameter file: %s" % e)
		return
	
	for filename in sorted(inputFile.entries.keys()):
		if listMode:
			print(filename)
			continue
		
		if len(packedFiles) > 0 and filename not in packedFiles:
			continue
		
		effectiveFilename = filename
		if '/' in effectiveFilename:
			effectiveFilename = effectiveFilename[effectiveFilename.rfind('/') + 1:]
		if '\\' in effectiveFilename:
			effectiveFilename = effectiveFilename[effectiveFilename.rfind('\\') + 1:]
		
		if not allowOverwrite and os.path.exists(effectiveFilename):
			print("Output file '%s' already exists, not overwriting" % effectiveFilename)
			return
		
		output = open(effectiveFilename, 'wb')
		output.write(inputFile.entries[filename])
		output.close()

def usage():
	print("pes-uniparam-unpack -- Unpack or list the contents of a PES UniformParameters file")
	print("Usage:")
	print("  pes-uniparam-unpack [OPTIONS] <UniformParameters file> [packed filename]...")
	print("  pes-uniparam-unpack [OPTIONS] <UniformParameters file> --list")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing packed files")
	print("  -l, --list                 List packed files")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
listMode = False
uniparamFile = None
packedFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg in ['-l', '--list']:
		listMode = True
	elif arg[0:1] == '-':
		usage()
	elif uniparamFile is None:
		uniparamFile = arg
	else:
		packedFiles.append(arg)

if uniparamFile is None:
	usage()

main(uniparamFile, packedFiles, listMode, allowOverwrite)
