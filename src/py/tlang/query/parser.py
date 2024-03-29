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
		"QUERY_NODE"              : "(([a-z][\-a-z0-9]*):)?([a-z\*\?][\-a-z0-9\*\?]*)",
		"QUERY_ATTRIBUTE"         : "@[a-z\*\?]+[\-a-z0-9\*\?]*",
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
		"COLON"           : ":",
		"RP"              : ")",
		"LB"              : "{",
		"RB"              : "}",
		"LS"              : "[",
		"RS"              : "]",
		"QUERY_ATTRIBUTE" : "@",
		"QUERY_AXIS_SELF" : "|",
	}
	groups = ("ExprValue", "ExprValuePrefix")
	return ParserUtils.EnsureSymbols(g, tokens, words, groups)

def grammar(g:Optional[Grammar]=None, isVerbose=False, suffixed=False) -> Grammar:
	"""Defines the grammar that parses grammar rule definitions. When
	`suffixed` is `True`, Query matches will need to have at least one
	suffix, which is necessary embedded in the expression language."""
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

	g.group("Query")
	g.rule("QueryNode", s.QUERY_NODE._as("name"))
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
		s.LB, g.arule(s.QUERY_VARIABLE, s.COLON).optional()._as("name"), s.Query._as("value"), s.RB
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

	# FIXME: So that whole "suffixed" thing is to avoid grammar conflicts
	# with the expr parser. But it doesn't work that well in the current
	# state, so we should remove it and rework it.
	#g.rule("QuerySuffixed",         s.QueryPrefix._as("prefix"), s.QuerySuffix.oneOrMore()._as("suffixes"))
	g.rule("QuerySuffixedOptional", s.QueryPrefix._as("prefix"), s.QuerySuffix.zeroOrMore()._as("suffixes"))
	g.rule("QueryAttributePrefix",  s.QueryAttribute._as("prefix"), s.QuerySuffix.zeroOrMore()._as("suffixes"))
	# if suffixed:
	# 	s.Query.set(s.QuerySuffixed, s.QueryAttributePrefix)
	# else:
	s.Query.set(s.QuerySuffixedOptional, s.QueryAttributePrefix)

	# We insert the QuerySuffixed just before the EXPR_VARIABLE, as the query
	# also has a variable. We only want ExprValuePrefix to be queries with
	# a suffix, not just a query with a prefix as things like `(fail!) would not
	# parse as `fail` is a query prefix, and the `!` would then become
	# unparseable.
	s.ExprValuePrefix.insert(10,s.Query)
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
		return self.tree.node("q:axis", {"axis":axis})

	def onQueryNode( self, match ):
		m = self.process(match)[0]
		ns      = m[2]
		pattern = m[3]
		attr = {"pattern":pattern,"ns":ns} if self.IsPattern(pattern) else {"name":pattern,"ns":ns}
		return self.tree.node("q:node", attr)

	def onQuerySubset( self, match ):
		index = int(self.process(match)[0][1])
		return self.tree.node("q:subset", {"index":index})

	def onQueryAttribute( self, match ):
		pattern = self.process(match)[0][0][1:]
		attr = {"pattern":pattern} if self.IsPattern(pattern) else {"name":pattern}
		return self.tree.node("q:attribute", attr)

	def onQueryCurrentNode( self, match ):
		return self.tree.node("q:node")

	def onQueryVariable( self, match ):
		name = self.process(match)[0][0]
		return self.tree.node("q:ref", {"name":name})

	def onQueryPredicate( self, match, expr ):
		return self.tree.node("q:predicate", expr)

	def onQuerySelectorBinding( self, match, name, value ):
		# TODO: Support implicit/explict
		return self.tree.node("q:binding", name, value)

	def onQuerySelectorValue( self, match ):
		return self.process(match[0])

	def onQuerySelector( self, match ):
		return self.process(match[0])

	def onQueryPrefix( self, match, axis, selector, predicate ):
		return self.tree.node("q:selection", axis, selector, predicate)

	def onQuerySuffix( self, match, axis, selector, predicate ):
		return self.onQueryPrefix(match, axis, selector, predicate)

	# NOTE: Deprecated
	# def onQuerySuffixed( self, match, prefix, suffixes ):
	# 	node = self.tree.node("q:query")
	# 	node.add(prefix)
	# 	for _ in suffixes:node.add(_)
	# 	return self.normalizeQueryNode(node)

	def onQuerySuffixedOptional( self, match, prefix, suffixes ):
		node = self.tree.node("q:query")
		node.add(prefix)
		for _ in suffixes:node.add(_)
		return self.normalizeQueryNode(node)

	def onQueryAttributePrefix( self, match, prefix, suffixes ):
		return self.onQuerySuffixedOptional(match, prefix, suffixes)

	def onQuery( self, match ):
		return self.process(match[0])

	def normalizeQueryNode( self, node ):
		# OK, so here we have an edge case which is related to the parser:
		# queries have precedence over EXPR_VARIABLES, so we might end up
		# with a query that has just one q:ref, like so:
		#
		# ```
		#  (q:query
		#       (q:selection
		#           (q:ref (@  (name NAME)))))))
		# ```
		#
		# We also have case where we have the following:
		#
		# ```
		#     (q:query
		#           (q:selection
		#               (q:attribute (@  (pattern [])))))
		# ```
		#
		# The following routine normalizes the subtree as a proper
		# `(ex:variable NAME)` or `(ex:symbol (@ (name "@")))`
		selectors = node.children
		if len(selectors) == 1 and selectors[0].name == "q:selection":
			s = selectors[0].children
			if len(s) == 1:
				n = s[0]
				if n.name == "q:ref":
					n.name = "ex:ref"
					return n.detach()
				elif n.name == "q:node" and n.attr("name"):
					# TODO: Maybe check for wether it's a pattern or a name?
					# FIXME: This should be attr("name")
					return self.tree.node("ex:symbol", {"name":n.attr("name")})
				elif n.name == "q:attribute":
					# FIXME: Why do we remove the query attribute?
					#return self.tree.node("expr-value-symbol", {"name":n.attr("name")})
					return n
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
