import io
import struct
import zlib

class DecodeError(Exception):
	pass

#
# Pixel formats:
# (ftex format ID) -- (dds dxgiFormat)
#
#  0 -- D3DFMT_A8R8G8B8
#  1 -- DXGI_FORMAT_R8_UNORM
#  2 -- BC1U ["DXT1"]
#  3 -- BC2U ["DXT3"]
#  4 -- BC3U ["DXT5"]
#  8 -- BC4U [DXGI_FORMAT_BC4_UNORM]
#  9 -- BC5U [DXGI_FORMAT_BC5_UNORM]
# 10 -- BC6H_UF16 [DXGI_FORMAT_BC6H_UF16]
# 11 -- BC7U [DXGI_FORMAT_BC7_UNORM]
# 12 -- DXGI_FORMAT_R16G16B16A16_FLOAT
# 13 -- DXGI_FORMAT_R32G32B32A32_FLOAT
# 14 -- DXGI_FORMAT_R10G10B10A2_UNORM
# 15 -- DXGI_FORMAT_R11G11B10_FLOAT
#
# Format support:
#  PES18: 0-4
#  PES19: 0-4, 8-15
#

#
# For each ftex format, stores the height and width of encoded blocks,
# and the size in bytes of each encoded block.
#
formatBlockConfiguration = {
	0:  (1,  4), # D3DFMT_A8R8G8B8
	1:  (1,  1), # DXGI_FORMAT_R8_UNORM
	2:  (4,  8), # DXGI_FORMAT_BC1_UNORM ["DXT1"]
	3:  (4, 16), # DXGI_FORMAT_BC2_UNORM ["DXT3"]
	4:  (4, 16), # DXGI_FORMAT_BC3_UNORM ["DXT5"]
	8:  (4,  8), # DXGI_FORMAT_BC4_UNORM
	9:  (4, 16), # DXGI_FORMAT_BC5_UNORM
	10: (4, 16), # DXGI_FORMAT_BC6H_UF16
	11: (4, 16), # DXGI_FORMAT_BC7_UNORM
	12: (1,  8), # DXGI_FORMAT_R16G16B16A16_FLOAT
	13: (1, 16), # DXGI_FORMAT_R32G32B32A32_FLOAT
	14: (1,  4), # DXGI_FORMAT_R10G10B10A2_UNORM
	15: (1,  4), # DXGI_FORMAT_R11G11B10_FLOAT
}
def ddsMipmapSize(ftexFormat, width, height, depth, mipmapIndex):
	(blockSizePixels, blockSizeBytes) = formatBlockConfiguration[ftexFormat]
	scaleFactor = 2 ** mipmapIndex
	
	mipmapWidth = (width + scaleFactor - 1) // scaleFactor
	mipmapHeight = (height + scaleFactor - 1) // scaleFactor
	mipmapDepth = (depth + scaleFactor - 1) // scaleFactor
	
	widthBlocks = (mipmapWidth + blockSizePixels - 1) // blockSizePixels
	heightBlocks = (mipmapHeight + blockSizePixels - 1) // blockSizePixels
	return widthBlocks * heightBlocks * mipmapDepth * blockSizeBytes

def ftexToDdsBuffer(ftexBuffer):
	def readImageBuffer(stream, imageOffset, chunkCount, uncompressedSize, compressedSize):
		stream.seek(imageOffset, 0)
		
		if chunkCount == 0:
			if compressedSize == 0:
				uncompressedBuffer = bytearray(uncompressedSize)
				if stream.readinto(uncompressedBuffer) != len(uncompressedBuffer):
					raise DecodeError("Unexpected end of stream")
				return uncompressedBuffer
			else:
				compressedBuffer = bytearray(compressedSize)
				if stream.readinto(compressedBuffer) != len(compressedBuffer):
					raise DecodeError("Unexpected end of stream")
				return zlib.decompress(compressedBuffer)
		
		chunks = []
		for i in range(chunkCount):
			header = bytearray(8)
			if stream.readinto(header) != len(header):
				raise DecodeError("Incomplete chunk header")
			(
				compressedSize,
				uncompressedSize,
				offset,
			) = struct.unpack('< HH I', header)
			isCompressed = (offset & (1 << 31)) == 0
			offset &= ~(1 << 31)
			
			chunks.append((offset, compressedSize, isCompressed))
		
		imageBuffers = []
		for (offset, compressedSize, isCompressed) in chunks:
			stream.seek(imageOffset + offset, 0)
			compressedBuffer = bytearray(compressedSize)
			if stream.readinto(compressedBuffer) != len(compressedBuffer):
				raise DecodeError("Unexpected end of stream")
			if isCompressed:
				try:
					decompressedBuffer = zlib.decompress(compressedBuffer)
				except:
					raise DecodeError("Decompression error")
			else:
				decompressedBuffer = compressedBuffer
			imageBuffers.append(decompressedBuffer)
		return b''.join(imageBuffers)
	
	
	
	inputStream = io.BytesIO(ftexBuffer)
	
	header = bytearray(64)
	if inputStream.readinto(header) != len(header):
		raise DecodeError("Incomplete ftex header")
	
	(
		ftexMagic,
		ftexVersion,
		ftexPixelFormat,
		ftexWidth,
		ftexHeight,
		ftexDepth,
		ftexMipmapCount,
		ftexNrt,
		ftexFlags,
		ftexUnknown1,
		ftexUnknown2,
		ftexTextureType,
		ftexFtexsCount,
		ftexUnknown3,
		ftexHash1,
		ftexHash2,
	) = struct.unpack('< 4s f HHHH  BB HIII  BB 14x  8s 8s', header)
	
	if ftexMagic != b'FTEX':
		raise DecodeError("Incorrect ftex signature")
	
	if ftexVersion < 2.025:
		raise DecodeError("Unsupported ftex version")
	if ftexVersion > 2.045:
		raise DecodeError("Unsupported ftex version")
	if ftexFtexsCount > 0:
		raise DecodeError("Unsupported ftex variant")
	if ftexMipmapCount == 0:
		raise DecodeError("Unsupported ftex variant")
	
	
	
	ddsFlags = (
		  0x1        # capabilities
		| 0x2        # height
		| 0x4        # width
		| 0x1000     # pixel format
	)
	ddsCapabilities1 = 0x1000 # texture
	ddsCapabilities2 = 0
	
	if (ftexTextureType & 4) != 0:
		# Cube map, with six faces
		if ftexDepth > 1:
			raise DecodeError("Unsupported ftex variant")
		imageCount = 6
		ddsDepth = 1
		ddsCapabilities1 |= 0x8    # complex
		ddsCapabilities2 |= 0xfe00 # cube map with six faces
		
		ddsExtensionDimension = 3 # 2D
		ddsExtensionFlags = 0x4 # cube map
	elif ftexDepth > 1:
		# Volume texture
		imageCount = 1
		ddsDepth = ftexDepth
		ddsFlags |= 0x800000      # depth
		ddsCapabilities2 |= 0x200000 # volume texture
		
		ddsExtensionDimension = 4 # 3D
		ddsExtensionFlags = 0
	else:
		# Regular 2D texture
		imageCount = 1
		ddsDepth = 1
		
		ddsExtensionDimension = 3 # 2D
		ddsExtensionFlags = 0
	
	ddsMipmapCount = ftexMipmapCount
	mipmapCount = ftexMipmapCount
	ddsFlags |= 0x20000          # mipmapCount
	ddsCapabilities1 |= 0x8      # complex
	ddsCapabilities1 |= 0x400000 # mipmap
	
	
	
	#
	# A frame is a byte array containing a single mipmap element of a single image.
	# Cube maps have six images with mipmaps, and so 6 * $mipmapCount frames.
	# Other textures just have $mipmapCount frames.
	#
	frameSpecifications = []
	for i in range(imageCount):
		for j in range(mipmapCount):
			mipmapHeader = bytearray(16)
			if inputStream.readinto(mipmapHeader) != len(mipmapHeader):
				raise DecodeError("Incomplete mipmap header")
			(
				offset,
				uncompressedSize,
				compressedSize,
				index,
				ftexsNumber,
				chunkCount,
			) = struct.unpack('< I I I BB H', mipmapHeader)
			if index != j:
				raise DecodeError("Unexpected mipmap")
			
			expectedFrameSize = ddsMipmapSize(ftexPixelFormat, ftexWidth, ftexHeight, ddsDepth, j)
			frameSpecifications.append((offset, chunkCount, uncompressedSize, compressedSize, expectedFrameSize))
	
	frames = []
	for (offset, chunkCount, uncompressedSize, compressedSize, expectedSize) in frameSpecifications:
		frame = readImageBuffer(inputStream, offset, chunkCount, uncompressedSize, compressedSize)
		if len(frame) < expectedSize:
			frame += bytes(expectedSize - len(frame))
		elif len(frame) > expectedSize:
			frame = frame[0:expectedSize]
		frames.append(frame)
	
	
	
	ddsPitch = None
	if ftexPixelFormat == 0:
		ddsPitchOrLinearSize = 4 * ftexWidth
		ddsFlags |= 0x8 # pitch
		useExtensionHeader = False
		
		ddsFormatFlags = 0x41 # uncompressed rgba
		ddsFourCC = b'\0\0\0\0'
		ddsRgbBitCount = 32
		ddsRBitMask = 0x00ff0000
		ddsGBitMask = 0x0000ff00
		ddsBBitMask = 0x000000ff
		ddsABitMask = 0xff000000
	else:
		ddsPitchOrLinearSize = len(frames[0])
		ddsFlags |= 0x80000 # linear size
		
		ddsFormatFlags = 0x4 # compressed
		ddsRgbBitCount = 0
		ddsRBitMask = 0
		ddsGBitMask = 0
		ddsBBitMask = 0
		ddsABitMask = 0
		
		ddsFourCC = None
		ddsExtensionFormat = None
		
		if ftexPixelFormat == 1:
			ddsExtensionFormat = 61 # DXGI_FORMAT_R8_UNORM
		elif ftexPixelFormat == 2:
			ddsFourCC = b'DXT1'
		elif ftexPixelFormat == 3:
			ddsFourCC = b'DXT3'
		elif ftexPixelFormat == 4:
			ddsFourCC = b'DXT5'
		elif ftexPixelFormat == 8:
			ddsExtensionFormat = 80 # DXGI_FORMAT_BC4_UNORM
		elif ftexPixelFormat == 9:
			ddsExtensionFormat = 83 # DXGI_FORMAT_BC5_UNORM
		elif ftexPixelFormat == 10:
			ddsExtensionFormat = 95 # DXGI_FORMAT_BC6H_UF16
		elif ftexPixelFormat == 11:
			ddsExtensionFormat = 98 # DXGI_FORMAT_BC7_UNORM
		elif ftexPixelFormat == 12:
			ddsExtensionFormat = 10 # DXGI_FORMAT_R16G16B16A16_FLOAT
		elif ftexPixelFormat == 13:
			ddsExtensionFormat = 2  # DXGI_FORMAT_R32G32B32A32_FLOAT
		elif ftexPixelFormat == 14:
			ddsExtensionFormat = 24 # DXGI_FORMAT_R10G10B10A2_UNORM
		elif ftexPixelFormat == 15:
			ddsExtensionFormat = 26 # DXGI_FORMAT_R11G11B10_FLOAT
		else:
			raise DecodeError("Unsupported ftex codec")
		
		if ddsExtensionFormat is not None:
			ddsFourCC = b'DX10'
			useExtensionHeader = True
		else:
			useExtensionHeader = False
	
	
	
	outputStream = io.BytesIO()
	outputStream.write(struct.pack('< 4s 7I 44x 2I 4s 5I 2I 12x',
		b'DDS ',
		
		124, # header size
		ddsFlags,
		ftexHeight,
		ftexWidth,
		ddsPitchOrLinearSize,
		ddsDepth,
		ddsMipmapCount,
		
		32, # substructure size
		ddsFormatFlags,
		ddsFourCC,
		ddsRgbBitCount,
		ddsRBitMask,
		ddsGBitMask,
		ddsBBitMask,
		ddsABitMask,
		
		ddsCapabilities1,
		ddsCapabilities2,
	))
	
	if useExtensionHeader:
		outputStream.write(struct.pack('< 5I',
			ddsExtensionFormat,
			ddsExtensionDimension,
			ddsExtensionFlags,
			1, # array size
			0, # flags
		))
	
	for frame in frames:
		outputStream.write(frame)
	
	return outputStream.getbuffer()

def ftexToDds(ftexFilename, ddsFilename):
	inputStream = open(ftexFilename, 'rb')
	inputBuffer = inputStream.read()
	inputStream.close()
	
	outputBuffer = ftexToDdsBuffer(inputBuffer)
	
	outputStream = open(ddsFilename, 'wb')
	outputStream.write(outputBuffer)
	outputStream.close()



def ddsToFtexBuffer(ddsBuffer, colorSpace):
	def encodeImage(data):
		chunkSize = 1 << 14 # Value known not to crash PES
		chunkCount = (len(data) + chunkSize - 1) // chunkSize
		
		headerBuffer = bytearray()
		chunkBuffer = bytearray()
		chunkBufferOffset = chunkCount * 8
		
		for i in range(chunkCount):
			chunk = data[chunkSize * i : chunkSize * (i + 1)]
			compressedChunk = zlib.compress(chunk, level = 9)
			offset = len(chunkBuffer)
			chunkBuffer += compressedChunk
			headerBuffer += struct.pack('< HHI',
				len(compressedChunk),
				len(chunk),
				offset + chunkBufferOffset,
			)
		
		return (headerBuffer + chunkBuffer, chunkCount)
	
	inputStream = io.BytesIO(ddsBuffer)
	
	header = bytearray(128)
	if inputStream.readinto(header) != len(header):
		raise DecodeError("Incomplete dds header")
	
	(
		ddsMagic,
		ddsHeaderSize,
		ddsFlags,
		ddsHeight,
		ddsWidth,
		ddsPitchOrLinearSize,
		ddsDepth,
		ddsMipmapCount,
		# ddsReserved,
		
		ddsPixelFormatSize,
		ddsFormatFlags,
		ddsFourCC,
		ddsRgbBitCount,
		ddsRBitMask,
		ddsGBitMask,
		ddsBBitMask,
		ddsABitMask,
		
		ddsCapabilities1,
		ddsCapabilities2,
		# ddsReserved,
	) = struct.unpack('< 4s 7I 44x 2I 4s 5I 2I 12x', header)
	
	if ddsMagic != b'DDS ':
		raise DecodeError("Incorrect dds signature")
	if ddsHeaderSize != 124:
		raise DecodeError("Incorrect dds header")
	
	if (
		    (ddsCapabilities1 & 0x400000) > 0 # mipmap
		and (ddsMipmapCount > 1)
	):
		mipmapCount = ddsMipmapCount
	else:
		mipmapCount = 1
	
	if ddsCapabilities2 & 0x200 > 0: #cubemap
		if ddsCapabilities2 & 0xfe00 != 0xfe00:
			raise DecodeError("Incomplete dds cube maps not supported")
		isCubeMap = True
		cubeEntries = 6
	else:
		isCubeMap = False
		cubeEntries = 1
	
	if ddsCapabilities2 & 0x200000 > 0: # volume texture
		depth = ddsDepth
	else:
		depth = 1
	
	if isCubeMap and depth > 1:
		raise DecodeError("Invalid dds combination: cube map and volume map both set")
	
	if colorSpace == 'LINEAR':
		ftexTextureType = 0x1
	elif colorSpace == 'SRGB':
		ftexTextureType = 0x3
	elif colorSpace == 'NORMAL':
		ftexTextureType = 0x9
	else:
		ftexTextureType = 0x9
	if isCubeMap:
		ftexTextureType |= 0x4
	
	
	
	if ddsFormatFlags & 0x4 == 0: # fourCC absent
		if (
			    (ddsFormatFlags & 0x40) > 0 # rgb
			and (ddsFormatFlags & 0x1) > 1  # alpha
			and ddsRBitMask == 0x00ff0000
			and ddsGBitMask == 0x0000ff00
			and ddsBBitMask == 0x000000ff
			and ddsABitMask == 0xff000000
		):
			ftexPixelFormat = 0
		else:
			raise DecodeError("Unsupported dds codec")
	elif ddsFourCC == b'DX10':
		extensionHeader = bytearray(20)
		if inputStream.readinto(extensionHeader) != len(extensionHeader):
			raise DecodeError("Incomplete dds extension header")
		
		(
			ddsExtensionFormat,
			# ddsOther,
		) = struct.unpack('< I 16x', extensionHeader)
		
		if ddsExtensionFormat == 61: # DXGI_FORMAT_R8_UNORM
			ftexPixelFormat = 1
		elif ddsExtensionFormat == 71: # DXGI_FORMAT_BC1_UNORM ["DXT1"]
			ftexPixelFormat = 2
		elif ddsExtensionFormat == 74: # DXGI_FORMAT_BC2_UNORM ["DXT3"]
			ftexPixelFormat = 3
		elif ddsExtensionFormat == 77: # DXGI_FORMAT_BC3_UNORM ["DXT5"]
			ftexPixelFormat = 4
		elif ddsExtensionFormat == 80: # DXGI_FORMAT_BC4_UNORM
			ftexPixelFormat = 8
		elif ddsExtensionFormat == 83: # DXGI_FORMAT_BC5_UNORM
			ftexPixelFormat = 9
		elif ddsExtensionFormat == 95: # DXGI_FORMAT_BC6H_UF16
			ftexPixelFormat = 10
		elif ddsExtensionFormat == 98: # DXGI_FORMAT_BC7_UNORM
			ftexPixelFormat = 11
		elif ddsExtensionFormat == 10: # DXGI_FORMAT_R16G16B16A16_FLOAT
			ftexPixelFormat = 12
		elif ddsExtensionFormat == 1:  # DXGI_FORMAT_R32G32B32A32_FLOAT
			ftexPixelFormat = 13
		elif ddsExtensionFormat == 24: # DXGI_FORMAT_R10G10B10A2_UNORM
			ftexPixelFormat = 14
		elif ddsExtensionFormat == 26: # DXGI_FORMAT_R11G11B10_FLOAT
			ftexPixelFormat = 15
		else:
			raise DecodeError("Unsupported dds codec")
	elif ddsFourCC == b'8888':
		ftexPixelFormat = 0
	elif ddsFourCC == b'DXT1':
		ftexPixelFormat = 2
	elif ddsFourCC == b'DXT3':
		ftexPixelFormat = 3
	elif ddsFourCC == b'DXT5':
		ftexPixelFormat = 4
	else:
		raise DecodeError("Unsupported dds codec")
	
	if ftexPixelFormat > 4:
		ftexVersion = 2.04
	else:
		ftexVersion = 2.03
	
	
	
	frameBuffer = bytearray()
	mipmapEntries = []
	for _ in range(cubeEntries):
		for mipmapIndex in range(mipmapCount):
			length = ddsMipmapSize(ftexPixelFormat, ddsWidth, ddsHeight, depth, mipmapIndex)
			frame = inputStream.read(length)
			if len(frame) != length:
				raise DecodeError("Unexpected end of dds stream")
			
			frameOffset = len(frameBuffer)
			(compressedFrame, chunkCount) = encodeImage(frame)
			frameBuffer += compressedFrame
			mipmapEntries.append((frameOffset, len(frame), len(compressedFrame), mipmapIndex, chunkCount))
	
	mipmapBuffer = bytearray()
	mipmapBufferOffset = 64
	frameBufferOffset = mipmapBufferOffset + len(mipmapEntries) * 16
	for (relativeFrameOffset, uncompressedSize, compressedSize, mipmapIndex, chunkCount) in mipmapEntries:
		mipmapBuffer += struct.pack('< III BB H',
			relativeFrameOffset + frameBufferOffset,
			uncompressedSize,
			compressedSize,
			mipmapIndex,
			0, # ftexs number
			chunkCount
		)
	
	header = struct.pack('< 4s f HHHH  BB HIII  BB 14x  16x',
		b'FTEX',
		ftexVersion,
		ftexPixelFormat,
		ddsWidth,
		ddsHeight,
		depth,
		mipmapCount,
		0x02, # nrt flag, meaning unknown
		0x11, # unknown flags
		1, # unknown
		0, # unknown
		ftexTextureType,
		0, # ftexs count
		0, # unknown
		# 14 bytes padding
		# 16 bytes hashes
	)
	
	return header + mipmapBuffer + frameBuffer

def ddsToFtex(ddsFilename, ftexFilename, colorSpace):
	inputStream = open(ddsFilename, 'rb')
	inputBuffer = inputStream.read()
	inputStream.close()
	
	outputBuffer = ddsToFtexBuffer(inputBuffer, colorSpace)
	
	outputStream = open(ftexFilename, 'wb')
	outputStream.write(outputBuffer)
	outputStream.close()
