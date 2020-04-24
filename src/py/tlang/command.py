from typing import Optional, List
import os, sys, argparse, json
from tlang.parser import parseString, parseFile, G, Processor
from tlang.tree.model import Node,NodeError,Repr
from tlang.interpreter.primitives import Primitives
from tlang.interpreter.core import ValueInterpreter

try:
	import colorama
	colorama.init()
	RED = colorama.Fore.RED
	CYAN = colorama.Fore.CYAN
	BLUE = colorama.Fore.BLUE
	GREEN = colorama.Fore.GREEN
	YELLOW = colorama.Fore.YELLOW
	BOLD = colorama.Style.BRIGHT
	DIM = colorama.Style.DIM
	NORMAL = colorama.Style.NORMAL
	RESET = colorama.Style.RESET_ALL

except ImportError as e:
	RED = ""
	GREEN = ""
	BLUE = ""
	CYAN = ""
	YELLOW = ""
	BRIGHT = ""
	BOLD = ""
	DIM = ""
	NORMAL = ""
	RESET = ""

def onError( error, err=sys.stdout ):
	if isinstance( error, NodeError):
		context = error.node
		while context and context.meta("line") == None:
			context = context.parent
		if not context:
			err.write(f" ! Error at node {node}\n")
		else:
			# We harvest the line and source information. We might
			# want to abstract this out.
			line = context.meta("line")
			offset = context.meta("offset")
			length = context.meta("length")
			source = context.root.meta("source")
			if source:
				# We get the relative line offset, and to do so we need to
				# read all the lines in the file.
				error_line = None
				with open(source, 'rt') as f:
					o = 0
					for i,_ in enumerate(f.readlines()):
						if i == line:
							error_line = _
							break
						else:
							o += len(_)
				error_start = offset - o
				error_end = error_start + length
				error_prefix = "".join(_ if _ in "\t \n" else " " for _ in error_line[:error_start])
				error_cursor = f"└{'─' * (length - 2)}┘" if length > 2 else "↥"
				err.write(f" ┌ {BOLD}Error{RESET} at line {line}[{error_start}:{error_end}] of '{BLUE}{source}{RESET}':\n")
				err.write(f" ├ {error_line[:error_start]}{RED}{BOLD}{error_line[error_start:error_end]}{RESET}{error_line[error_end:]}{RESET}")
				err.write(f" │ {error_prefix}{RED}{error_cursor}{RESET}\n")
			else:
				err.write(f" ┌  {BOLD}Error{RESET} at line {line} range {offset}-{offset+length}:\n")
		err.write(f" └→ {RED}{BOLD}{error.error}{RESET}\n")
		if not source:
			err.write(f"    ↳ {error.node}{RESET}\n")
		if error.hint:
			err.write(f"    ↳ {error.hint}{RESET}\n")
	else:
		# This is a runtime error, not really a managed error. This means
		# that error should be reported.
		err.write(f" {RED}⚠ {RESET} {BOLD}Internal error: {RED}{error.__class__.__name__}{RESET}\n")
		raise (error)

def run( tree:Node, logValues=False, out=sys.stdout, err=sys.stderr ):
	inter = ValueInterpreter()
	Primitives().bind(inter.context)
	def print_out(value):
		if isinstance(value, Exception):
			raise value
		elif isinstance(value, Node):
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
	except Exception as e:
		onError(e, err=err)

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
			ast.meta("source", path)
			assert ast.meta("source") == path
			if opts.ast:
				for _ in Repr.Apply(ast, depth=-1):
					sys.stdout.write(_)
				return ast
			else:
				return run(ast, opts.log)

if __name__ == '__main__':
	res = command()

# EOF - vim: ts=4 sw=4 noet
