from typing import Optional, List
import os, sys, argparse, json
from tlang.parser import parseString, parseFile, G, Processor
from tlang.tree.model import Node,NodeError,Repr
from tlang.interpreter.primitives import Primitives
from tlang.interpreter.core import ValueInterpreter

def run( tree:Node, logValues=False, out = sys.stdout ):
	inter = ValueInterpreter()
	Primitives().bind(inter.context)
	def print_out(value):
		if isinstance(value, Node):
			for _ in Repr.Apply(value, depth=-1):
				out.write(_)
		else:
			out.write(json.dumps(value))
		out.write("\n")
	try:
		if not logValues:
			for _ in inter.feed(tree):
				print_out (_)
		else:
			for child in tree.children:
				if child.name == "ex:comment":
					continue
				print_out (inter.run(child))
	except NodeError as e:
		print (e)

# TODO: -c to interpret a command
# TODO: -i for interactive mode
# TODO: -V --version for version information
def command( args:Optional[List[str]]=None, name="tlang" ):
	if args is None: args = sys.argv[1:]
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = name or os.path.basename(__file__.split(".")[0]),
		description = "Baseline interpreter for TLang"
	)
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*',
		help='The .tlang source files to process')
	oparser.add_argument("-l", "--log", action="store_true",
		help='Logs the value of each expresssion')
	oparser.add_argument("-A", "--ast", action="store_true",
		help='Outputs the AST')
	oparser.add_argument("-vp", "--verbose-parsing", action="store_true",
		help='Outputs detailed parsing information')
	# We create the parse and register the options
	opts = oparser.parse_args(args=args)
	if opts.verbose_parsing:
		G.setVerbose()
	for path in opts.files:
		res       = G.parseStream(sys.stdin) if path == "-" else G.parsePath(path)
		processor = Processor(G)
		if not res.isSuccess():
			print (res.describe())
			return None
		else:
			ast = processor.process(res)
			if opts.ast:
				for _ in Repr.Apply(ast, depth=-1):
					sys.stdout.write(_)
				return ast
			else:
				return run(ast, opts.log)

if __name__ == '__main__':
	res = command()

# EOF - vim: ts=4 sw=4 noet
