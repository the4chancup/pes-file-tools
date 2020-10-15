import hashlib
import io
import struct

class DecodeError(Exception):
	pass

class FpkFile:
	def __init__(self):
		self.entries = {}
	
	def read(self, byteBuffer):
		data = memoryview(byteBuffer)
		
		if len(data) < 48:
			raise DecodeError("Incomplete header")
		(
			magic1,
			fpkType,
			magic2,
			fileSize,
			unknown1,
			fileCount,
			referenceCount,
			unknown2,
		) = struct.unpack('< 6s B 3s I 18x I I I I', data[0:48])
		
		if magic1 != b'foxfpk':
			raise DecodeError("Invalid FPK")
		if magic2 != b'win':
			raise DecodeError("Invalid FPK")
		
		if unknown1 != 2:
			raise DecodeError("Unsupported FPK")
		if unknown2 != 0:
			raise DecodeError("Unsupported FPK")
		if referenceCount != 0:
			raise DecodeError("Unsupported FPK")
		
		stream = io.BytesIO(data[48:])
		entries = {}
		for i in range(fileCount):
			entryBuffer = bytearray(48)
			if stream.readinto(entryBuffer) != len(entryBuffer):
				raise DecodeError("Incomplete file entry")
			
			(
				contentOffset,
				contentLength,
				filenameOffset,
				filenameLength,
				checksum,
			) = struct.unpack('< QQQQ 16s', entryBuffer)
			
			if contentOffset + contentLength > len(data):
				raise DecodeError("Unexpected end of file")
			if filenameOffset + filenameLength > len(data):
				raise DecodeError("Unexpected end of file")
			
			filename = str(data[filenameOffset : filenameOffset + filenameLength], 'utf-8')
			content = data[contentOffset : contentOffset + contentLength]
			
			if filename in entries:
				raise DecodeError("Duplicate entry for filename '%s'" % filename)
			entries[filename] = content
			
			digest = hashlib.md5()
			digest.update(data[filenameOffset : filenameOffset + filenameLength])
			if digest.digest() != checksum:
				raise DecodeError("Incorrect checksum")
		
		self.entries = entries
	
	def readFile(self, filename):
		stream = open(filename, 'rb')
		byteBuffer = stream.read()
		stream.close()
		self.read(byteBuffer)
	
	def write(self, isFpkd):
		entries = []
		filenameBuffer = bytearray()
		contentBuffer = bytearray()
		for filename in sorted(self.entries.keys()):
			relativeFilenameOffset = len(filenameBuffer)
			encodedFilename = bytes(filename, 'utf-8')
			filenameBuffer += encodedFilename + b'\0'
			
			relativeContentOffset = len(contentBuffer)
			contentBuffer += self.entries[filename]
			if len(contentBuffer) % 16 > 0:
				contentBuffer += bytearray(16 - len(contentBuffer) % 16)
			
			digest = hashlib.md5()
			digest.update(encodedFilename)
			
			entries.append((
				relativeContentOffset,
				len(self.entries[filename]),
				relativeFilenameOffset,
				len(encodedFilename),
				digest.digest(),
			))
		if len(filenameBuffer) % 16 > 0:
			filenameBuffer += bytearray(16 - len(filenameBuffer) % 16)
		
		entryBuffer = bytearray()
		entryBufferOffset = 48
		filenameBufferOffset = entryBufferOffset + 48 * len(entries)
		contentBufferOffset = filenameBufferOffset + len(filenameBuffer)
		for (relativeContentOffset, contentLength, relativeFilenameOffset, filenameLength, filenameDigest) in entries:
			entryBuffer += struct.pack('< QQQQ 16s',
				relativeContentOffset + contentBufferOffset,
				contentLength,
				relativeFilenameOffset + filenameBufferOffset,
				filenameLength,
				filenameDigest,
			)
		
		header = struct.pack('< 6s c 3s I 18x I I I I',
			b'foxfpk',
			(b'd' if isFpkd else b'\0'),
			b'win',
			len(contentBuffer) + contentBufferOffset,
			2,
			len(entries),
			0,
			0,
		)
		return header + entryBuffer + filenameBuffer + contentBuffer
	
	def writeFile(self, filename):
		isFpkd = filename.lower().endswith('.fpkd')
		
		stream = open(filename, 'wb')
		stream.write(self.write(isFpkd))
		stream.close()
