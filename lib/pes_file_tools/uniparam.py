import io
import struct

class DecodeError(Exception):
	pass

class UniformParameterFile:
	def __init__(self):
		# entries is a dictionary from $filename (string) to $content (bytes).
		# $filename is the kit config filename;
		# $content is the content of the kit config file.
		self.entries = {}
	
	def read(self, byteBuffer):
		data = memoryview(byteBuffer)
		
		if len(data) < 8:
			raise DecodeError("Incomplete header")
		(entryCount, entryOffset) = struct.unpack('< II', data[0:8])
		
		entryStream = io.BytesIO(data[entryOffset:])
		entries = {}
		for i in range(entryCount):
			entryBuffer = bytearray(12)
			if entryStream.readinto(entryBuffer) != len(entryBuffer):
				raise DecodeError("Incomplete entry")
			(contentOffset, contentLength, filenameOffset) = struct.unpack('< III', entryBuffer)
			
			filenameStream = io.BytesIO(data[filenameOffset:])
			filenameBytes = b''
			while True:
				filenameByte = bytearray(1)
				if filenameStream.readinto(filenameByte) != len(filenameByte):
					raise DecodeError("Unexpected end of file reading entry filename")
				if filenameByte[0] == 0:
					break
				filenameBytes += filenameByte
			filename = str(filenameBytes, 'utf-8')
			
			if not (0 <= contentOffset <= len(data)) and (contentOffset + contentLength <= len(data)):
				raise DecodeError("Incomplete data for entry '%s'" % filename)
			content = bytes(data[contentOffset : contentOffset + contentLength])
			
			if filename in entries:
				raise DecodeError("Duplicate entry for filename '%s'" % filename)
			entries[filename] = content
		self.entries = entries
	
	def readFile(self, filename):
		stream = open(filename, 'rb')
		byteBuffer = stream.read()
		stream.close()
		self.read(byteBuffer)
	
	def write(self):
		entries = []
		filenameBuffer = bytearray()
		contentBuffer = bytearray()
		for filename in sorted(self.entries.keys()):
			relativeFilenameOffset = len(filenameBuffer)
			filenameBuffer += bytes(filename, 'utf-8')
			filenameBuffer += b'\0'
			
			relativeContentOffset = len(contentBuffer)
			contentBuffer += self.entries[filename]
			if len(contentBuffer) % 16 > 0:
				contentBuffer += bytearray(16 - len(contentBuffer) % 16)
			
			entries.append((relativeContentOffset, len(self.entries[filename]), relativeFilenameOffset))
		
		entryBuffer = bytearray()
		entryBufferOffset = 8
		filenameBufferOffset = entryBufferOffset + 12 * len(entries)
		contentBufferOffset = filenameBufferOffset + len(filenameBuffer)
		for (relativeContentOffset, contentLength, relativeFilenameOffset) in entries:
			entryBuffer += struct.pack('< III',
				relativeContentOffset + contentBufferOffset,
				contentLength,
				relativeFilenameOffset + filenameBufferOffset,
			)
		
		header = struct.pack('< II', len(entries), entryBufferOffset)
		return header + entryBuffer + filenameBuffer + contentBuffer
	
	def writeFile(self, filename):
		stream = open(filename, 'wb')
		stream.write(self.write())
		stream.close()
		