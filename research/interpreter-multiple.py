import tlang
from tlang.tree.model import TreeTransform,TreeProcessor,TreeBuilder,NodeError,SemanticError
from typing import Union,Any,Tuple,Optional,Dict,List,Iterator
## @tdoc:process text=texto desc=texto
## @tdoc:indent spaces=2
## desc
##   This experiment is a refinement of the original interpreter experiment,
##   where multiple interpreters are used for the different types of 
##   constructs.

N = TreeBuilder.MakeNode

# -----------------------------------------------------------------------------
#
# MODEL
#
# -----------------------------------------------------------------------------
## section title="Model"
##   desc
##     The core elements required by the runtime of the interpreter.

class Symbol:

	def __init__( self, name:str ):
		self.name = name

	def __repr__( self ):
		return self.name

class Singleton(Symbol):
	pass

class Reference(Symbol):
	pass

End   = object()
Atom  = Union[None,str,int,bool,Symbol]
Value = Union[Atom,Symbol]

class Slot:

	def __init__( self, value=None ):
		self.value:Optional[Any] = value

class Context:

	def __init__( self, parent:'Context'=None ):
		self.parent:Optional[Context] = parent
		self.slots:Dict[str,Slot] = {}

	def derive( self ) -> 'Context':
		return Context(self)

	def has( self, name:str ) -> bool:
		return name in self.slots

	def get( self, name:str ) -> Optional[Any]:
		return self.slots.get(name)

	def define( self, name:str, value:Any ):
		# We don't allow to defined twice
		assert name not in self.slots
		self.slots[name] = value
		return value

	def resolve( self, name:str )->Optional[Slot]:
		if name in self.slots:
			return self.slots[name]
		elif self.parent:
			return self.parent.resolve(name)
		else:
			return None

	def seal( self ):
		def no_define( name:str, value:Any ):
			raise RuntimeError(f"Context is sealed, cannot define slot '{name}'")
		self.define = no_define

# -----------------------------------------------------------------------------
#
# INTERPRETERS
#
# -----------------------------------------------------------------------------

class ValueInterpreter(TreeProcessor):
	"""Creates processes out of definitions."""

	PREFIX = "ex:"

	def __init__( self, context:Context=None, literalInterpreter=None ):
		super().__init__()
		self.context:Context = context or Context()
		self.literalInterpreter = LiteralInterpreter or LiteralInterpreter()

	def pushContext( self ):
		self.context = Context(self.context)
		return self.context

	def popContext( self ):
		res = self.context
		self.context = self.context.parent
		return res

	def derive( self ):
		return self.__class__(self.context.derive(), self.literalInterpreter)

	#NOTE: This is a direct invocation
	#TODO: @on("(list (name (@ (name A))) … REST)")
	def on_list( self, node ):
		target = self.process(node.children[0])
		# NOTE: We do eager evaluation here
		raw_args = [_ for _ in node.children[1:]]
		if target is None:
			raise NodeError(node.children[0], SemanticError("Target resolved to None"))
		if not hasattr(target, META_INVOCATION):
			raise NodeError(node, SemanticError("Invocation target is missing invocation protocol meta-information"))
		else:
			protocol = getattr(target, META_INVOCATION)
			return self.invoke(target, protocol, raw_args)

	def on_ref( self, node ):
		return self.on_name(node)

	def on_name( self, node ):
		name = node["name"]
		res = self.context.resolve(name)
		if res is None:
			raise NodeError(node, SemanticError(f"Cannot resolve symbol: {name}"))
		else:
			return res

	def on_string( self, node ):
		return node["value"]

	def on_number( self, node ):
		return node["value"]

	def on_quote( self, node ):
		return [self.literalInterpreter.process(_) for _ in node.children]

	def invoke( self, target, protocol:'Arguments', args:List[Any] ):
		"""Performs an invocation of the target using the given arguments."""
		argv = []
		j    = len(protocol) - 1
		# Here we iterate through the arguments, extract the corresponding
		# protocol information and process the arguments accordingly.
		self.pushContext()
		inter = self
		for i, arg_node in enumerate(args):
			if i > j:
				# We skip any extra argument
				break
			else:
				arg_meta     = protocol[min(i,j)]
				is_node      = arg_meta.flags & NODE == NODE
				is_data      = arg_meta.flags & DATA == DATA
				is_lazy      = arg_meta.flags & LAZY == LAZY
				if is_node:
					value = arg_node
				else:
					inter = self.literalInterpreter if is_data else self
					# NOTE: We derive for the lazy evaluation as the context
					# might change.
					value = inter.derive().feed(arg_node) if is_lazy else inter.process(arg_node)
				if arg_meta.name != "*":
					self.context.define(arg_meta.name, value)
				argv.append(value)
		res = target(argv)
		self.popContext()
		return res

class LiteralInterpreter(TreeTransform):
	"""Creates subtrees from expressions"""

	PREFIX = "ex:"

	def on_list( self, node ):
		return [self.process(_) for _ in node.children]

	def on_name( self, node ):
		return node["value"]

	def on_string( self, node ):
		return node["value"]

	def on_number( self, node ):
		return node["value"]

# -----------------------------------------------------------------------------
#
# PRIMITIVES
#
# -----------------------------------------------------------------------------

## section title="Primitives"
##   text
##     The primitives are the core functions that power the interpreter. Each
##     function might have a different invocation protocol: some arguments
##     are eager, some arguments are lazy, some argumnets are evaluated, some
##     are passed as raw AST nodes, etc.

META_INVOCATION = "__tlang_invocation__"

##   symbol#EAGER: Flag that denotes an eager evaluation
EAGER = 0
##   symbol#VALUE: Flag that denotes an evaluation of the AST
VALUE = 0
##   symbol#LAZY: Flag that denotes a lazy evaluation (opposite of `EAGER`)
LAZY  = pow(2,0)
##   symbol#DATA: Flag that denotes a data evaluation (ie. no invocation, just the data)
DATA  = pow(2,1)
##   symbol#NODE: Flag that denotes that the argument should be passed as AST
NODE  = pow(2,2)

class Argument:

	def __init__( self, name:str, index:int, flags:int=EAGER ):
		self.name = name
		self.index = index
		self.flags = flags

	def __repr__( self ):
		return f"{self.name}#{self.flags}[{self.index}]"

class Rest(Argument):

	def __init__( self, index:int, flags:int=EAGER ):
		super().__init__("*", index, flags)

Arguments = List[Argument]

def invocation( **kwargs ):
	"""Adds a protocol annotation to a callable object, descibing how
	the arguments should be passed/evaluated."""
	def decorator( f ):
		args = []
		rest = None
		for k,v in kwargs.items():
			if k == "__":
				rest = Rest(-1, v)
			else:
				args.append(Argument(k,len(args),v))
		if rest:
			rest.index = len(args)
			args.append(rest)
		setattr(f, META_INVOCATION, args)
		return f
	return decorator

class Primitives:

	def bind( self, context ):
		context.define("out!",   self.do_out)
		context.define("lambda", self.do_lambda)
		return self

	@invocation( __=EAGER )
	def do_out( self, *args ):
		print (*args)

	@invocation( args=NODE, __=NODE )
	def do_lambda( self, args:Iterator[Value] ):
		print ("LAMBDA", args)
		return self.do_out
		# func_args = expand(interpreter.data.feed(args[0]))
		# # We might have the unnormalized form (LAMBDA A B)
		# if isinstance(func_args, Reference):
		# 	func_args = [func_args]
		# func_code = args[1:]
		# # This is the actual execution of the function
		# def functor(interpreter, args):
		# 	# The functor creates a new context
		# 	interp = interpreter.derive()
		# 	# Maps out the function arguments
		# 	for i,ref in enumerate(func_args):
		# 		# NOTE: Not sure what args are at this stage
		# 		value = args[i]
		# 		if isinstance(value, RuntimeError):
		# 			yield RuntimeError(f"Cannot bind argument {i} '{ref.name}', because: {value}")
		# 		else:
		# 			# We define the slots of the arguments
		# 			interp.context.define(ref.name, value)
		# 	# We re-interpret the nodes in the context
		# 	for line in func_code:
		# 		yield from interp.feed(line)
		# # We define the invocation protocol, which is always eager, for now.
		# kwargs = OrderedDict()
		# for ref in func_args:
		# 	kwargs[ref.name] = EAGER|VALUE
		# # We yield the decorated functor
		# yield invocation( **kwargs )(functor)




# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	#PROGRAM = '(out! "Hello, World!")'
	#PROGRAM = " '(1 (2 3) 4 (5 6 (7 8))) "
	PROGRAM = '((lambda (A) A) "Hello, world!")'
	tree = tlang.parseString(PROGRAM)
	print (tree)
	print ("---")
	inter = ValueInterpreter()
	Primitives().bind(inter.context)
	try:
		for _ in inter.feed(tree):
			print (_)
	except NodeError as e:
		print (e)


# EOF - vim: ts=4 sw=4 noet
