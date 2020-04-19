import os, sys
BASE = os.path.normpath(os.path.abspath(__file__) + "/../../../../")
NOTHING = object()
from libparsing import Processor
from tlang.tree.model import Node

try:
	from texto.main import run as texto
except ImportError as e:
	texto = None

class SourceProcessor(Processor):

	def postProcess( self, match, result ):
		if isinstance(result, Node):
			result.meta("offset", match.offset)
			result.meta("length", match.length)
			result.meta("line",   match.line)
		return result

# -----------------------------------------------------------------------------
#
# PARSER UTILS
#
# -----------------------------------------------------------------------------

class ParserUtils:

	@classmethod
	def EnsureSymbols( cls, grammar, tokens=None, words=None, groups=None ):
		"""Adds the given tokens, words and groups to the given grammar if
		they are not defined, returning the symbols."""
		g = grammar
		s = grammar.symbols
		if tokens:
			for k,v in tokens.items():
				if not hasattr(s,k): g.token(k,v)
		if words:
			for k,v in words.items():
				if not hasattr(s,k): g.word(k,v)
		if groups:
			for k in groups:
				if not hasattr(s,k): g.group(k)
		return g.symbols

	@classmethod
	def ParseString( cls, grammarFactory, text:str, isVerbose=False, processor=None ):
		"""Parses the given string using the grammar returned by the grammar factory."""
		g = grammarFactory(isVerbose=isVerbose)
		result = g.parseString(text)
		if not processor:
			return result
		elif result.isSuccess():
			return processor.process(result)
		else:
			raise Exception("Parsing failed: {0}".format(result.describe()))

	@classmethod
	def ParseFile( cls, grammarFactory, path:str, isVerbose=False, processor=None ):
		with open(path, "rt") as f:
			return cls.ParseString(grammarFactory, f.read(), isVerbose, processor)

	@classmethod
	def ParseMain( cls, grammarFactory, processor, args=None, output=sys.stdout ):
		args = args or sys.argv[1:]
		res = []
		for arg in args:
			if os.path.exists(arg):
				result = cls.ParseFile(grammarFactory, arg, True, processor=False)
			else:
				result = cls.ParseString(grammarFactory, arg, True, processor=False)
			res.append(result)
			if output:
				if not result.isSuccess():
					output.write (result.describe())
				else:
					output.write (str(processor.process(result)))
		return res


	@staticmethod
	def Indent (element, context):
		indent=(context.get('indent') or 0)
		context.set('indent', (indent + 1))

	@staticmethod
	def Dedent (element, context):
		self=__module__
		indent=(context.get('indent') or 0)
		context.set('indent', (indent - 1))

	@staticmethod
	def CheckIndent ( element, context, min=None):
		if min is None: min = False
		indent = context.get("indent") or 0
		o      = context.offset or 0
		so     = max(o - indent, 0)
		eo     = o
		tabs   = 0
		# This is a fix
		if so == eo and so > 0:
			so = eo
		for i in range(so, eo):
			if context[i] == b"\t":
				tabs += 1
		return tabs == indent

# -----------------------------------------------------------------------------
#
# TEST UTILS
#
# -----------------------------------------------------------------------------

class TestUtils:
	"""A collection of utility methods to help run tests using the
	documentation as a data source for the tests."""

	@classmethod
	def GetExamples( cls, name, type ):
		assert texto, "The 'texto' Python module is not availabled, but is required"
		path = os.path.join(BASE, "docs", name)
		res  = []
		with open(path) as f:
			status, xmltree = texto(["-Odom"], f, noOutput=True)
			for node in xmltree.getElementsByTagName("pre"):
				if not node.getAttribute("data-lang") == type: continue
				res.append("\n".join(_.data for _ in node.childNodes))
		return res

	@classmethod
	def AssertParsingResult( cls, result, i=0 ):
		if result.isFailure():
			raise Exception("Test {0} failed: {1}".format(i, result.describe()))
		elif result.isPartial():
			raise Exception("Test {0} failed: {1}".format(i, result.describe()))
		elif result.isSuccess():
			return True
		else:
			raise Exception("Unknown status: {0}". format(result.status))

	@classmethod
	def ParseExamples( cls, name, type, parseString ):
		"""Ensures that the examples in the documentation compile properly"""
		# We run through the examples and make sure they all compile
		for i,example in enumerate(cls.GetExamples(name, type)):
			cls.AssertParsingResult(parseString(example, process=False), i)

	@classmethod
	def ParseLines( cls, text, parseString ):
		i = 0
		for q in text.split("\n"):
			q = q.strip()
			if not q: continue
			cls.AssertParsingResult(parseString(q, process=False), i)
			i += 1

	@classmethod
	def ReparseExamples( cls, name, type, parseString ):
		"""Ensures that the output of a parsed element is parseable and generates
		the exact same tree."""
		for i,example in enumerate(cls.GetExamples(name, type)):
			source_repr   = "\n".join(str(_) for _ in parseString(example))
			reparsed_repr = "\n".join(str(_) for _ in parseString(source_repr))
			assert source_repr == reparsed_repr

# EOF - vim: ts=4 sw=4 noet
