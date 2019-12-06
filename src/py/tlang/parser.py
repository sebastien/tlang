from tlang.query.parser import grammar, QueryProcessor
from tlang.utils import ParserUtils
from libparsing  import Grammar

Processor = QueryProcessor
G = grammar(Grammar("tlang"), suffixed=False)
G.axiom = G.symbols.ExprValue
P = Processor(G)

def parseString( text:str, isVerbose=False, process=True ):
	return ParserUtils.ParseString(grammar, text, isVerbose, processor=QueryProcessor.Get() if process else None)

def parseFile( path:str, isVerbose=False, process=True ):
	return ParserUtils.ParseFile(grammar, path, isVerbose, processor=QueryProcessor.Get() if process else None)

if __name__ == "__main__":
	import os, sys
	path = sys.argv[1]
	text = open(path).read() if os.path.exists(path) else path
	print (parseString(text))

# EOF - vim: ts=4 sw=4 noet
