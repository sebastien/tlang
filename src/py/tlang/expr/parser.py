from libparsing import Grammar, Symbols, Processor, ensure_string
from typing import Optional
from tlang.utils import ParserUtils
from tlang.tree.model import TreeBuilder
import sys, os

GRAMMAR = None

def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shared by all the grammars
	defined in this moddule."""
	s      = g.symbols
	tokens = {
		"WS"                      : "[\s\n]+",
		"NUMBER"                  : "[0-9]+(\.[0-9]+)?",
		"STRING_DQ"               : "\"([^\"]*)\"",
		"EXPR_NAME"               : "[a-z][\-a-z0-9]*[\!\?]?",
		"EXPR_VARIABLE"           : "[_A-Z][\_A-Z0-9]*",
		"EXPR_SYMBOL"             : ":[A-Za-z][\_a-zA-Z0-9]*",
		"EXPR_SINGLETON"          : "#[A-Za-z][\-a-zA-Z0-9]*[\!\?]?",
		"EXPR_KEY"                : "[A-Za-z][\_a-zA-Z0-9]*:",
		"EXPR_TYPE"               : "[A-Z][\_a-zA-Z0-9]*",
		"EXPR_COMMENT"            : ";;([^\n]*)",
		"REST"                    : "(\\.\\.\\.)|…",
	}
	words = {
		"LP"              : "(",
		"RP"              : ")",
		"COMMA"           : ",",
		"QUOTE"           : "'",
		"PIPE"            : "|",
		"EXPR_TEMPLATE"   : "${",
		"RB"              : "}",
	}
	groups = ()
	return ParserUtils.EnsureSymbols(g, tokens, words, groups)


def grammar(g:Optional[Grammar]=None, isVerbose=False) -> Grammar:
	"""Defines the grammar that parses grammar rule definitions."""
	global GRAMMAR
	if not g:
		if GRAMMAR:
			return GRAMMAR
		else:
			g=Grammar("expr", isVerbose=isVerbose)

	s = symbols(g)

	g.group("ExprValuePrefix")
	g.group("ExprComment",   s.EXPR_COMMENT)
	g.rule("ExprValue")
	g.rule("ExprTemplate"  , s.EXPR_TEMPLATE, s.ExprValue._as("value"), s.RB)

	g.rule("ExprList",       s.LP,    s.ExprValue._as("arg"),  s.RP)
	# NOTE: Here we want to avoid using `ExprValue` as otherwise we'll end up
	# with really deeply nested matches.
	g.rule("ExprQuote",      s.QUOTE, s.ExprValuePrefix._as("arg"))
	g.rule("ExprPipe",       s.PIPE,  s.ExprValuePrefix._as("arg"))
	g.rule("ExprJoin",       s.WS,    s.ExprValuePrefix._as("arg"))
	g.rule("ExprRest",       s.REST,  s.ExprValuePrefix._as("arg"))

	s.ExprValuePrefix.set(
		s.ExprList,              # 0
		s.ExprQuote,
		s.ExprTemplate,
		s.ExprComment,
		s.NUMBER,                # 5
		s.STRING_DQ,
		s.EXPR_SINGLETON,
		s.EXPR_KEY,
		# NOTE: Query is going to be inserted here #9
		s.EXPR_NAME,             # 10
		s.EXPR_SYMBOL,           # 11
		s.EXPR_VARIABLE,         # 12
		s.EXPR_TYPE,             # 13
	)
	g.group("ExprValueSuffix").set(
		s.ExprPipe,
		s.ExprRest,
		s.ExprJoin,
		s.ExprComment,
	)
	s.ExprValue.set(s.ExprValuePrefix._as("prefix"), s.ExprValueSuffix.zeroOrMore()._as("suffixes"), s.WS.zeroOrMore())

	g.axiom = s.ExprValue
	g.skip  = s.WS

	if not GRAMMAR:
		GRAMMAR = g
	g.setVerbose(isVerbose)
	return g

# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------

def sourcemap(f ):
	def decorator( self, match ):
		# TODO: This should be an option, ie. we don't necessarily want
		# that all the time
		node = f(self, match)
		node.meta("offset", match.offset)
		node.meta("length", match.length)
		node.meta("line",   match.line)
		return node
	return decorator

class ExprProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = cls()
		return cls.INSTANCE

	def __init__( self, grammar=None, strict=True ):
		Processor.__init__( self, grammar, strict )
		self.tree = TreeBuilder()

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

	@sourcemap
	def onNUMBER( self, match):
		value = float(self.process(match)[0])
		return self.tree.node("ex:number", {"value":value})

	@sourcemap
	def onSTRING_DQ( self, match):
		value = self.process(match)[1]
		return self.tree.node("ex:string", {"value":value})

	@sourcemap
	def onEXPR_SYMBOL( self, match):
		value = self.process(match)[0]
		# We strip the leading ":"
		return self.tree.node("ex:symbol", {"name":value[1:]})

	@sourcemap
	def onEXPR_NAME( self, match):
		value = self.process(match)[0]
		return self.tree.node("ex:ref", {"name":value})

	@sourcemap
	def onEXPR_SINGLETON( self, match):
		value = self.process(match)[0]
		return self.tree.node("ex:singleton", {"name":value})

	@sourcemap
	def onEXPR_KEY( self, match):
		value = self.process(match)[0]
		# We strip the trailing :
		return self.tree.node("ex:key", {"name":value[:-1]})

	@sourcemap
	def onEXPR_VARIABLE( self, match):
		value = self.process(match)[0]
		return self.tree.node("ex:ref", {"name":value})

	@sourcemap
	def onEXPR_TYPE( self, match):
		value = self.process(match)[0]
		return self.tree.node("ex:type", {"name":value})

	@sourcemap
	def onExprComment( self, match ):
		value = self.process(match)[0][1]
		return self.tree.node("ex:comment", {"value":value})

	def onExprValuePrefix( self, match ):
		return self.process(match)[0]

	def onExprValueSuffix( self, match ):
		return self.process(match[0])

	def onExprList( self, match, arg ):
		node = self.tree.node("ex:list")
		if arg.name == "ex:seq":
			node.merge(arg)
		else:
			if arg.parent:
				root = arg.root
				if root.name == "ex:seq":
					node.merge(root)
				else:
					node.add(root)
			else:
				node.add(arg)
		return node

	def onExprTemplate( self, match, value ):
		return self.tree.node("ex:template", value)

	def onExprJoin( self, match, arg ):
		# NOTE: The join suffix creates a sequence of values which
		# is denoted as a different type from list.
		if arg.name == "ex:seq":
			return arg
		else:
			if arg.parent:
				# If the arg is already attached, we should not change it.
				return arg
			else:
				node = self.tree.node("ex:seq")
				node.add(arg)
				return node

	def onExprRest( self, match, arg ):
		# FIXME: This is probably not right
		node = self.tree.node("ex:rest")
		node.add(arg)
		return node

	def onExprPipe( self, match, arg ):
		return self.tree.node("ex:pipe", arg)

	def onExprQuote( self, match, arg ):
		return self.tree.node("ex:quote", arg)

	# FIXME: Not sure what the difference between invocation and list
	# is in practice. Should be the same.
	def onExprValue( self, match, prefix, suffixes ):
		"""An `ExprValue` has a prefix and zero or more suffixes. The main
		challenge here is that the suffix might change the way the resulting
		value is constructed, for instance with `…` or `|`. This method takes
		care of constructing the resulting value appropriately."""
		# NOTE: This is where we manage priorities. We should define
		# more clearly what happens there.

		# The result is what we return, we start with the prefix, which
		# is pretty much always a straightforward value.
		# SEE: `s.ExprValuePrefix.set`
		result  = prefix

		# Now we're going to iterate through the suffixes, and switching the
		# result based on what suffix we have.
		for i,suffix in enumerate(suffixes):
			# NOTE: Arguably, these transformations would probably be
			# better explained/represented in TLang itself.
			prefix_name  = prefix.name
			suffix_name  = suffix.name
			# … VALUE (REST)
			if suffix_name == "ex:rest":
				if prefix_name != "ex:seq":
					# If the prefix is not a SEQ, then we wrap it in a sequence
					# as REST requires a SEQ.
					assert prefix is result
					prefix = self.tree.node("ex:seq", prefix)
					result = prefix
				# We have a … VALUE and the prefix is already
				# a SEQ, then we append the REST at the end of the SEQ,
				# and the REST becomes the new prefix/context.
				prefix.add(suffix)
				prefix  = suffix
			# <SPACE> VALUE (SEQ)
			elif suffix_name == "ex:seq":
				if prefix_name == "ex:rest" or prefix_name == "ex:seq":
					# If the SEQ is preceded by a REST or SEQ, then its
					# content is merged.
					prefix.merge(suffix)
				else:
					# Otherwise we inject the preceding value in the SEQ
					suffix.insert(0, prefix)
					prefix = suffix
					result = suffix
			# | VALUE (PIPE)
			elif suffix_name == "ex:pipe":
				if prefix_name != "ex:seq":
					prefix = self.tree.node("ex:seq", prefix)
				prefix.merge(suffix)
		return result

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

# TODO: move the core to to tlang.utils.GrammarUtils.parse{String|File|Main}(g,tokens,words,groups)
def parseString( text:str, isVerbose=False, process=True ):
	return ParserUtils.ParseString(grammar, text, isVerbose, processor=ExprProcessor.Get() if process else None)

def parseFile( path:str, isVerbose=False, process=True ):
	return ParserUtils.ParseFile(grammar, path, isVerbose, processor=ExprProcessor.Get() if process else None)

if __name__ == '__main__':
	ParserUtils.ParseMain(grammar, ExprProcessor.Get())

# EOF - vim: ts=4 sw=4 noet
