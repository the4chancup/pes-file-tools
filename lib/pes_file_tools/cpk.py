import datetime
import io
import struct

from .crilayla import decompressCrilayla

class DecodeError(Exception):
	pass

def read(stream, size):
	output = bytes()
	while len(output) < size:
		buffer = stream.read(size - len(output))
		if len(buffer) == 0:
			raise DecodeError("Unexpected end of file")
		output += buffer
	return output

def write(stream, content):
	while len(content) > 0:
		written = stream.write(content)
		if written == 0:
			raise DecodeError("Writing error")
		content = content[written:]

class UtfTable:
	class UtfDatumType:
		int8 = 0
		int16 = 2
		int32 = 4
		int64 = 6
		float32 = 8
		string = 10
		bytestring = 11
		# I believe 1,3,5,7 are signed integers, but I have never seen them in any pes files
	
	datumSizes = {
		UtfDatumType.int8: 1,
		UtfDatumType.int16: 2,
		UtfDatumType.int32: 4,
		UtfDatumType.int64: 8,
		UtfDatumType.float32: 4,
		UtfDatumType.string: 4,
		UtfDatumType.bytestring: 8,
	}
	
	class UtfDatumStorage:
		null = 1
		constant = 3
		variable = 5
	
	class Column:
		def __init__(self, name, datumType):
			self.name = name
			self.datumType = datumType
	
	def __init__(self):
		self.columns = []
		self.rows = []
	
	@staticmethod
	def crypt(block):
		m = 0x5f
		t = 0x15
		
		output = bytearray(len(block))
		for i in range(len(output)):
			output[i] = block[i] ^ (m & 0xff)
			m *= t
			m &= 0xff
		return output
	
	def read(self, stream, offset, tableName):
		stream.seek(offset, 0)
		outerHeader = read(stream, 16)
		( name, unknown, length ) = struct.unpack('< 4s I Q', outerHeader)
		nameString = str(name, 'UTF-8')
		if nameString != tableName:
			raise DecodeError("Unexpected utf table name, found '%s', expected '%s'" % (nameString, tableName))
		
		encryptedContent = read(stream, length)
		if encryptedContent[0:4] == b'@UTF':
			content = memoryview(encryptedContent)
		else:
			content = memoryview(UtfTable.crypt(encryptedContent))
		
		headerStream = io.BytesIO(content)
		header = bytearray(32)
		if headerStream.readinto(header) != len(header):
			raise DecodeError("Unexpected end of input reading cpk header")
		(
			magic,
			bodyLength,
			rowsOffset,
			stringsOffset,
			dataOffset,
			tableName,
			columnCount,
			rowLength,
			rowCount,
		) = struct.unpack('> 4s IIII IHHI', header)
		
		if str(magic, 'UTF-8') != '@UTF':
			raise DecodeError("Unexpected utf table magic")
		if bodyLength + 8 != length:
			raise DecodeError("Unexpected utf table inner length")
		
		body = content[8:]
		rows = body[rowsOffset:]
		strings = body[stringsOffset:]
		data = body[dataOffset:]
		
		def readString(offset):
			stringBytes = bytearray()
			while offset < len(strings) and strings[offset] != 0:
				stringBytes.append(strings[offset])
				offset += 1
			return str(stringBytes, 'UTF-8')
		
		def readData(offset, length):
			return data[offset : offset + length]
		
		def readValue(stream, dataType):
			if dataType == UtfTable.UtfDatumType.int8:
				data = bytearray(1)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( value, ) = struct.unpack('> B', data)
				return value
			elif dataType == UtfTable.UtfDatumType.int16:
				data = bytearray(2)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( value, ) = struct.unpack('> H', data)
				return value
			elif dataType == UtfTable.UtfDatumType.int32:
				data = bytearray(4)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( value, ) = struct.unpack('> I', data)
				return value
			elif dataType == UtfTable.UtfDatumType.int64:
				data = bytearray(8)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( value, ) = struct.unpack('> Q', data)
				return value
			elif dataType == UtfTable.UtfDatumType.float32:
				data = bytearray(4)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( value, ) = struct.unpack('> f', data)
				return value
			elif dataType == UtfTable.UtfDatumType.string:
				data = bytearray(4)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( offset, ) = struct.unpack('> I', data)
				return readString(offset)
			elif dataType == UtfTable.UtfDatumType.bytestring:
				data = bytearray(8)
				if stream.readinto(data) != len(data):
					raise DecodeError("Unexpected end of input")
				( offset, length, ) = struct.unpack('> II', data)
				return readData(offset, length)
			else:
				print("Unknown data type: %s" % dataType)
				return None
		
		columns = []
		for i in range(columnCount):
			rowBuffer = bytearray(5)
			if headerStream.readinto(rowBuffer) != len(rowBuffer):
				raise DecodeError("Unexpected end of input")
			( flags, nameOffset ) = struct.unpack('> B I', rowBuffer)
			
			name = readString(nameOffset)
			datumType = flags & 0x0f
			storageType = flags >> 4
			
			if storageType == UtfTable.UtfDatumStorage.constant:
				constantValue = readValue(headerStream, datumType)
			else:
				constantValue = None
			
			columns.append((name, datumType, storageType, constantValue))
			self.columns.append(UtfTable.Column(name, datumType))
		
		for i in range(rowCount):
			rowBuffer = rows[i * rowLength : (i + 1) * rowLength]
			rowStream = io.BytesIO(rowBuffer)
			
			row = {}
			for (name, datumType, storageType, constantValue) in columns:
				if storageType == UtfTable.UtfDatumStorage.null:
					value = None
				elif storageType == UtfTable.UtfDatumStorage.constant:
					value = constantValue
				elif storageType == UtfTable.UtfDatumStorage.variable:
					value = readValue(rowStream, datumType)
				else:
					print("Unknown encoding: %s" % storageType)
					value = None
				
				row[name] = value
			self.rows.append(row)
	
	def write(self, stream, tableMagic, tableName):
		columnStream = io.BytesIO()
		rowStream = io.BytesIO()
		stringStream = io.BytesIO()
		dataStream = io.BytesIO()
		
		stringIndices = {}
		def addString(string):
			if string not in stringIndices:
				stringIndices[string] = len(stringStream.getbuffer())
				stringStream.write(string.encode('utf-8') + bytes(1))
			return stringIndices[string]
		
		def addData(data):
			index = len(dataStream.getbuffer())
			dataStream.write(data)
			if len(dataStream.getbuffer()) % 8 > 0:
				dataStream.write(bytearray(8 - (len(dataStream.getbuffer()) % 8)))
			return index
		
		def writeCell(dataType, value):
			if dataType == UtfTable.UtfDatumType.int8:
				rowStream.write(struct.pack('> B', value))
			elif dataType == UtfTable.UtfDatumType.int16:
				rowStream.write(struct.pack('> H', value))
			elif dataType == UtfTable.UtfDatumType.int32:
				rowStream.write(struct.pack('> I', value))
			elif dataType == UtfTable.UtfDatumType.int64:
				rowStream.write(struct.pack('> Q', value))
			elif dataType == UtfTable.UtfDatumType.float32:
				rowStream.write(struct.pack('> f', value))
			elif dataType == UtfTable.UtfDatumType.string:
				rowStream.write(struct.pack('> I', addString(value)))
			elif dataType == UtfTable.UtfDatumType.bytestring:
				rowStream.write(struct.pack('> II', addData(value), len(value)))
			else:
				print("Unknown data type: %s" % dataType)
		
		tableNameID = addString(tableName)
		
		storageTypes = {}
		rowLength = 0
		for column in self.columns:
			if len(self.rows) == 1 and self.rows[0][column.name] is None:
				storageType = UtfTable.UtfDatumStorage.null
			else:
				storageType = UtfTable.UtfDatumStorage.variable
				rowLength += UtfTable.datumSizes[column.datumType]
			storageTypes[column.name] = storageType
			
			flags = storageType << 4 | column.datumType
			nameIndex = addString(column.name)
			columnStream.write(struct.pack('> B I', flags, nameIndex))
		
		for row in self.rows:
			for column in self.columns:
				if storageTypes[column.name] == UtfTable.UtfDatumStorage.variable:
					writeCell(column.datumType, row[column.name])
		
		columnBuffer = columnStream.getbuffer()
		rowBuffer = rowStream.getbuffer()
		stringBuffer = stringStream.getbuffer()
		dataBuffer = dataStream.getbuffer()
		
		columnOffset = 32
		rowOffset = columnOffset + len(columnBuffer)
		stringOffset = rowOffset + len(rowBuffer)
		stringPaddingOffset = stringOffset + len(stringBuffer)
		if stringPaddingOffset % 8 > 0:
			stringPadding = bytes(8 - (stringPaddingOffset % 8))
		else:
			stringPadding = bytes(0)
		dataOffset = stringPaddingOffset + len(stringPadding)
		dataEnd = dataOffset + len(dataBuffer)
		
		header = struct.pack('> 4s IIII IHHI',
			'@UTF'.encode('utf-8'),
			dataEnd - 8,
			rowOffset - 8,
			stringOffset - 8,
			dataOffset - 8,
			tableNameID,
			len(self.columns),
			rowLength,
			len(self.rows),
		)
		
		plaintextBuffer = header + columnBuffer + rowBuffer + stringBuffer + stringPadding + dataBuffer
		encryptedBuffer = struct.pack('< 4s I Q', tableMagic.encode('utf-8'), 0, len(plaintextBuffer)) + UtfTable.crypt(plaintextBuffer)
		write(stream, encryptedBuffer)
		
		return len(encryptedBuffer)


class CpkReader:
	class FileEntry:
		def __init__(self, name, size, offset, modificationTime, compressedSize):
			self.name = name
			self.size = size
			self.offset = offset
			self.modificationTime = modificationTime
			self.compressedSize = compressedSize
	
	def __init__(self):
		self.stream = None
		self.files = []
	
	def open(self, filename):
		self.close()
		self.stream = open(filename, 'rb')
		self.files = []
		
		headerTable = UtfTable()
		headerTable.read(self.stream, 0, 'CPK ')
		headerFields = headerTable.rows[0]
		
		if 'ContentOffset' not in headerFields:
			raise DecodeError("Missing content offset")
		contentOffset = headerFields['ContentOffset']
		
		if 'TocOffset' not in headerFields:
			raise DecodeError("Missing table of contents")
		tocOffset = headerFields['TocOffset']
		tocTable = UtfTable()
		tocTable.read(self.stream, tocOffset, 'TOC ')
		
		etocTable = None
		if 'EtocOffset' in headerFields:
			etocOffset = headerFields['EtocOffset']
			if etocOffset is not None:
				etocTable = UtfTable()
				etocTable.read(self.stream, etocOffset, 'ETOC')
				if 'UpdateDateTime' not in [column.name for column in etocTable.columns]:
					etocTable = None
		
		tocRows = [column.name for column in tocTable.columns]
		for row in ['DirName', 'FileName', 'FileSize', 'FileOffset', 'ExtractSize']:
			if row not in tocRows:
				raise DecodeError("Incomplete table of contents")
		
		# The actual offset used by libcpk seems to be hardcoded as 0x800,
		# and ignores ContentOffset entirely.
		effectiveContentOffset = 0x800
		for row in tocTable.rows:
			name = row['DirName'].replace('\\', '/').rstrip('/') + '/' + row['FileName'].replace('\\', '/').lstrip('/')
			
			if 'ID' in row and row['ID'] is not None and etocTable is not None and row['ID'] < len(etocTable.rows):
				encodedModificationTime = etocTable.rows[row['ID']]['UpdateDateTime']
				modificationTime = datetime.datetime(
					encodedModificationTime >> 48 & 0xffff,
					encodedModificationTime >> 40 & 0xff,
					encodedModificationTime >> 32 & 0xff,
					encodedModificationTime >> 24 & 0xff,
					encodedModificationTime >> 16 & 0xff,
					encodedModificationTime >>  8 & 0xff,
				)
			else:
				modificationTime = None
			
			self.files.append(CpkReader.FileEntry(name, row['ExtractSize'], row['FileOffset'] + effectiveContentOffset, modificationTime, row['FileSize']))
	
	def close(self):
		if self.stream is not None:
			self.stream.close()
			self.stream = None
	
	def readFile(self, entry):
		self.stream.seek(entry.offset, 0)
		content = read(self.stream, entry.compressedSize)
		
		if entry.size != entry.compressedSize and len(content) >= 16 and content[0:8] == b'CRILAYLA':
			return decompressCrilayla(content)
		
		return content

class CpkWriter:
	class FileEntry:
		def __init__(self, size, offset, modificationTime):
			self.size = size
			self.offset = offset
			self.modificationTime = modificationTime
	
	def __init__(self):
		self.stream = None
		self.alignment = None
		self.position = None
		self.files = {}
	
	def open(self, filename, alignment = 0x800):
		self.alignment = alignment
		self.stream = open(filename, 'wb')
		self.files = {}
		
		self.position = 0x800
		write(self.stream, bytes(self.position - 6))
		write(self.stream, "(c)CRI".encode('utf-8'))
	
	def close(self):
		toc = UtfTable()
		toc.columns.append(UtfTable.Column("DirName", UtfTable.UtfDatumType.string))
		toc.columns.append(UtfTable.Column("FileName", UtfTable.UtfDatumType.string))
		toc.columns.append(UtfTable.Column("FileSize", UtfTable.UtfDatumType.int32))
		toc.columns.append(UtfTable.Column("ExtractSize", UtfTable.UtfDatumType.int32))
		toc.columns.append(UtfTable.Column("FileOffset", UtfTable.UtfDatumType.int64))
		toc.columns.append(UtfTable.Column("ID", UtfTable.UtfDatumType.int32))
		toc.columns.append(UtfTable.Column("UserString", UtfTable.UtfDatumType.string))
		
		etoc = UtfTable()
		etoc.columns.append(UtfTable.Column("UpdateDateTime", UtfTable.UtfDatumType.int64))
		etoc.columns.append(UtfTable.Column("LocalDir", UtfTable.UtfDatumType.string))
		
		totalSize = 0
		for filename in sorted(list(self.files.keys()), key = lambda x: x.upper()):
			pos = filename.rfind('/')
			if pos == -1:
				entryDirName = ''
				entryFileName = filename
			else:
				entryDirName = filename[0:pos]
				entryFileName = filename[pos + 1:]
			entry = self.files[filename]
			
			toc.rows.append({
				"DirName": entryDirName,
				"FileName": entryFileName,
				"FileSize": entry.size,
				"ExtractSize": entry.size,
				"FileOffset": entry.offset - 0x800,
				"ID": len(toc.rows),
				"UserString": "",
			})
			
			if entry.modificationTime is not None:
				etoc.rows.append({
					"UpdateDateTime": (
						entry.modificationTime.year << 48 |
						entry.modificationTime.month << 40 |
						entry.modificationTime.day << 32 |
						entry.modificationTime.hour << 24 |
						entry.modificationTime.minute << 16 |
						entry.modificationTime.second << 8 |
						0 << 0
					),
					"LocalDir": entryDirName,
				})
			
			totalSize += entry.size
		
		tocPosition = self.position
		tocSize = toc.write(self.stream, 'TOC ', 'CpkTocInfo')
		self.position += tocSize
		
		if len(etoc.rows) == len(toc.rows):
			if tocSize % self.alignment > 0:
				tocPadding = self.alignment - (tocSize % self.alignment)
				write(self.stream, bytes(tocPadding))
				self.position += tocPadding
			
			etoc.rows.append({
				"UpdateDateTime": 0,
				"LocalDir": "",
			})
			etocPosition = self.position
			etocSize = etoc.write(self.stream, 'ETOC', 'CpkEtocInfo')
		else:
			etocPosition = None
			etocSize = None
		
		header = UtfTable()
		header.rows.append({})
		def addHeader(key, value, type):
			header.columns.append(UtfTable.Column(key, type))
			header.rows[0][key] = value
		
		addHeader("UpdateDateTime", 1, UtfTable.UtfDatumType.int64)
		addHeader("FileSize", None, UtfTable.UtfDatumType.int64)
		addHeader("ContentOffset", 0x800, UtfTable.UtfDatumType.int64)
		addHeader("ContentSize", tocPosition - 0x800, UtfTable.UtfDatumType.int64)
		addHeader("TocOffset", tocPosition, UtfTable.UtfDatumType.int64)
		addHeader("TocSize", tocSize, UtfTable.UtfDatumType.int64)
		addHeader("TocCrc", None, UtfTable.UtfDatumType.int32)
		addHeader("HtocOffset", None, UtfTable.UtfDatumType.int64)
		addHeader("HtocSize", None, UtfTable.UtfDatumType.int64)
		addHeader("EtocOffset", etocPosition, UtfTable.UtfDatumType.int64)
		addHeader("EtocSize", etocSize, UtfTable.UtfDatumType.int64)
		addHeader("ItocOffset", None, UtfTable.UtfDatumType.int64)
		addHeader("ItocSize", None, UtfTable.UtfDatumType.int64)
		addHeader("ItocCrc", None, UtfTable.UtfDatumType.int32)
		addHeader("GtocOffset", None, UtfTable.UtfDatumType.int64)
		addHeader("GtocSize", None, UtfTable.UtfDatumType.int64)
		addHeader("GtocCrc", None, UtfTable.UtfDatumType.int32)
		addHeader("HgtocOffset", None, UtfTable.UtfDatumType.int64)
		addHeader("HgtocSize", None, UtfTable.UtfDatumType.int64)
		addHeader("EnabledPackedSize", totalSize, UtfTable.UtfDatumType.int64)
		addHeader("EnabledDataSize", totalSize, UtfTable.UtfDatumType.int64)
		addHeader("TotalDataSize", None, UtfTable.UtfDatumType.int64)
		addHeader("Tocs", None, UtfTable.UtfDatumType.int32)
		addHeader("Files", len(self.files), UtfTable.UtfDatumType.int32)
		addHeader("Groups", 0, UtfTable.UtfDatumType.int32)
		addHeader("Attrs", 0, UtfTable.UtfDatumType.int32)
		addHeader("TotalFiles", None, UtfTable.UtfDatumType.int32)
		addHeader("Directories", None, UtfTable.UtfDatumType.int32)
		addHeader("Updates", None, UtfTable.UtfDatumType.int32)
		addHeader("Version", 7, UtfTable.UtfDatumType.int16)
		addHeader("Revision", 14, UtfTable.UtfDatumType.int16)
		addHeader("Align", self.alignment, UtfTable.UtfDatumType.int16)
		addHeader("Sorted", 1, UtfTable.UtfDatumType.int16)
		addHeader("EnableFileName", 1, UtfTable.UtfDatumType.int16)
		addHeader("EID", None, UtfTable.UtfDatumType.int16)
		addHeader("CpkMode", 1, UtfTable.UtfDatumType.int32)
		addHeader("Tvers", "pes-file-tools", UtfTable.UtfDatumType.string)
		addHeader("Comment", "", UtfTable.UtfDatumType.string)
		addHeader("Codec", 0, UtfTable.UtfDatumType.int32)
		addHeader("DpkItoc", 0, UtfTable.UtfDatumType.int32)
		addHeader("EnableTocCrc", 0, UtfTable.UtfDatumType.int16)
		addHeader("EnableFileCrc", 0, UtfTable.UtfDatumType.int16)
		addHeader("CrcMode", 0, UtfTable.UtfDatumType.int32)
		addHeader("CrcTable", bytes(0), UtfTable.UtfDatumType.bytestring)
		
		self.stream.seek(0)
		header.write(self.stream, 'CPK ', 'CpkHeader')
		self.stream.close()
	
	def writeFile(self, filename, content, modificationTime = None):
		if filename in self.files:
			return False
		
		self.files[filename] = CpkWriter.FileEntry(len(content), self.position, modificationTime)
		if len(content) % self.alignment > 0:
			paddingLength = self.alignment - (len(content) % self.alignment)
		else:
			paddingLength = 0
		write(self.stream, content)
		write(self.stream, bytearray(paddingLength))
		self.position += len(content) + paddingLength
		return True
