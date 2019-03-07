from tlang.query.parser import grammar, QueryProcessor
from libparsing  import Grammar
from typing import Optional, List
import sys

G = grammar(Grammar("tlang"))
G.axiom = G.symbols.ExprValue

def run( args:Optional[List[str]]=None ):
	arg_list:List[str] = args or sys.argv[1:]
	path      = arg_list[0]
	res       = G.parsePath(path)
	processor = QueryProcessor(G)
	if not res.isSuccess():
		print (res.describe())
		return None
	else:
		return processor.process(res)

if __name__ == '__main__':
	res = run()

# EOF - vim: ts=4 sw=4 noet
