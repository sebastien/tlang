from libparsing import Grammar, Symbols, Processor, ensure_string
from typing import Optional
from tlang.rule.model import Rule
import sys, os

__doc__ = """
Defines a parser for the rule grammar, producing a Rule model.
"""

GRAMMAR = None

# TODO: move the core to to tlang.utils.GrammarUtils.symbols(g,tokens,words,groups)
def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shader by all the grammars
	defined in this moddule."""
	s      = g.symbols
	tokens = {
		"WS"           : "\s+",
		"RULE_NAME"    : "[A-Z][_A-Z]*",
		"RULE_VARIANT" : "\([a-z][\-a-z]*\)",
		"RULE_BINDING" : ":[A-Z][_A-Z]*",
		"RULE_COMMENT" : "\s*//[^\n]+",
		"TOKEN_RANGE"  : "\[(.)-(.)\]",
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
		"EOL"      : "\n",

	}
	groups = ("Tree",)
	for k,v in tokens.items():
		if not hasattr(s,k): g.token(k,v)
	for k,v in words.items():
		if not hasattr(s,k): g.word(k,v)
	for k in groups:
		if not hasattr(s,k): g.group(k)
	return g.symbols

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
	g.group("RuleExpression")
	g.rule("RuleReference", s.RULE_NAME, s.RULE_BINDING.optional(), s.CARDINALITY.optional())
	g.rule("RuleGroup", s.LP, s.RuleExpression.oneOrMore(), s.RP, s.CARDINALITY.optional())
	g.rule("RuleTokenString", s.STRING_SQ)
	g.rule("RuleTokenRange", s.TOKEN_RANGE)
	g.group("RuleToken", s.RuleTokenString, s.RuleTokenRange)
	s.RuleExpression.set( s.RuleToken, s.RuleGroup, s.RuleReference)

	# Statements
	g.rule("RulePattern",    s.EOL, s.RULE_PAT, s.Tree, s.RULE_END)
	g.rule("RuleDefinition", s.RULE_NAME, s.RULE_VARIANT.optional(), s.RULE_DEF, s.RuleExpression.oneOrMore(), s.RULE_END, s.RulePattern.optional())
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

class RuleProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = RuleProcessor()
		return cls.INSTANCE

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

# TODO: move the core to to tlang.utils.GrammarUtils.parse{String|File|Main}(g,tokens,words,groups)
def parseString( text:str, isVerbose=False, process=True ):
	g = grammar(isVerbose=isVerbose)
	result = g.parseString(text)
	if not process:
		return result
	elif result.isSuccess():
		return RuleProcessor.Get().process(result)
	else:
		raise Exception("Parsing failed: {0}".format(result.describe()))

def parseFile( path:str, isVerbose=False, process=True ):
	with open(path, "rt") as f:
		return parseString(f.read(), isVerbose)

if __name__ == '__main__':
	processor = RuleProcessor()
	for arg in sys.argv[1:]:
		if os.path.exists(arg):
			result = parseFile(arg, True, process=False)
		else:
			result = parseString(arg, True, process=False)
		if not result.isSuccess():
			print (result.describe())
		else:
			print (processor.process(result))

# EOF - vim: ts=4 sw=4 noet
