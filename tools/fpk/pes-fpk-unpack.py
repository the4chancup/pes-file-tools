#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import fpk

def main(fpkFile, listMode, allowOverwrite, directory):
	inputFile = fpk.FpkFile()
	try:
		inputFile.readFile(fpkFile)
	except Exception as e:
		print("Error reading fpk file: %s" % e)
		return
	
	if directory is not None:
		os.chdir(directory)
	
	for filename in sorted(inputFile.entries.keys()):
		if listMode:
			print(filename)
			continue
		
		filenameComponents = filename.replace('\\', '/').split('/')
		if len(filenameComponents) == 0:
			continue
		if filenameComponents[-1] == '':
			continue
		components = [component for component in filenameComponents if component != '']
		
		for i in range(len(components) - 1):
			d = os.path.join(*components[0 : i + 1])
			if os.path.isdir(d):
				continue
			elif os.path.exists(d):
				print("Cannot create directory '%s': file exists" % d)
				return
			else:
				os.mkdir(d)
		
		effectiveFilename = os.path.join(*components)
		if not allowOverwrite and os.path.exists(effectiveFilename):
			print("Output file '%s' already exists, not overwriting" % effectiveFilename)
			return
		
		output = open(effectiveFilename, 'wb')
		output.write(inputFile.entries[filename])
		output.close()

def usage():
	print("pes-fpk-unpack -- Unpack or list a PES fpk archive")
	print("Usage:")
	print("  pes-fpk-unpack [OPTIONS] <fpk file>")
	print("  pes-fpk-unpack [OPTIONS] <fpk file> --list")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing packed files")
	print("  -d, --directory <DIR>      Unpack in directory <DIR>")
	print("  -l, --list                 List packed files")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
directory = None
listMode = False
fpkFile = None

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg in ['-d', '--directory']:
		if index >= len(sys.argv):
			usage()
		if directory is not None:
			usage()
		directory = sys.argv[index]
		index += 1
	elif arg in ['-l', '--list']:
		listMode = True
	elif arg[0:1] == '-':
		usage()
	elif fpkFile is None:
		fpkFile = arg
	else:
		usage()

if fpkFile is None:
	usage()

main(fpkFile, listMode, allowOverwrite, directory)
