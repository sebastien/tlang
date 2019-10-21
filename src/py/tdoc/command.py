import sys, argparse
from typing import Optional, List
from tdoc.parser import parseString, parsePath

def run( args:Optional[List[str]]=None, name="tdoc" ):
	if args is None: args = sys.argv[1:]
	if type(args) not in (type([]), type(())): args = [args]
	oparser = argparse.ArgumentParser(
		prog        = name or os.path.basename(__file__.split(".")[0]),
		description = "Parser and transpiler for TDoc <http://tlang.org/tdoc>"
	)
	oparser.add_argument("files", metavar="FILE", type=str, nargs='*',
		help='The .tdoc source files to process')
	# We create the parse and register the options
	opts = oparser.parse_args(args=args)
	for path in opts.files:
		res       = parsePath(path)

if __name__ == '__main__':
	res = run()

# EOF - vim: ts=4 sw=4 noet
