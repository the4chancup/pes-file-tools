#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import zlib

def main(
	inputFileNames,
	outputFileName,
	inPlace,
	allowNoop,
	allowOverwrite
):
	for inputFileName in inputFileNames:
		if outputFileName is not None:
			thisOutputFileName = outputFileName
		elif inPlace:
			thisOutputFileName = inputFileName
		else:
			pos = inputFileName.rfind('.')
			if pos == -1:
				thisOutputFileName = inputFileName + ".decompressed"
			else:
				thisOutputFileName = inputFileName[0:pos] + ".decompressed." + inputFileName[pos + 1:]
			if not allowOverwrite and os.path.exists(thisOutputFileName):
				print("Output file '%s' already exists, not overwriting" % thisOutputFileName)
				return
		
		inputFile = open(inputFileName, mode = 'rb')
		inputBuffer = inputFile.read()
		inputFile.close()
		
		if not allowNoop and not zlib.isCompressed(inputBuffer):
			print("Input file '%s' is not compressed" % inputFileName)
			return
		
		try:
			outputBuffer = zlib.tryDecompress(inputBuffer)
		except:
			print("Error decompressing input file '%s'" % inputFileName)
			return
		
		outputFile = open(thisOutputFileName, mode = 'wb')
		outputFile.write(outputBuffer)
		outputFile.close()

def usage():
	print("pes-zlib-decompress -- Decompress a file compressed using PES zlib compression")
	print("Usage:")
	print("  pes-zlib-decompress [OPTIONS] <compressed file>...")
	print("  pes-zlib-decompress [OPTIONS] <compressed file> -o <output file>")
	print("Options:")
	print("  -i, --in-place             Replace compressed file with uncompressed file")
	print("  -n, --allow-noop           Store copy of input file if input is not compressed")
	print("  -r, --allow-replace        Allow overwriting existing files")
	print("  -o, --output <FILE>        Save uncompressed file as FILE")
	print("  -h, --help                 Display this help")
	sys.exit()

inPlace = False
allowNoop = False
allowOverwrite = False
outputFile = None
inputFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-i', '--in-place']:
		inPlace = True
	elif arg in ['-n', '--allow-noop']:
		allowNoop = True
	elif arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg in ['-o', '--output']:
		if index >= len(sys.argv):
			usage()
		if outputFile is not None:
			usage()
		outputFile = sys.argv[index]
		index += 1
	elif arg[0:1] == '-':
		usage()
	else:
		inputFiles.append(arg)

if len(inputFiles) == 0:
	usage()
if outputFile is not None and len(inputFiles) != 1:
	usage()

main(
	inputFiles,
	outputFile,
	inPlace,
	allowNoop,
	allowOverwrite,
)
