from tlang.query.parser import grammar, QueryProcessor
from libparsing  import Grammar
import os,sys

G = grammar(Grammar("tlang"))
G.axiom = G.symbols.ExprValue
P = QueryProcessor(G)

def parseString( text:str ):
	res = G.parseString(text)
	if not res.isSuccess():
		raise SyntaxError(res.describe())
	else:
		return P.process(res)

if __name__ == "__main__":
	path = sys.argv[1]
	text = open(path).read() if os.path.exists(path) else path
	print (parseString(text))

# EOF - vim: ts=4 sw=4 noet
