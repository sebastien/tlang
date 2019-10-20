#!/usr/bin/env python3.8
from tlang import tree
import re, sys, os
from typing import Optional,Any
from collections import OrderedDict

class Parser:
	"""The TDoc parser is implemented as a straightforward line-by-line
	parser with an event-based (SAX-like) interface."""

	DATA_NODE    = 1
	DATA_ATTR    = 2
	DATA_CONTENT = 3
	DATA_RAW     = 4

	NAME    = "[A-Za-z0-9\-_]+"
	ATTR    = f"{NAME}=[^ ]*"
	STR_SQ  = "'(\\'|[^'])+'"
	STR_DQ  = '"(\\"|[^"])+"'
	VALUE   = f"([^ ]+|{STR_SQ}|{STR_DQ})"
	RE_ATTR = re.compile(f" (?P<name>{NAME})=(?P<value>{VALUE})?")
	RE_NODE = re.compile(f"^((?P<ns>{NAME}):)?(?P<name>{NAME})(\|(?P<parser>{NAME}))?(?P<attrs>( {ATTR})*)?(: (?P<content>.*))?$")

	def __init__( self, driver=None ):
		self.customParser:Optional[str] = None
		self.customParserLevel:Optional[int] = None
		self.driver = driver or ADriver()
		self.level = 0

	def start( self ):
		"""The parser is stateful, and `start` initializes its state."""
		self.customParser = None
		self.customParserLevel = None
		self.level = 0
		self.driver.onDocumentStart()

	def end( self ):
		self.driver.onDocumentEnd()

	def feed( self, line:str ):
		"""Freeds a line into the parser, which produces a directive for
		the driver and may affect the state of the parser."""
		i = 0
		n = len(line)
		while i < n and line[i] == '\t':
			i += 1
		l = line[i:] if i>0 else line
		if self.customParser:
			if i > self.customParserLevel:
				return self.driver.onRaw(line[self.customParserLevel + 1:])
			else:
				self.customParser = None
				self.customParserLevel = None
		if self.isComment(l):
			return self.driver.onComment(l[1:])
		elif self.isAttribute(l):
			ns, name, value = self.parseAttributeLine(l)
			return self.driver.onAttribute(ns, name, value)
		elif m := self.isNode(l):
			print ("LEVEL", self.level, "/", i)
			if i <= self.level:
				while self.level > i:
					self.driver.onNodeEnd()
					self.level -= 1
			elif i > self.level + 1:
				return self.onContent(line[self.level:])
			else:
				assert i == self.level
				self.driver.onNodeEnd()
			ns, name, parser, attr, content = self.parseNodeLine(l, m)
			self.level = i
			if parser:
				self.customParser = r["parser"]
				self.customParserLevel = i
			res = self.driver.onNodeStart(ns, name, parser)
			for ns, name, value in attr:
				self.driver.onAttribute(ns, name, value)
			if content is not None:
				self.driver.onContent(content)
			return res
		else:
			return self.driver.onContent(l)

	def isComment( self, line:str ) -> bool:
		return line and line[0] == "#"

	def isNode( self, line:str ) -> bool:
		"""Tells if this line is node line"""
		return self.RE_NODE.match(line)

	def isAttribute( self, line:str ) -> bool:
		"""Tells if this line is attribute line"""
		return line and line[0] == '@'

	def parseNodeLine( self, line, match):
		return (
			match.group("ns"),
			match.group("name"),
			match.group("parser"),
			(_ for _ in self.parseAttributes(match.group("attrs"))),
			match.group("content"),
		)

	def parseAttributes( self, line ):
		# Inline attributes are like
		#   ATTR=VALUE ATTR=VALUE…
		# Where value can be unquoted, single quoted or double quoted,
		# with \" or \' to escape quotes.
		n = len(line)
		o = 0
		while m := self.RE_ATTR.match(line, o):
			v = m.group("value")
			# This little dance corrects the string escaping
			if len(v) < 2:
				w = v
			else:
				s = v[0]
				e = v[-1]
				if s != e:
					w = v
				elif s == '"':
					w = v[1:-1].replace('\\"', '"')
				elif s == "'":
					w = v[1:-1].replace("\\'", "'")
				else:
					w = v
			yield (m.group("name"), w)
			o = m.end()

	def parseAttributeLine( self, line ):
		# Attributes are like
		#   @NAME VALUE
		# or
		#   @NS:NAME VALUE
		name_value = line.split(' ', 1)
		name         = name_value[0][1:]
		ns_name      = name.split(':', 1)
		if len(ns_name) == 1:
			ns = None
		else:
			ns, name = ns_name
		content = name_value[1] if len(name_value) == 2 else None
		return (ns, name, name)

class ADriver:

	def onDocumentStart( self ):
		pass

	def onDocumentEnd( self ):
		pass

	def onNodeStart( self, ns:Optional[str], name:str, process:Optional[str] ):
		print (f"<{ns or '*'}:{name} ")

	def onNodeEnd( self ):
		print (f"/>")

	def onAttribute( self, ns:Optional[str], name:str, value:Optional[str] ):
		print (f"@{ns or '*'}:{name} {value}")

	def onContent( self, text:str ):
		print (f"→{text}")

	def onRaw( self, text:str ):
		print (f"R{text}")

	def onComment( self, text:str ):
		print (f"#{text}")

class TLangDriver(ADriver):
	pass


def parseString( text:str ):
	p = Parser()
	p.start()
	for line in text.split("\n"):
		p.feed(line)
	p.end()

if __name__ == "__main__":
	path = sys.argv[1]
	text = open(path).read() if os.path.exists(path) else path
	print (parseString(text))

# EOF - vim: ts=4 sw=4 noet
