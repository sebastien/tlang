#!/usr/bin/env python3.8
from tlang import tree
import re, sys, os, logging
from typing import Optional,Any,List
from collections import OrderedDict,namedtuple

# TODO: The parser should yield its position (line, column) and a value
# being either Skip, string, Warning, or Error

# TODO: Options

# TODO: Whitespace:
# - preserve: as-is (EOL between tags)
# - normalize: all become spaces

# -----------------------------------------------------------------------------
#
# PARSER
#
# -----------------------------------------------------------------------------

ParseOption = namedtuple("ParseOption", ("type", "default", "help"))
class ParseOptions:
	"""Define options for parsers, readers and writers."""

	OPTIONS = {
		"comments"   : ParseOption(bool         , True , "Includes comments in the output"),
		"embed"      : ParseOption(bool         , False, "Turns on embedded mode"),
		"embedLine"  : ParseOption(Optional[str], None , "Line prefix for embedded TDoc data (eg. '#')"),
		"embedStart" : ParseOption(Optional[str], None , "Start of embedded TDoc data (eg. '/*')"),
		"embedEnd"   : ParseOption(Optional[str], None , "End of embedded TDoc data (eg. '*/')"),
	}

	def __init__( self, options=None ):
		self.options = {}
		self.merge(options)

	def merge( self, options ):
		if options:
			for k,v in options.items():
				if k in self.OPTIONS:
					setattr(self, k, v)
		return self

	def __getattr__( self, name ):
		if name in ("options", "OPTIONS"):
			return object.__getattribute__(self, name)
		elif name not in self.OPTIONS:
			raise ValueError(f"No option {name}, pick any of {tuple(self.OPTIONS.keys())}")
		else:
			return self.options[name] if name in self.options else self.OPTIONS[name]

	def __setattr__( self, name, value ):
		if name in ("options", "OPTIONS"):
			object.__setattr__(self, name, value)
		elif name not in self.OPTIONS:
			raise ValueError(f"No option {name}, pick any of {tuple(self.OPTIONS.keys())}")
		else:
			expected_type = self.OPTIONS[name][0]
			# FIXME: We should test using generics
			if False and not isinstance(value, expected_type):
				raise ValueError(f"Option {name} should be {expected_type}, got {type(value)}: {value}")
			else:
				self.options[name] = value

	def __repr__( self ):
		return repr(self.options)

class ParseError:
	"""Define a parse error, that can be relayed by the writer."""

	def __init__( self, line:int, char:int, message:str, length:int=0 ):
		self.line = line
		self.char = char
		self.message = message
		self.length = length

	def __str__( self ):
		return f"Syntax error at {self.line}:{self.char}: {self.message}"

class Parser:
	"""The TDoc parser is implemented as a straightforward line-by-line
	parser with an event-based (SAX-like) interface.

	The parser uses iterable consistently as an abstraction over multiple
	sources and makes it possible to pause/resume parsing.
	"""

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


	def __init__( self, options:ParseOptions ):
		self.customParser:Optional[str] = None
		self.customParserLevel:Optional[int] = None
		self.options = options
		self.depth = 0
		self.nodeCount = 0

	def parse( self, iterable, driver:"Driver" ):
		yield from self.start(driver)
		for line in iterable:
			yield from self.feed(line, driver)
		yield from self.end(driver)

	def start( self, driver:"Driver" ):
		"""The parser is stateful, and `start` initializes its state."""
		self.nodeCount    = 0
		self.customParser = None
		self.customParserLevel = None
		self.depth = -1
		yield from driver.onDocumentStart(self.options)

	def end( self, driver:"Driver"  ):
		yield from driver.onDocumentEnd()

	def feed( self, line:str, driver:"Driver"  ):
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
		if self.customParser:
			if i > self.customParserLevel:
				yield from driver.onRawContent(line[self.customParserLevel + 1:] + "\n")
				stopped = True
			elif not l:
				# This is an empty line, so we log it as an EOL
				yield from driver.onRawContent("\n")
			else:
				self.customParser = None
				self.customParserLevel = None
		if stopped:
			pass
		elif self.isComment(l):
			yield from driver.onComment(l[1:])
		elif self.isAttribute(l):
			ns, name, value = self.parseAttributeLine(l)
			yield from driver.onAttribute(ns, name, value)
		elif m := self.isNode(l):
			if i > self.depth + 1:
				yield from self.onContent(line[self.depth:])
			else:
				if i < self.depth:
					while self.depth > i:
						yield from driver.onNodeEnd()
						self.depth -= 1
				if i == self.depth:
					# The first node has self.depth == 0 == i, but there
					# is no previous node.
					if self.nodeCount > 0:
						yield from driver.onNodeEnd()
				else:
					assert i == self.depth + 1
				if not stopped:
					ns, name, parser, attr, content = self.parseNodeLine(l, m)
					self.depth = i
					if parser:
						self.customParser = m["parser"]
						self.customParserLevel = i
					self.nodeCount += 1
					yield from driver.onNodeStart(ns, name, parser)
					for ns, name, value in attr:
						yield from driver.onAttribute(ns, name, value)
					if content is not None:
						yield from driver.onContent(content)
		elif self.isExplicitContent(l):
			yield from driver.onContent(l[1:])
		else:
			yield from driver.onContent(line[self.depth + 1:])

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
	"""An abstract interface for the parser driver. The driver yields
	values that are then handled by a writer. In other words, it transforms
	the stream of events produced by the parser in a stream of values to
	be written."""

	@classmethod
	def GetDefault( cls ):
		return XMLDriver()

	def __init__( self ):
		self.options = None

	def onDocumentStart( self, options:ParseOptions ):
		self.options = options
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

	RE_CDATA  = re.compile("\<|\>")
	StackItem = namedtuple("StackItem", ("node"))

	def __init__( self ):
		super().__init__()
		self.reset()

	def reset( self ):
		# Stores the current node, if any
		self.node:Optional[str] = None
		# We use a list of content strings that we need to flush
		# as soon
		self.content:List[str] = []
		self.isContentCDATA = False
		# The stack is used to do the closing tags on document end.
		self.stack:List[XMLDriver.StackItem] = []

	# =========================================================================
	# HANDLERS
	# =========================================================================

	def onDocumentStart( self, options:ParseOptions ):
		yield from super().onDocumentStart(options)
		self.reset()
		yield '<?xml version="1.0"?>\n'

	def onDocumentEnd( self ):
		yield from self.flushContent()
		while self.stack:
			yield f"</{self.stack.pop().node}>"

	def onNodeStart( self, ns:Optional[str], name:str, process:Optional[str] ):
		yield from self.flushContent()
		# We need to handle child nodes
		self.node = f"{ns}:{name}" if ns else f"{name}"
		self.stack.append(XMLDriver.StackItem(self.node))
		yield f"<{self.node}"

	def onNodeEnd( self ):
		yield from self.flushContent()
		yield (f"</{self.node}>")
		self.stack.pop()

	def onAttribute( self, ns:Optional[str], name:str, value:Optional[str] ):
		svalue = '"' + value.replace('"', '\\"') + '"'
		attr   =  f" {ns}:{name}={svalue}" if ns else f" {name}={svalue}"
		if not self.content:
			yield attr
		else:
			# TODO: Should yield an error
			logging.warn(f"XMLDriver: Can't output attribute after content: {attr}")

	def onAttributesEnd( self ):
		yield '>'

	def onContent( self, text:str, type:int=0 ):
		if not self.isContentCDATA and self.RE_CDATA.search(text):
			self.isContentCDATA = True
		self.content.append((type,text))
		yield None

	def onRawContent( self, text:str ):
		yield from self.onContent(text, 1)

	def onComment( self, text:str ):
		yield from self.flushContent()
		if self.options.comments:
			yield (f"<!-- {text} -->\n")

	# =========================================================================
	# HELPERS
	# =========================================================================

	def flushContent( self ):
		"""We need to defer the processingof text content to properly
		do escapes and CDATA detection."""
		if self.content:
			is_cdata = self.isContentCDATA
			if is_cdata:
				yield "<[CDATA[["
			for i,(t, line) in enumerate(self.content):
				yield ">" if i == 0 else ("" if t == 1 else "\n")
				yield line
			if is_cdata:
				yield "]]>"
			self.content = []
			self.isContentCDATA = None

# -----------------------------------------------------------------------------
#
# WRITER 
#
# -----------------------------------------------------------------------------

class Writer:
	"""A default writer that writes content to an output stream (stdout by
	default)."""

	def __init__( self, stream=sys.stdout ):
		self.out = stream

	def write( self, iterable ):
		"""Writes the iterable elements to the output stream."""
		for _ in iterable:
			if _ is None:
				pass
			elif isinstance(_, str):
				self.out.write(_)
			elif isinstance(_, ParseError):
				logging.error(str(_))

class NullWriter(Writer):
	"""A writer useful for debugging."""

	def _write( self, iterable ):
		for _ in iterable:
			pass

# -----------------------------------------------------------------------------
#
# READER
#
# -----------------------------------------------------------------------------

class EmbeddedReader:
	"""Extracts TDoc content from a text file, wrapping the primary
	content in TDoc preformatted nodes."""

	# TODO: Start, Line and end (from options)
	def __init__( self, comment="#", line="code|tdoc"):
		self.comment = comment
		self.line = line
		self.shebang = "#!"

	def read( self, iterable ):
		in_content = False
		for i,line in enumerate(iterable):
			if i == 0 and line.startswith(self.shebang):
				pass
			elif line.startswith(self.comment):
				in_content = False
				yield line[len(self.comment):]
			elif not in_content:
				yield self.line
				yield f"\t{line}"
				in_content = True
			else:
				yield f"\t{line}"

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

def parseIterable( iterable, out=sys.stdout, options=ParseOptions(), driver=Driver.GetDefault() ):
	if options.embed:
		iterable = (EmbeddedReader().read(_ for _ in iterable))
	return Writer(out).write(Parser(options).parse(iterable, driver))

def parseString( text:str, out=sys.stdout, options=ParseOptions(), driver=Driver.GetDefault() ):
	with open(path) as f:
		return parseIterable( (_[:-1] for _ in text.split("\n")), out=out, options=options, driver=driver)

def parsePath( path:str, out=sys.stdout, options=ParseOptions(), driver=Driver.GetDefault() ):
	with open(path) as f:
		return parseIterable( f.readlines(), out=out, options=options, driver=driver)

if __name__ == "__main__":
	path = sys.argv[1]
	text = open(path).read() if os.path.exists(path) else path

# EOF - vim: ts=4 sw=4 noet
