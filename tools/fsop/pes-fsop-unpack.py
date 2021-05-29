#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import fsop

def main(fsopFile, listMode, allowOverwrite, directory):
	inputFile = fsop.FsopFile()
	try:
		inputFile.readFile(fsopFile)
	except Exception as e:
		print("Error reading fsop file: %s" % e)
		return
	
	if directory is not None:
		os.chdir(directory)
	
	for name in sorted(inputFile.entries.keys()):
		if listMode:
			print(name)
			continue
		
		if not os.path.exists(name):
			os.mkdir(name)
		elif os.path.isdir(name):
			print("Cannot create directory '%s': file exists" % name)
		
		vertexFilename = os.path.join(name, 'vertex-shader.cso')
		pixelFilename = os.path.join(name, 'pixel-shader.cso')
		
		if not allowOverwrite and os.path.exists(vertexFilename):
			print("Output file '%s' already exists, not overwriting" % vertexFilename)
			return
		
		if not allowOverwrite and os.path.exists(pixelFilename):
			print("Output file '%s' already exists, not overwriting" % pixelFilename)
			return
		
		vertexOutput = open(vertexFilename, 'wb')
		vertexOutput.write(inputFile.entries[name].vertexShader)
		vertexOutput.close()
		
		pixelOutput = open(pixelFilename, 'wb')
		pixelOutput.write(inputFile.entries[name].pixelShader)
		pixelOutput.close()

def usage():
	print("pes-fsop-unpack -- Unpack or list a PES fsop shader pack")
	print("Usage:")
	print("  pes-fsop-unpack [OPTIONS] <fsop file>")
	print("  pes-fsop-unpack [OPTIONS] <fsop file> --list")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing packed files")
	print("  -d, --directory <DIR>      Unpack in directory <DIR>")
	print("  -l, --list                 List packed files")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
directory = None
listMode = False
fsopFile = None

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
	elif fsopFile is None:
		fsopFile = arg
	else:
		usage()

if fsopFile is None:
	usage()

main(fsopFile, listMode, allowOverwrite, directory)
