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
		"QUERY_VARIABLE"          : "[A-Z][_A-Z0-9]*",
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
		"QUERY_ATTRIBUTE" : "@",
		"QUERY_AXIS_SELF" : "|",
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
		s.QUERY_AXIS_AFTER,
		s.QUERY_AXIS_SELF,
	)

	g.rule("QueryNode",          s.QUERY_NODE)
	g.rule("QueryVariable",      s.QUERY_VARIABLE)
	g.rule("QueryAttribute",     s.QUERY_ATTRIBUTE)
	g.rule("QueryCurrentNode",   s.QUERY_CURRENT_NODE)
	g.rule("QuerySubset",        s.QUERY_SUBSET)

	g.group("QuerySelectorValue",
		s.QuerySubset,
		s.QueryCurrentNode,
		s.QueryVariable,
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

	g.rule("QueryPrefix",
		s.QueryAxis.optional()._as("axis"),
		s.QuerySelector._as("selector"),
		s.QueryPredicate.optional()._as("predicate"),
	)

	g.rule("QuerySuffix",
		s.QueryAxis._as("axis"),
		s.QuerySelector._as("selector"),
		s.QueryPredicate.optional()._as("predicate"),
	)

	g.rule("Query",
		s.QueryPrefix._as("prefix"), s.QuerySuffix.zeroOrMore()._as("suffixes")
	)

	# We insert the Query just before the EXPR_VARIABLE, as the query
	# also has a variable.
	s.ExprValuePrefix.insert(8,s.Query)
	print (s.ExprValuePrefix)
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

	@classmethod
	def IsPattern( cls, text ):
		for c in text:
			if c in ".*?_":
				return True

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

	def onQueryAxis( self, match ):
		axis = self.process(match)[0][0]
		return self.tree.node("query-axis", {"axis":axis})

	def onQueryNode( self, match ):
		pattern = self.process(match)[0][0]
		attr = {"pattern":pattern} if self.IsPattern(pattern) else {"name":pattern}
		return self.tree.node("query-node", attr)

	def onQuerySubset( self, match ):
		index = int(self.process(match)[0][1])
		return self.tree.node("query-subset", {"index":index})

	def onQueryAttribute( self, match ):
		pattern = self.process(match)[0][0][1:]
		attr = {"pattern":pattern} if self.IsPattern(pattern) else {"name":pattern}
		return self.tree.node("query-attribute", attr)

	def onQueryCurrentNode( self, match ):
		return self.tree.node("query-node")

	def onQueryVariable( self, match ):
		name = self.process(match)[0][0]
		return self.tree.node("query-variable", {"name":name})

	def onQueryPredicate( self, match, expr ):
		return self.tree.node("query-predicate", expr)

	def onQuerySelectorBinding( self, match, value ):
		# TODO: Support implicit/explict
		return self.tree.node("query-binding", value)

	def onQuerySelectorValue( self, match ):
		return self.process(match[0])

	def onQuerySelector( self, match ):
		return self.process(match[0])

	def onQueryPrefix( self, match, axis, selector, predicate ):
		return self.tree.node("query-selection", axis, selector, predicate)

	def onQuerySuffix( self, match, axis, selector, predicate ):
		return self.onQueryPrefix(match, axis, selector, predicate)

	def onQuery( self, match, prefix, suffixes ):
		node = self.tree.node("query")
		node.add(prefix)
		for _ in suffixes:node.add(_)
		return self.normalizeQueryNode(node)

	def normalizeQueryNode( self, node ):
		# OK, so here we have an edge case which is related to the parser:
		# queries have precedence over EXPR_VARIABLES, so we might end up
		# with a query that has just one query-variable, like so:
		#
		# ```
		#  (query
		#       (query-selection
		#           (query-variable (@  (name NAME)))))))
		# ```
		# 
		# We also have case where we have the following:
		#
		# ```
		#     (query
		#           (query-selection
		#               (query-attribute (@  (pattern [])))))
		# ```
		#
		# The following routine normalizes the subtree as a proper
		# `(expr-variable NAME)` or `(expr-value-symbol (@ (name "@")))`
		selectors = node.children
		if len(selectors) == 1 and selectors[0].name == "query-selection":
			s = selectors[0].children
			if len(s) == 1:
				n = s[0]
				if n.name == "query-variable":
					n.name = "expr-variable"
					return n.detach()
				elif n.name == "query-node" and n.attr("name"):
					# TODO: Maybe check for wether it's a pattern or a name?
					# FIXME: This should be attr("name")
					return self.tree.node("expr-value-symbol", {"name":n.attr("name")})
				elif n.name == "query-attribute":
					return self.tree.node("expr-value-symbol", {"name":"@"})
		return node

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
