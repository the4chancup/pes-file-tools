#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import fpk

def addFile(fpk, realFilename, packedFilename):
	if packedFilename in fpk.entries:
		print("Cannot pack duplicate filename '%s'" % packedFilename)
		return False
	
	inputFile = open(realFilename, 'rb')
	content = inputFile.read()
	inputFile.close()
	
	fpk.entries[packedFilename] = content
	return True

def addDirectoryRecursive(fpk, directory, pathPrefix):
	for filename in os.listdir(directory):
		path = os.path.join(directory, filename)
		if os.path.isdir(path):
			if not addDirectoryRecursive(fpk, path, "%s%s/" % (pathPrefix, filename)):
				return False
		else:
			if not addFile(fpk, path, pathPrefix + filename):
				return False
	return True

def main(fpkFile, packedFiles, allowOverwrite):
	outputFile = fpk.FpkFile()
	
	if not allowOverwrite and os.path.exists(fpkFile):
		print("Output file '%s' already exists, not overwriting" % fpkFile)
		return
	
	for filename in packedFiles:
		if os.path.isdir(filename):
			if not addDirectoryRecursive(outputFile, filename, '/'):
				return
		else:
			effectiveFilename = filename
			if '/' in effectiveFilename:
				effectiveFilename = effectiveFilename[effectiveFilename.rfind('/') + 1:]
			if '\\' in effectiveFilename:
				effectiveFilename = effectiveFilename[effectiveFilename.rfind('\\') + 1:]
			
			if not addFile(outputFile, filename, effectiveFilename):
				return
	
	outputFile.writeFile(fpkFile)

def usage():
	print("pes-fpk-pack -- Pack a PES fpk archive")
	print("Usage:")
	print("  pes-fpk-pack [OPTIONS] <fpk file> [directory]...")
	print("    Recursively packs the contents of <directory> with path information included")
	print("  pes-fpk-pack [OPTIONS] <fpk file> [filename]...")
	print("    Packs the <filename> files without path information")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing fpk file")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
fpkFile = None
packedFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg[0:1] == '-':
		usage()
	elif fpkFile is None:
		fpkFile = arg
	else:
		packedFiles.append(arg)

if fpkFile is None:
	usage()

main(fpkFile, packedFiles, allowOverwrite)
