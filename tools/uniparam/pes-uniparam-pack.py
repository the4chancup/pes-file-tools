import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import uniparam, zlib

def main(
	uniparamFile,
	packedFiles,
	allowOverwrite,
):
	outputFile = uniparam.UniformParameterFile()
	
	if not allowOverwrite and os.path.exists(uniparamFile):
		print("Output file '%s' already exists, not overwriting" % uniparamFile)
		return
	
	sourceFiles = {}
	for filename in packedFiles:
		effectiveFilename = filename
		if '/' in effectiveFilename:
			effectiveFilename = effectiveFilename[effectiveFilename.rfind('/') + 1:]
		if '\\' in effectiveFilename:
			effectiveFilename = effectiveFilename[effectiveFilename.rfind('\\') + 1:]
		
		if effectiveFilename in sourceFiles:
			print("Cannot pack duplicate filenames '%s' and '%s'" % (filename, sourceFiles[effectiveFilename]))
			return
		
		sourceFiles[effectiveFilename] = filename
	
	for effectiveFilename in sourceFiles.keys():
		filename = sourceFiles[effectiveFilename]
		inputFile = open(filename, 'rb')
		content = inputFile.read()
		inputFile.close()
		outputFile.entries[effectiveFilename] = content
	
	outputFile.writeFile(uniparamFile)

def usage():
	print("pes-uniparam-pack -- Pack a collection of kit config files into a PES UniformParameters file")
	print("Usage:")
	print("  pes-uniparam-pack [OPTIONS] <UniformParameters file> [filename]...")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing UniformParameter file")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
uniparamFile = None
packedFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg[0:1] == '-':
		usage()
	elif uniparamFile is None:
		uniparamFile = arg
	else:
		packedFiles.append(arg)

if uniparamFile is None:
	usage()

main(uniparamFile, packedFiles, allowOverwrite)
