from libparsing import Grammar, Symbols, Processor, ensure_string
from typing import Optional
from tlang.tree.model import Node,NodeTemplate
import sys, os

GRAMMAR = None

def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shader by all the grammars
	defined in this moddule."""
	s      = g.symbols
	tokens = {
		"WS"            : "[\s\n]+",
		"NUMBER"        : "[0-9]+(\.[0-9]+)?",
		"STRING_DQ"     : "\"[^\"]*\"",
		"EMPTY_LINE"    : "s*\n",
		"NODE_NAME"     : "[a-z][\-a-z0-9]*",
		"NODE_COMMENT"  : ";;[^\n]*[\n]?",
		"NODE_SYMBOL"   : "[a-zA-Z][\-_A-Za-z0-9]*",
		"NODE_SYMBOL_Q" : "'([a-zA-Z][\-_A-Za-z0-9]*)",
		"NODE_TEMPLATE" : "(…|\.\.\.)?([A-Z][_A-Z]*)",
	}
	words = {
		"LP"       : "(",
		"RP"       : ")",
		"AT"       : "@",
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

	# Node attributes
	g.group("NodeAttributeString", s.STRING_DQ)
	g.group("NodeAttributeNumber", s.NUMBER)
	g.group("NodeAttributeSymbol", s.NODE_SYMBOL)
	g.group("NodeAttributeValue", s.NodeAttributeString, s.NodeAttributeNumber, s.NodeAttributeSymbol)
	g.rule("NodeAttribute", s.LP, s.NODE_NAME._as("key"), s.WS, s.NodeAttributeValue._as("value"), s.RP)
	g.rule("NodeAttributes", s.LP, s.AT, s.WS,  s.NodeAttribute.oneOrMore()._as("attributes"), s.RP)

	g.group("NodeChild")
	g.rule("NodeString"  , s.STRING_DQ)
	g.rule("NodeNumber"  , s.NUMBER)
	g.rule("NodeSymbol"  , s.NODE_SYMBOL_Q)
	g.rule("NodeTemplate" , s.NODE_TEMPLATE)
	g.group("NodeComment", s.NODE_COMMENT)

	g.rule("Leaf", s.NODE_NAME._as("name"))
	g.rule("Node", s.LP, s.NODE_NAME._as("name"), s.NodeAttributes.optional()._as("attributes"), s.NodeChild.zeroOrMore()._as("children"), s.RP)

	# NOTE: Changing the order might speed up things
	s.NodeChild.set(
		s.NodeSymbol, s.NodeNumber, s.NodeString, s.NodeTemplate,
		s.Leaf, s.Node,
	)

	g.rule("Tree", s.NodeComment.zeroOrMore(), s.NodeChild._as("node"), s.NodeComment.zeroOrMore())
	g.rule("Forest", s.Tree.oneOrMore())
	g.axiom = s.Forest
	g.skip  = s.WS

	if not GRAMMAR:
		GRAMMAR = g
		g.prepare()
	g.setVerbose(isVerbose)
	return g

class TreeProcessor(Processor):

	INSTANCE = None

	@classmethod
	def Get(cls):
		if not cls.INSTANCE: cls.INSTANCE = TreeProcessor()
		return cls.INSTANCE

	def createGrammar(self) -> Grammar:
		return GRAMMAR or grammar()

	def onForest( self, match ):
		res = []
		for _ in match:
			r = self.process(_)
			if r:
				res += r
		return res

	def onTree( self, match, node ):
		return self.process(node)

	def onNodeNumber( self, match ):
		value = float(self.process(match[0])[0])
		value = int(value) if int(value) == value else value
		return Node("number").attr("value", value)

	def onNodeString( self, match ):
		value = self.process(match[0])[0]
		return Node("string").attr("value", value)

	def onNodeSymbol( self, match ):
		value = self.process(match[0])[1]
		return Node("symbol").attr("value", value)

	def onNodeTemplate( self, match ):
		_, rest, name = self.process(match[0])
		res =  NodeTemplate("template").attr("value", name)
		if rest: res.attr("expand", bool(rest))
		return res

	def onLeaf( self, match, name ):
		return Node(ensure_string(name[0]))

	def onNode( self, match, name, attributes, children ):
		name = ensure_string(name[0])
		node = Node(name)
		node.children = children
		if attributes:
			for key, value in attributes:
				node.attributes[key] = value
		return node

	def onNodeAttributes( self, match, attributes ):
		return attributes or ()

	def onNodeAttribute( self, match, key, value ):
		key   = key[0]
		return (key, value)

	def onNodeAttributeValue( self, match ):
		return self.process(match[0])

	def onNodeAttributeString( self, match ):
		return ensure_string(self.process(match[0])[0])

	def onNodeAttributeSymbol( self, match ):
		return ensure_string(self.process(match[0])[0])

	def onNodeAttributeNumber( self, match ):
		value = float(self.process(match[0])[0])
		value = int(value) if int(value) == value else value
		return value

	def onNodeChild( self, match ):
		return self.process(match[0])

	def onNodeComment( self, match ):
		return None

def parseString( text:str, isVerbose=False, process=True ):
	g = grammar (isVerbose=isVerbose)
	result = g.parseString(text)
	if not process:
		return result
	elif result.isSuccess():
		return TreeProcessor.Get().process(result)
	else:
		raise Exception("Parsing failed: {0}".format(result.describe()))

def parseFile( path:str, isVerbose=False, process=True ):
	with open(path, "rt") as f:
		return parseString(f.read(), isVerbose)

if __name__ == '__main__':
	processor = TreeProcessor()
	for arg in sys.argv[1:]:
		if os.path.exists(arg):
			result = parseFile(arg, True, process=False)
		else:
			result = parseString(arg, True, process=False)
		if not result.isSuccess():
			print (result.describe())
		else:
			forest = processor.process(result)
			for tree in forest:
				print(tree)

# EOF - vim: ts=4 sw=4 noet
