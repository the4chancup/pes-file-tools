import io
import struct

class DecodeError(Exception):
	pass

class Shader:
	def __init__(self, vertexShader, pixelShader):
		self.vertexShader = vertexShader
		self.pixelShader = pixelShader

class FsopFile:
	cipherValue = 0x9c
	
	def __init__(self):
		self.entries = {}
	
	def crypt(self, shaderBuffer):
		return bytes([b ^ FsopFile.cipherValue for b in shaderBuffer])
	
	def read(self, stream):
		while True:
			nameLengthBuffer = bytearray(1)
			if stream.readinto(nameLengthBuffer) != len(nameLengthBuffer):
				break
			( nameLength, ) = struct.unpack('< B', nameLengthBuffer)
			nameBuffer = bytearray(nameLength)
			if stream.readinto(nameBuffer) != len(nameBuffer):
				raise DecodeError("Incomplete filename entry")
			name = str(nameBuffer[:-1], 'utf-8')
			
			vertexShaderLengthBuffer = bytearray(4)
			if stream.readinto(vertexShaderLengthBuffer) != len(vertexShaderLengthBuffer):
				raise DecodeError("Incomplete vertex shader entry")
			( vertexShaderLength, ) = struct.unpack('< I', vertexShaderLengthBuffer)
			vertexShaderBuffer = bytearray(vertexShaderLength)
			if stream.readinto(vertexShaderBuffer) != len(vertexShaderBuffer):
				raise DecodeError("Incomplete vertex shader")
			
			pixelShaderLengthBuffer = bytearray(4)
			if stream.readinto(pixelShaderLengthBuffer) != len(pixelShaderLengthBuffer):
				raise DecodeError("Incomplete pixel shader entry")
			( pixelShaderLength, ) = struct.unpack('< I', pixelShaderLengthBuffer)
			pixelShaderBuffer = bytearray(pixelShaderLength)
			if stream.readinto(pixelShaderBuffer) != len(pixelShaderBuffer):
				raise DecodeError("Incomplete pixel shader")
			
			self.entries[name] = Shader(self.crypt(vertexShaderBuffer), self.crypt(pixelShaderBuffer))
	
	def readBuffer(self, byteBuffer):
		self.read(io.BytesIO(byteBuffer))
	
	def readFile(self, filename):
		stream = open(filename, 'rb')
		self.read(stream)
		stream.close()
	
	def write(self, stream):
		for name in sorted(self.entries.keys()):
			encodedName = bytes(name, 'utf-8')
			vertexShaderBuffer = self.crypt(self.entries[name].vertexShader)
			pixelShaderBuffer = self.crypt(self.entries[name].pixelShader)
			
			block = (
				  struct.pack('< B', len(encodedName) + 1)
				+ encodedName
				+ bytes([0])
				+ struct.pack('< I', len(vertexShaderBuffer))
				+ vertexShaderBuffer
				+ struct.pack('< I', len(pixelShaderBuffer))
				+ pixelShaderBuffer
			)
			stream.write(block)
	
	def writeBuffer(self):
		stream = io.BytesIO()
		self.write(stream)
		out = stream.getvalue()
		stream.close()
		return out
	
	def writeFile(self, filename):
		stream = open(filename, 'wb')
		self.write(stream)
		stream.close()
