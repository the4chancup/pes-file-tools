#! /usr/bin/env python3

import datetime, os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import cpk

def addFile(cpk, realFilename, packedFilename):
	stat = os.stat(realFilename)
	mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
	
	inputFile = open(realFilename, 'rb')
	content = inputFile.read()
	inputFile.close()
	
	if not cpk.writeFile(packedFilename, content, mtime):
		print("Cannot pack duplicate filename '%s'" % packedFilename)
		return False
	
	return True

def addFileRecursive(cpk, filename, pathPrefix):
	if not os.path.isdir(filename):
		if not addFile(cpk, filename, pathPrefix):
			return False
	else:
		for entry in sorted(list(os.listdir(filename))):
			path = os.path.join(filename, entry)
			if not addFileRecursive(cpk, path, "%s/%s" % (pathPrefix, entry)):
				return False
	return True

def main(cpkFile, packedFiles, allowOverwrite):
	if not allowOverwrite and os.path.exists(cpkFile):
		print("Output file '%s' already exists, not overwriting" % cpkFile)
		return
	
	outputFile = cpk.CpkWriter()
	outputFile.open(cpkFile)
	
	for filename in packedFiles:
		if not addFileRecursive(outputFile, filename, os.path.basename(filename.strip('/\\'))):
			return
	
	outputFile.close()

def usage():
	print("pes-cpk-pack -- Pack a PES cpk archive")
	print("Usage:")
	print("  pes-cpk-pack [OPTIONS] <cpk file> [filename]...")
	print("    Recursively packs the contents of <filename>")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing cpk file")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
cpkFile = None
packedFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg[0:1] == '-':
		usage()
	elif cpkFile is None:
		cpkFile = arg
	else:
		packedFiles.append(arg)

if cpkFile is None:
	usage()

main(cpkFile, packedFiles, allowOverwrite)
