#!/usr/bin/env python3.8
from tlang import tree
import re, sys, os, logging
from typing import Optional,Any,List
from collections import OrderedDict,namedtuple

# TODO: The parser should yield its position (line, column) and a value
# being either Skip, string, Warning, or Error

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
		self.driver = driver or XMLDriver()
		self.depth = 0
		self.nodeCount = 0

	def start( self ):
		"""The parser is stateful, and `start` initializes its state."""
		self.nodeCount    = 0
		self.customParser = None
		self.customParserLevel = None
		self.depth = 0
		yield from self.driver.onDocumentStart()

	def end( self ):
		yield from self.driver.onDocumentEnd()

	def feed( self, line:str ):
		"""Freeds a line into the parser, which produces a directive for
		the driver and may affect the state of the parser."""
		i = 0
		n = len(line)
		while i < n and line[i] == '\t':
			i += 1
		l = line[i:] if i>0 else line
		# NOTE: We use stopped as a way to exit the loop early, as we're
		# using an iterator.
		stopped = False
		print ("LINE", self.customParser,":",repr(line))
		if self.customParser:
			if i > self.customParserLevel:
				yield from self.driver.onRawContent(line[self.customParserLevel + 1:] + "\n")
				stopped = True
			else:
				self.customParser = None
				self.customParserLevel = None
		if stopped:
			pass
		elif self.isComment(l):
			yield from self.driver.onComment(l[1:])
		elif self.isAttribute(l):
			ns, name, value = self.parseAttributeLine(l)
			yield from self.driver.onAttribute(ns, name, value)
		elif m := self.isNode(l):
			if i > self.depth + 1:
				yield from self.onContent(line[self.depth:])
			else:
				if i < self.depth:
					while self.depth > i:
						yield from self.driver.onNodeEnd()
						self.depth -= 1
				if i == self.depth:
					# The first node has self.depth == 0 == i, but there
					# is no previous node.
					if self.nodeCount > 0:
						yield from self.driver.onNodeEnd()
				else:
					assert i == self.depth + 1
				if not stopped:
					ns, name, parser, attr, content = self.parseNodeLine(l, m)
					self.depth = i
					if parser:
						self.customParser = m["parser"]
						self.customParserLevel = i
					self.nodeCount += 1
					yield from self.driver.onNodeStart(ns, name, parser)
					for ns, name, value in attr:
						yield from self.driver.onAttribute(ns, name, value)
					if content is not None:
						yield from self.driver.onContent(content)
		elif self.isExplicitContent(l):
			yield from self.driver.onContent(l[1:])
		else:
			yield from self.driver.onContent(l)

	# =========================================================================
	# PREDICATES
	# =========================================================================

	def isComment( self, line:str ) -> bool:
		return line and line[0] == "#"

	def isExplicitContent( self, line:str ) -> bool:
		return line and line[0] == ":"

	def isNode( self, line:str ) -> bool:
		"""Tells if this line is node line"""
		return self.RE_NODE.match(line)

	def isAttribute( self, line:str ) -> bool:
		"""Tells if this line is attribute line"""
		return line and line[0] == '@'

	# =========================================================================
	# SPECIFIC PARSERS
	# =========================================================================

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

# -----------------------------------------------------------------------------
#
# DRIVER
#
# -----------------------------------------------------------------------------

class Driver:

	def onDocumentStart( self ):
		yield None

	def onDocumentEnd( self ):
		yield None

	def onNodeStart( self, ns:Optional[str], name:str, process:Optional[str] ):
		yield None

	def onNodeEnd( self ):
		yield None

	def onAttribute( self, ns:Optional[str], name:str, value:Optional[str] ):
		yield None

	def onContent( self, text:str ):
		yield None

	def onRawContent( self, text:str ):
		yield None

	def onComment( self, text:str ):
		yield None

# -----------------------------------------------------------------------------
#
# XML DRIVER
#
# -----------------------------------------------------------------------------

class XMLDriver(Driver):
	"""A driver that emits an XML-serialized document (as a text string)."""

	StackItem = namedtuple("StackItem", ("node"))

	def __init__( self ):
		self.node = None
		self.stack:List[XMLDriver.StackItem] = []
		self.hasContent:Optional[bool] = None

	def onDocumentStart( self ):
		yield '<?xml version="1.0" ?>\n'

	def onDocumentEnd( self ):
		while self.stack:
			yield f"</{self.stack.pop().node}>"

	def onNodeStart( self, ns:Optional[str], name:str, process:Optional[str] ):
		# We need to handle child nodes
		if self.hasContent is False:
			yield ">"
		self.node = f"{ns}:{name}" if ns else f"{name}"
		self.hasContent = False
		self.stack.append(XMLDriver.StackItem(self.node))
		yield f"<{self.node}"

	def onNodeEnd( self ):
		yield (f"</{self.node}>")
		self.stack.pop()

	def onAttribute( self, ns:Optional[str], name:str, value:Optional[str] ):
		svalue = '"' + value.replace('"', '\\"') + '"'
		attr   =  f" {ns}:{name}={svalue}" if ns else f" {name}={svalue}"
		if not self.hasContent:
			yield attr
		else:
			# TODO: Should yield an error
			logging.warn(f"XMLDriver: Can't output attribute after content: {attr}")

	def onAttributesEnd( self ):
		yield '>'

	def onContent( self, text:str ):
		if self.hasContent is False:
			yield ">"
			self.hasContent = True
		yield text

	def onRawContent( self, text:str ):
		yield from self.onContent(text)

	def onComment( self, text:str ):
		yield (f"<!-- {text} -->\n")

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

# TODO: parseString and parsePath should have the same body
def parseString( text:str, out=sys.stdout ):
	p = Parser()
	for _ in p.start():
		out.write(_)
	for line in text.split("\n"):
		for _ in p.feed(line):
			out.write(_)
	for _ in p.end():
		out.write(_)

def parsePath( path:str, out=sys.stdout ):
	p = Parser()
	for _ in p.start():
		out.write(_)
	with open(path) as f:
		for line in f.readlines():
			for _ in p.feed(line[:-1]):
				out.write(_)
	for _ in p.end():
		out.write(_)

if __name__ == "__main__":
	path = sys.argv[1]
	text = open(path).read() if os.path.exists(path) else path
	print (parseString(text))

# EOF - vim: ts=4 sw=4 noet
