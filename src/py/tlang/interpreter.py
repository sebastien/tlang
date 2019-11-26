from tlang.query.parser import grammar, QueryProcessor
from libparsing  import Grammar
from typing import Optional, List
import os, sys, argparse

G = grammar(Grammar("tlang"), suffixed=True)
G.axiom = G.symbols.ExprValue

def run( args:Optional[List[str]]=None, name="tlang" ):
	if args is None: args = sys.argv[1:]
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = name or os.path.basename(__file__.split(".")[0]),
		description = "Compiler for TLang"
	)
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*',
		help='The .tlang source files to process')
	oparser.add_argument("-vp", "--verbose-parsing", action="store_true",
		help='Outputs detailed parsing information')
	# We create the parse and register the options
	opts = oparser.parse_args(args=args)
	if opts.verbose_parsing:
		G.setVerbose()
	for path in opts.files:
		res       = G.parseStream(sys.stdin) if path == "-" else G.parsePath(path)
		processor = QueryProcessor(G)
		if not res.isSuccess():
			print (res.describe())
			return None
		else:
			return processor.process(res)

if __name__ == '__main__':
	res = run()

# EOF - vim: ts=4 sw=4 noet
