import struct

class DecodeError(Exception):
	pass

class BitStream:
	def __init__(self, buffer):
		self.buffer = buffer
		self.index = 0
		self.pooledBits = 0
		self.pooledBitCount = 0
	
	def read(self, bits):
		while self.pooledBitCount < bits:
			if self.index >= len(self.buffer):
				raise DecodeError('unexpected end of crilayla stream')
			self.pooledBits = self.pooledBits << 8 | self.buffer[len(self.buffer) - self.index - 1]
			self.pooledBitCount += 8
			self.index += 1
		result = self.pooledBits >> (self.pooledBitCount - bits)
		self.pooledBitCount -= bits
		self.pooledBits = self.pooledBits & ((1 << self.pooledBitCount) - 1)
		return result

def decompressCrilaylaStream(stream, uncompressedSize):
	buffer = bytearray(uncompressedSize)
	size = 0
	
	while size < len(buffer):
		isReferenceBlock = stream.read(1)
		if isReferenceBlock:
			# backreference to earlier data in output buffer
			referenceOffset = stream.read(13) + 3
			referenceLength = 3
			
			def referenceLengthSizeChunks():
				for i in [2, 3, 5, 8]:
					yield i
				while True:
					yield 8
			for chunkSize in referenceLengthSizeChunks():
				chunk = stream.read(chunkSize)
				referenceLength += chunk
				if chunk + 1 != 1 << chunkSize:
					break
			
			for i in range(referenceLength):
				buffer[len(buffer) - size - 1] = buffer[len(buffer) - size - 1 + referenceOffset]
				size += 1
		
		else:
			# raw byte
			byte = stream.read(8)
			buffer[len(buffer) - size - 1] = byte
			size += 1
	
	return buffer

def decompressCrilayla(buffer):
	( magic, uncompressedSize, uncompressedPrefixOffset ) = struct.unpack('< 8s I I', buffer[0:16])
	if str(magic, 'UTF-8') != 'CRILAYLA':
		raise DecodeError('invalid magic')
	
	# hardcoded
	uncompressedPrefixLength = 0x100
	if 0x10 + uncompressedPrefixOffset + uncompressedPrefixLength > len(buffer):
		raise DecodeError('crilayla buffer too short')
	uncompressedPrefix = buffer[0x10 + uncompressedPrefixOffset : 0x10 + uncompressedPrefixOffset + uncompressedPrefixLength]
	
	# The total buffer, minus the header, minus the uncompressed prefix
	stream = BitStream(buffer[0x10 : 0x10 + uncompressedPrefixOffset])
	return uncompressedPrefix + decompressCrilaylaStream(stream, uncompressedSize)
