import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import zlib

def main(
	inputFileNames,
	outputFileName,
	inPlace,
	allowMultiple,
	allowOverwrite,
):
	for inputFileName in inputFileNames:
		if outputFileName is not None:
			thisOutputFileName = outputFileName
		elif inPlace:
			thisOutputFileName = inputFileName
		else:
			pos = inputFileName.rfind('.')
			if pos == -1:
				thisOutputFileName = inputFileName + ".compressed"
			else:
				thisOutputFileName = inputFileName[0:pos] + ".compressed." + inputFileName[pos + 1:]
			if not allowOverwrite and os.path.exists(thisOutputFileName):
				print("Output file '%s' already exists, not overwriting" % thisOutputFileName)
				return
		
		inputFile = open(inputFileName, mode = 'rb')
		inputBuffer = inputFile.read()
		inputFile.close()
		
		if not allowMultiple and zlib.isCompressed(inputBuffer):
			print("Input file '%s' is already compressed, not compressing again" % inputFileName)
			return
		
		outputFile = open(thisOutputFileName, mode = 'wb')
		outputFile.write(zlib.compress(inputBuffer))
		outputFile.close()

def usage():
	print("Usage:")
	print("  pes-zlib-compress [OPTIONS] <uncompressed file>...")
	print("  pes-zlib-compress [OPTIONS] <uncompressed file> -o <output file>")
	print("Options:")
	print("  -i, --in-place             Replace uncompressed file with compressed file")
	print("  -m, --allow-multiple       Allow compressing already compressed files")
	print("  -r, --allow-replace        Allow overwriting existing files")
	print("  -o, --output <FILE>        Save compressed file as FILE")
	print("  -h, --help                 Display this help")
	sys.exit()

inPlace = False
allowMultiple = False
allowOverwrite = False
outputFile = None
inputFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-i', '--in-place']:
		inPlace = True
	elif arg in ['-m', '--allow-multiple']:
		allowMultiple = True
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
	allowMultiple,
	allowOverwrite,
)
