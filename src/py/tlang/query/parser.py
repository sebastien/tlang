from libparsing  import Grammar, Symbols, Processor, ensure_string
from typing      import Optional
from tlang.utils import ParserUtils
from tlang.expr.parser import ExprProcessor, grammar as expr_grammar
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
		"QUERY_NODE"              : "[a-z\*\?][\-a-z0-9\*\?]*",
		"QUERY_ATTRIBUTE"         : "@[a-z\*\?]?[\-a-z0-9\*\?]*",
		"QUERY_CURRENT_NODE"      : "\.+",
		"QUERY_SUBSET"            : "#(\d+)",

		"QUERY_AXIS_DESCENDANTS"  : "\\.?/(\d?/)?",
		"QUERY_AXIS_ANCESTORS"    : "\\.?\\\\(\d?\\\\)?",
		"QUERY_AXIS_BEFORE"       : "\\.?>(\d?>|-?\\=?\\+?>)?",
		"QUERY_AXIS_AFTER"        : "\\.?<(\d?<|-?\\=?\\+?<)?",
	}
	words = {
		"LP"              : "(",
		"RP"              : ")",
		"LB"              : "}",
		"RB"              : "}",
		"LS"              : "[",
		"RS"              : "]",
		"QUERY_ATTRIBUTE" : "@"
	}
	groups = ("ExprValue", "ExprValuePrefix")
	return ParserUtils.EnsureSymbols(g, tokens, words, groups)


def grammar(g:Optional[Grammar]=None, isVerbose=False) -> Grammar:
	"""Defines the grammar that parses grammar rule definitions."""
	global GRAMMAR
	if not g:
		if GRAMMAR:
			return GRAMMAR
		else:
			g=Grammar("query", isVerbose=isVerbose)
	g = expr_grammar(g)
	s = symbols(g)

	# TODO: Template
	g.group("QueryAxis",
		s.QUERY_AXIS_DESCENDANTS,
		s.QUERY_AXIS_ANCESTORS,
		s.QUERY_AXIS_BEFORE,
		s.QUERY_AXIS_AFTER
	)

	g.rule("QueryNode",          s.QUERY_NODE)
	g.rule("QueryAttribute",     s.QUERY_ATTRIBUTE)
	g.rule("QueryCurrentNode",   s.QUERY_CURRENT_NODE)
	g.rule("QuerySubset",        s.QUERY_SUBSET)

	g.group("QuerySelectorValue",
		s.QuerySubset,
		s.QueryCurrentNode,
		s.QueryNode,
		s.QueryAttribute,
	)

	# TODO: Support optional name
	g.rule("QuerySelectorBinding",
		s.LB, s.QuerySelectorValue._as("value"), s.RB
	)

	g.group("QuerySelector",
		s.QuerySelectorBinding,
		s.QuerySelectorValue,
	)

	g.rule("QueryPredicate",
		s.LS,
		s.ExprValue._as("expr"),
		s.RS,
	)

	g.rule("QuerySelection",
		s.QueryAxis.optional()._as("axis"),
		s.QuerySelector._as("selector"),
		s.QueryPredicate.optional()._as("predicate"),
	)

	g.rule("Query",
		s.QuerySelection.oneOrMore()._as("selectors")
	)

	# TODO: The s.Query should be PREFIXED!
	s.ExprValuePrefix.add(s.Query)
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

class QueryProcessor(ExprProcessor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = QueryProcessor()
		return cls.INSTANCE

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

	def onQueryAxis( self, match ):
		axis = self.process(match)[0][0]
		return self.tree.node("query-axis", {"axis":axis})

	def onQueryNode( self, match ):
		pattern = self.process(match)[0][0]
		# TODO: Detect if patter is a regexp or not
		return self.tree.node("query-node", {"pattern":pattern})

	def onQuerySubset( self, match ):
		index = int(self.process(match)[0][1])
		return self.tree.node("query-subset", {"index":index})

	def onQueryAttribute( self, match ):
		pattern = self.process(match)[0][1:]
		# TODO: Detect if patter is a regexp or not
		return self.tree.node("query-attribute", {"pattern":pattern})

	def onQueryCurrentNode( self, match ):
		return self.tree.node("query-node")

	def onQueryPredicate( self, match, expr ):
		return self.tree.node("query-predicate", expr)

	def onQuerySelectorBinding( self, match, value ):
		# TODO: Support implicit/explict
		return self.tree.node("query-binding", value)

	def onQuerySelectorValue( self, match ):
		return self.process(match)[0]

	def onQuerySelector( self, match ):
		return self.process(match)[0]

	def onQuerySelection( self, match, axis, selector, predicate ):
		return self.tree.node("query-selection", axis, selector, predicate)

	def onQuery( self, match, selectors ):
		return self.tree.node("query", *selectors)

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
