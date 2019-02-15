from tlang.query.parser import grammar, QueryProcessor
from libparsing  import Grammar
import sys

G = grammar(Grammar("tlang"))
G.axiom = G.symbols.ExprValue

for path in sys.argv[1:]:
	res       = G.parsePath(path)
	processor = QueryProcessor(G)
	if not res.isSuccess():
		print (res.describe())
	else:
		print (processor.process(res))

# EOF - vim: ts=4 sw=4 noet
