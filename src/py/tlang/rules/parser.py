from libparsing import Grammar, Symbols, Processor, ensure_string
from typing import Optional
from tlang.rules.model import Rule
from tlang.utils import ParserUtils
import sys, os

__doc__ = """
Defines a parser for the rule grammar, producing a Rule model.
"""

GRAMMAR = None

# -----------------------------------------------------------------------------
#
# SYMBOLS
#
# -----------------------------------------------------------------------------

# TODO: move the core to to tlang.utils.GrammarUtils.symbols(g,tokens,words,groups)
def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shader by all the grammars
	defined in this moddule."""
	tokens = {
		"WS"           : "\s+",
		"RULE_NAME"    : "[A-Z][_A-Z]*",
		"RULE_VARIANT" : "\([a-z][\-a-z]*\)",
		"RULE_BINDING" : ":[A-Z][_A-Z]*",
		"RULE_COMMENT" : "\s*//[^\n]+",
		"TOKEN_RANGE"  : "\[((.)-(.)|\\-|[^\\]])+\]",
		"CARDINALITY"  : "[\?\*\+]",
		"STRING_SQ"    : "'[^']+'",
		"STRING_DQ"    : "\"[^\"]*\"",
		"EMPTY_LINE"   : "s*\n"
	}
	words = {
		"RULE_DEF" : ":=",
		"RULE_END" : ";",
		"RULE_PAT" : "-->",
		"LP"       : "(",
		"RP"       : ")",
		"QUOTE"    : "'",
		"UNDERSCORE": "_",
		"EOL"      : "\n",

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
			g=Grammar("tree", isVerbose=isVerbose)
	s = symbols(g)

	# Expressions
	g.group("RuleValue")
	g.rule("RuleExpression")
	g.rule("RuleReference", s.RULE_NAME, s.RULE_BINDING.optional(), s.CARDINALITY.optional())
	g.rule("RuleGroup", s.LP, s.RuleExpression, s.RP, s.CARDINALITY.optional())
	g.rule("RuleTokenString", s.STRING_SQ)
	g.rule("RuleTokenRange", s.TOKEN_RANGE)
	g.group("RuleTokenValue", s.RuleTokenString, s.RuleTokenRange)
	g.rule("RuleToken", s.RuleTokenValue, s.CARDINALITY.optional())
	s.RuleValue.set( s.RuleToken, s.RuleGroup, s.RuleReference)
	s.RuleExpression.set(s.RuleValue, g.arule(s.UNDERSCORE.optional(), s.RuleValue).zeroOrMore ())

	# Statements
	g.rule("RulePattern",    s.EOL, s.RULE_PAT, s.Tree, s.RULE_END)
	g.rule("RuleDefinition", s.RULE_NAME, s.RULE_VARIANT.optional(), s.RULE_DEF, s.RuleExpression, s.RULE_END, s.RulePattern.optional())
	g.rule("RuleComment",    s.RULE_COMMENT, s.EOL)

	# Rules
	g.group("RuleStatement",
		s.RuleComment,
		s.RuleDefinition,
		s.EMPTY_LINE,
	)

	g.rule("Rules", s.RuleStatement.zeroOrMore())

	g.axiom = s.Rules
	g.skip  = s.WS

	if not GRAMMAR:
		GRAMMAR = g
		g.prepare()
	g.setVerbose(isVerbose)
	return g

# -----------------------------------------------------------------------------
#
# PROCESSOR
#
# -----------------------------------------------------------------------------

class RuleProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = RuleProcessor()
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
	return ParserUtils.ParseString(grammar, text, isVerbose, processor=RuleProcessor.Get() if process else None)

def parseFile( path:str, isVerbose=False, process=True ):
	return ParserUtils.ParseFile(grammar, path, isVerbose, processor=RuleProcessor.Get() if process else None)

if __name__ == '__main__':
	ParserUtils.ParseMain(grammar, RuleProcessor.Get())

# EOF - vim: ts=4 sw=4 noet
