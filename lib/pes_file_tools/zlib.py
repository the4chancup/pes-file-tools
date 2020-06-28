import struct
import zlib

class DecodeError(Exception):
	pass

def encodeHeader(compressedBuffer, uncompressedBuffer):
	return struct.pack('< 3B 5s II',
		0x00,
		0x10,
		0x01,
		'WESYS'.encode('UTF-8'),
		len(compressedBuffer),
		len(uncompressedBuffer),
	)

def decodeHeader(byteBuffer):
	if len(byteBuffer) < 16:
		return None
	header = byteBuffer[0:16]
	(magic, ) = struct.unpack('< 4x 4s 8x', header)
	if magic != b'ESYS':
		return None
	return memoryview(byteBuffer)[16:]

def compress(byteBuffer):
	compressedBuffer = zlib.compress(byteBuffer)
	return encodeHeader(compressedBuffer, byteBuffer) + compressedBuffer

def tryCompress(byteBuffer):
	compressedBuffer = zlib.compress(byteBuffer)
	if len(compressedBuffer) + 16 < len(byteBuffer):
		return encodeHeader(compressedBuffer, byteBuffer) + compressedBuffer
	else:
		return byteBuffer

def decompress(byteBuffer):
	compressedBuffer = decodeHeader(byteBuffer)
	if compressedBuffer is None:
		raise DecodeError()
	try:
		return zlib.decompress(compressedBuffer)
	except:
		raise DecodeError()

def tryDecompress(byteBuffer):
	compressedBuffer = decodeHeader(byteBuffer)
	if compressedBuffer is None:
		return byteBuffer
	try:
		return zlib.decompress(compressedBuffer)
	except:
		raise DecodeError()

def isCompressed(byteBuffer):
	compressedBuffer = decodeHeader(byteBuffer)
	return compressedBuffer is not None
