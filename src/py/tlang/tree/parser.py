from libparsing import Grammar, Symbols
from typing import Optional

GRAMMAR = None

def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shader by all the grammars
	defined in this moddule."""
	s      = g.symbols
	tokens = {
		"WS"           : "[\s\n]+",
		"NODE_NAME"    : "[a-z][\-a-z0-9]+",
		"ATOM_SYMBOL"  : "[a-z]\w+",
		"ATOM_SYMBOL_Q": "'[a-z]\w+",
		"ATOM_NUMBER"  : "[0-9]+(\.[0-9]+)?",
		"STRING_DQ"    : "\"[^\"]*\"",
		"EMPTY_LINE"   : "s*\n",
		"TREE_COMMENT" : ";;[^\n]*\n",
	}
	words = {
		"LP"       : "(",
		"RP"       : ")",
		"QUOTE"    : "'",
		"AT"       : "@",
		"EOL"      : "\n",
	}
	groups = ()
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

	g.group("NodeChild")
	g.rule("NodeString", s.LP, g.aword("string"), s.STRING_DQ,   s.LP)
	g.rule("NodeNumber", s.LP, g.aword("number"), s.ATOM_NUMBER, s.LP)
	g.rule("NodeSymbol", s.LP, g.aword("symbol"), s.ATOM_SYMBOL, s.LP)
	g.group("NodeAttributeValue", s.STRING_DQ, s.ATOM_NUMBER, s.ATOM_SYMBOL)
	g.rule("NodeAttribute", s.LP, s.ATOM_SYMBOL, s.NodeAttributeValue, s.LP)
	g.rule("NodeAttributes", s.LP, s.AT,          s.NodeAttribute.oneOrMore(), s.LP)
	g.rule("NodeStringShort", s.STRING_DQ)
	g.rule("NodeNumberShort", s.ATOM_NUMBER)
	g.rule("NodeSymbolShort", s.ATOM_SYMBOL_Q)
	g.rule("Node", s.LP, s.NODE_NAME, s.NodeAttributes.optional(), s.NodeChild.zeroOrMore(), s.RP)

	s.NodeChild.set(
		s.NodeSymbolShort, s.NodeNumberShort, s.NodeStringShort,
		s.NodeSymbol     , s.NodeNumber     , s.NodeString,
		s.Node
	)

	g.group("Tree", s.Node)
	g.axiom = s.Tree
	g.skip  = s.WS

	GRAMMAR = g
	g.setVerbose(isVerbose)
	return g

def parseString( text:str, isVerbose=False ):
	g = grammar (isVerbose=isVerbose)
	return g.parseString(text)

def parseFile( path:str, isVerbose=False ):
	with open(path, "rt") as f:
		return self.parseString(f.read(), isVerbose)

# EOF - vim: ts=4 sw=4 noet
