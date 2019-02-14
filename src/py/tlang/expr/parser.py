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
		"STRING_DQ"               : "\"[^\"]*\"",
		"EMPTY_LINE"              : "s*\n",
		"EXPR_SYMBOL"             : "[a-z][\-a-z0-9]*[!\?]?",
		"EXPR_VARIABLE"           : "[A-Z][\_A-Z0-9]*",
	}
	words = {
		"LP"              : "(",
		"RP"              : ")",
		"LB"              : "{",
		"RB"              : "}",
		"COMMA"           : ",",
		"COLON"           : ":",
		"PIPE"            : "|",
		"EOL"             : "\n",
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

	g.rule("ExprValue")
	g.rule("ExprBinding"   , s.LB, s.ExprValue._as("value"), g.arule(s.COLON, s.EXPR_VARIABLE).optional()._as("name"), s.RB)

	g.rule("ExprInvocation", s.LP,    s.ExprValue.optional()._as("arg"), s.RP)
	g.rule("ExprPipe",       s.PIPE,  s.ExprValue._as("arg"))
	g.rule("ExprJoin",       s.COMMA, s.ExprValue._as("arg"))

	g.group("ExprValuePrefix").set(
		s.ExprBinding,
		s.NUMBER, s.STRING_DQ, s.EXPR_SYMBOL, s.EXPR_VARIABLE
	)
	g.group("ExprValueSuffix").set(
		s.ExprInvocation,
		s.ExprPipe,
		s.ExprJoin,
	)
	s.ExprValue.set(s.ExprValuePrefix._as("prefix"), s.ExprValueSuffix.zeroOrMore()._as("suffixes"))

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

class ExprProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = ExprProcessor()
		return cls.INSTANCE

	def __init__( self, grammar=None, strict=True ):
		Processor.__init__( self, grammar, strict )
		self.tree = TreeBuilder()

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

	def onNUMBER( self, match):
		value = float(self.process(match)[0])
		return self.tree.node("expr-value-number", {"value":value})

	def onSTRING_DQ( self, match):
		value = self.process(match)[1]
		return self.tree.node("expr-value-string", {"value":value})

	def onEXPR_SYMBOL( self, match):
		value = self.process(match)[0]
		return self.tree.node("expr-value-symbol", {"value":value})

	def onExprValuePrefix( self, match ):
		return self.process(match[0])
		return res

	def onExprValueSuffix( self, match ):
		return self.process(match[0])

	def onExprInvocation( self, match, arg ):
		node = self.tree.node("expr-value-invocation")
		if arg.name.startswith("expr-value-list"):
			node.merge(arg)
		else:
			node.add(arg)
		return node

	def onExprJoin( self, match, arg ):
		if arg.name == "expr-value-list":
			return arg
		else:
			node = self.tree.node("expr-value-list")
			node.add(arg)
			return node

	def onExprPipe( self, match, arg ):
		node = self.tree.node("expr-value-pipe")
		node.add(arg)
		return node

	def onExprValue( self, match, prefix, suffixes ):
		# NOTE: This is where we manage priorities. We should define
		# more clearly what happens there.
		for suffix in suffixes:
			if suffix.name == "expr-value-list":
				suffix.insert(0, prefix)
				prefix = suffix
			elif suffix.name == "expr-value-invocation":
				suffix.insert(0, prefix)
				prefix = suffix
			elif suffix.name == "expr-value-pipe":
				assert (len(suffix.children)) == 1
				first_child = suffix.children[0]
				if first_child.name == "expr-value-invocation":
					first_child.insert(1,prefix)
					prefix = first_child.detach()
				else:
					prefix = self.tree.node("expr-value-invocation", prefix, first_child.detach())
			else:
				raise ValueError("Suffix not supported yet: {0}".format(suffix))
		return prefix

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