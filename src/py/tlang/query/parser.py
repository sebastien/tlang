from libparsing import Grammar, Symbols, Processor, ensure_string
from typing import Optional
from tlang.utils import ParserUtils
import sys, os

GRAMMAR = None

def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shared by all the grammars
	defined in this moddule."""
	s      = g.symbols
	tokens = {
		"WS"                      : "[\s\n]+",
		"NUMBER"                  : "[0-9]+(\.[0-9]+)?",
		"STRING_DQ"               : "\"[^\"]*\"",
		"EMPTY_LINE"              : "s*\n",
		"QUERY_VARIABLE"          : "[A-Z[A-Z0-9]*",
		"QUERY_PATTERN"           : "[a-z\*\?][\-a-z0-9\*\?]*",
		"QUERY_SYMBOL"            : "[a-z][\-a-z0-9]*",
		"QUERY_COMMENT"           : ";;[^\n]*[\n]?",
		"QUERY_AXIS_DESCENDANTS"  : "/(\d?/)?",
		"QUERY_AXIS_ANCESTORS"    : "\\(\d?\\)?",
		"QUERY_AXIS_AFTER"        : ">(\d?>)?",
		"QUERY_AXIS_BEFORE"       : "<(\d?<)?",
		"QUERY_CURRENT_NODE"      : "\.+",
	}
	words = {
		"LP"              : "(",
		"RP"              : ")",
		"LB"              : "}",
		"RB"              : "}",
		"LS"              : "[",
		"RS"              : "]",
		"AT"              : "@",
		"STAR"            : "*",
		"QUERY_ATTRIBUTE" : "@."
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
			g=Grammar("query", isVerbose=isVerbose)
	s = symbols(g)

	# TODO: Template
	g.group("QueryAxis",
		s.QUERY_AXIS_DESCENDANTS,
		s.QUERY_AXIS_ANCESTORS,
		s.QUERY_AXIS_BEFORE,
		s.QUERY_AXIS_AFTER
	)

	g.rule("QueryNodePattern",      s.QUERY_PATTERN)
	g.rule("QueryAttributePattern", s.AT, s.QUERY_PATTERN)
	g.rule("QueryCurrentNode",      s.QUERY_CURRENT_NODE)
	g.rule("QueryCurrentAttribute", s.QUERY_ATTRIBUTE)

	g.group("QueryPredicate",
		s.QueryNodePattern,
		s.QueryAttributePattern,
		s.QueryCurrentNode,
		s.QueryCurrentAttribute,
	)

	g.rule("Selector",
		s.QueryAxis.optional()._as("axis"),
		s.QueryPredicate.optional()._as("predicate"),
	)

	g.rule("Selection",
		s.Selector.oneOrMore()
	)

	g.rule("Query",
		s.Selection
	)

	g.axiom = s.Query
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

class QueryProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = QueryProcessor()
		return cls.INSTANCE

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

# TODO: move the core to to tlang.utils.GrammarUtils.parse{String|File|Main}(g,tokens,words,groups)
def parseString( text:str, isVerbose=False, process=True ):
	return ParserUtils.ParseString(grammar, text, isVerbose, processor=QueryProcessor.Get() if process else None)

def parseFile( path:str, isVerbose=False, process=True ):
	return ParserUtils.ParseFile(grammar, path, isVerbose, processor=QueryProcessor.Get() if process else None)

if __name__ == '__main__':
	ParserUtils.ParseMain(grammar, QueryProcessor.Get())

# EOF - vim: ts=4 sw=4 noet
