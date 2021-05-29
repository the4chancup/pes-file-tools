#! /usr/bin/env python3

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'lib'))

from pes_file_tools import fsop

def main(fsopFile, packedFiles, allowOverwrite):
	outputFile = fsop.FsopFile()
	
	if not allowOverwrite and os.path.exists(fsopFile):
		print("Output file '%s' already exists, not overwriting" % fsopFile)
		return
	
	for filename in packedFiles:
		name = filename.replace('\\', '/').split('/')[-1]
		vertexShaderFilename = os.path.join(filename, 'vertex-shader.cso')
		pixelShaderFilename = os.path.join(filename, 'pixel-shader.cso')
		
		stream = open(vertexShaderFilename, 'rb')
		vertexShader = stream.read()
		stream.close()
		
		stream = open(pixelShaderFilename, 'rb')
		pixelShader = stream.read()
		stream.close()
		
		outputFile.entries[name] = fsop.Shader(vertexShader, pixelShader)
	
	outputFile.writeFile(fsopFile)

def usage():
	print("pes-fsop-pack -- Pack a PES fsop shader pack")
	print("Usage:")
	print("  pes-fsop-pack [OPTIONS] <fsop file> [directory]...")
	print("    Packs the contents of the <directory> shader directory")
	print("    <directory> must contain 'vertex-shader.cso' and 'pixel-shader.cso' files")
	print("Options:")
	print("  -r, --allow-replace        Allow overwriting existing fsop file")
	print("  -h, --help                 Display this help")
	sys.exit()

allowOverwrite = False
fsopFile = None
packedFiles = []

index = 1
while index < len(sys.argv):
	arg = sys.argv[index]
	index += 1
	if arg in ['-r', '--allow-replace']:
		allowOverwrite = True
	elif arg[0:1] == '-':
		usage()
	elif fsopFile is None:
		fsopFile = arg
	else:
		packedFiles.append(arg)

if fsopFile is None:
	usage()

main(fsopFile, packedFiles, allowOverwrite)
