from libparsing import Grammar, Symbols, Processor, ensure_string
from typing import Optional
from tlang.rules.model import Format
from tlang.utils import ParserUtils
from tlang.tree.parser import grammar as tree_grammar
import sys, os

__doc__ = """
Defines a parser for the rule grammar, producing a Format model.
"""

GRAMMAR = None

# -----------------------------------------------------------------------------
#
# SYMBOLS
#
# -----------------------------------------------------------------------------

# TODO: move the core to to tlang.utils.GrammarUtils.symbols(g,tokens,words,groups)
def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shared by all the grammars
	defined in this moddule."""
	tokens = {
		"WS"           : "\s+",
		"FORMAT_NAME"    : "[A-Z][_A-Z]*",
		"FORMAT_VARIANT" : "\([A-Za-z][0-9A-Z\-a-z]*\)",
		"FORMAT_BINDING" : ":[A-Z][_A-Z]*",
		"FORMAT_COMMENT" : "\s*//[^\n]+",
		"TOKEN_RANGE"  : "\[((.)-(.)|\\-|[^\\]])+\]",
		"CARDINALITY"  : "[\?\*\+]",
		"STRING_SQ"    : "'[^']+'",
		"STRING_DQ"    : "\"[^\"]*\"",
		"EMPTY_LINE"   : "s*\n"
	}
	words = {
		"FORMAT_DEF"  : ":=",
		"FORMAT_END"  : ";",
		"FORMAT_PAT"  : "-->",
		"LP"        : "(",
		"RP"        : ")",
		"PIPE"      : "|",
		"UNDERSCORE": "_",
		"EOL"       : "\n",

	}
	groups = ("Tree",)
	return ParserUtils.EnsureSymbols(g, tokens, words, groups)

# -----------------------------------------------------------------------------
#
# GRAMMAR
#
# -----------------------------------------------------------------------------

def grammar(g:Optional[Grammar]=None, isVerbose=False) -> Grammar:
	"""Defines the grammar that parses grammar rule definitions."""
	global GRAMMAR
	if not g:
		if GRAMMAR:
			return GRAMMAR
		else:
			g=Grammar("format", isVerbose=isVerbose)
	g = tree_grammar(g)
	s = symbols(g)

	# Expressions
	g.group("FormatValue")
	g.rule ("FormatExpression")
	g.rule ("FormatReference"              , s.FORMAT_NAME             , s.FORMAT_BINDING.optional() , s.CARDINALITY.optional())
	g.rule ("FormatGroup"                  , s.LP                    , s.FormatExpression          , s.RP                      , s.CARDINALITY.optional())
	g.group("FormatTokenString"            , s.STRING_SQ             , s.STRING_DQ)
	g.rule ("FormatTokenRange"             , s.TOKEN_RANGE)
	g.group("FormatTokenValue"             , s.FormatTokenString       , s.FormatTokenRange)
	g.rule ("FormatToken"                  , s.FormatTokenValue        , s.CARDINALITY.optional())
	g.rule ("FormatExpressionOr"           , s.PIPE                  , s.FormatValue)
	g.rule ("FormatExpressionAnd"          , s.UNDERSCORE.optional() , s.FormatValue)
	g.group("FormatExpressionContinuation" , s.FormatExpressionOr      , s.FormatExpressionAnd)
	s.FormatValue.set( s.FormatToken, s.FormatGroup, s.FormatReference)
	s.FormatExpression.set(s.FormatValue, s.FormatExpressionContinuation.zeroOrMore ())

	# Statements
	g.rule("FormatPattern"    , s.EOL.optional(), s.FORMAT_PAT, s.Tree)
	g.rule("FormatDefinition" , s.FORMAT_NAME     , s.FORMAT_VARIANT.optional() , s.FORMAT_DEF , s.FormatExpression , s.FormatPattern.optional() , s.FORMAT_END)
	g.rule("FormatComment"    , s.FORMAT_COMMENT  , s.EOL)

	# Formats
	g.group("FormatStatement",
		s.FormatComment,
		s.FormatDefinition,
		s.EMPTY_LINE,
	)

	g.rule("Formats", s.FormatStatement.zeroOrMore())

	g.axiom = s.Formats
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

class FormatProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = FormatProcessor()
		return cls.INSTANCE

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

def sourcemap(f):
	def decorator( self, match, *args, **kwargs ):
		# TODO: This should be an option, ie. we don't necessarily want
		# that all the time
		node = f(self, match, *args, **kwargs)
		node.meta("offset", match.offset)
		node.meta("length", match.length)
		node.meta("line",   match.line)
		return node
	functools.update_wrapper(decorator, f)
	return decorator

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

# TODO: move the core to to tlang.utils.GrammarUtils.parse{String|File|Main}(g,tokens,words,groups)
def parseString( text:str, isVerbose=False, process=True ):
	return ParserUtils.ParseString(grammar, text, isVerbose, processor=FormatProcessor.Get() if process else None)

def parseFile( path:str, isVerbose=False, process=True ):
	return ParserUtils.ParseFile(grammar, path, isVerbose, processor=FormatProcessor.Get() if process else None)

if __name__ == '__main__':
	ParserUtils.ParseMain(grammar, FormatProcessor.Get())

# EOF - vim: ts=4 sw=4 noet
