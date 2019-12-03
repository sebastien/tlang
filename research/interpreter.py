#!/usr/bin/env python3
from typing import Optional,Callable,Iterable,Any,List,Union,Iterator,Generator,Iterable
from tlang.tree import Node
from collections import OrderedDict
# FIXME: This should be reworked
from tlang.interpreter import parseFile
from enum import Enum
import inspect

# TODO: Runtime errors should always be bound to the origin node, so that
# we know where it's coming from.

# TODO: Consider lambdas/closures as processes that need to be fed N arguments

## @tdoc:indent spaces=2
## title: TLang's Research interpreter
## text|texto
##   This is the experimental, slow, Python-based interpreter for TLang. 
##   The goal is to create an interpreter that is suitable for experimentation
##   with features, as well as creating a proof of concept for interpreting
##   TLang. It is not meant to be fast, but is rather meant as a reference.

## section
##   title: Data types
# -----------------------------------------------------------------------------
#
# SYMBOL
#
# -----------------------------------------------------------------------------

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

## section
##   title: Runtime model
##   :
# -----------------------------------------------------------------------------
#
# SLOT
#
# -----------------------------------------------------------------------------

class Slot:

	def __init__( self, value=None ):
		self.value:Optional[Any] = value

# -----------------------------------------------------------------------------
#
# CONTEXT
#
# -----------------------------------------------------------------------------

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
# INVOCATION PROTOCOL
#
# -----------------------------------------------------------------------------

META_INVOCATION = "__tlang_invocation__"
EAGER = 0
VALUE = 0
LAZY  = pow(2,0)
DATA  = pow(2,1)
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


class NodeRuntimeError(RuntimeError):

	def __init__( self, node:Node, *args ):
		super().__init__( *args )
		self.node = node

	def __str__( self ):
		if self.node:
			return f"{self.node.meta('offset')}+{self.node.meta('length')}:{super().__repr__()}"
		else:
			return super().__repr__()

## section
##   title: Interpreters
##   text|texto
##     The interpreters define how the TLang program tree is turned into
##     _values_ and _effects_. The core mechanics relies on walking the
##     tree and producing values or effects, based on the operational
##     semantics.
##   :
# -----------------------------------------------------------------------------
#
# INTERPRETER (ABSTRACT)
#
# -----------------------------------------------------------------------------
# The idea here is to have intepreter work lazily using iterators, giving the
# freedom to to lazy of eager evaluation and to defer until the last moment
# how things are going to be evaluated (ie. run or as data).

class Interpreter:

	META_MATCH = "__tlang_interp_match__"

	@staticmethod
	def Match( name:str ):
		def decorator(f):
			setattr(f, Interpreter.META_MATCH, name)
			return f
		return decorator

	def __init__( self, context:Optional[Context]=None, parent:'Interpreter'=None ):
		self.matches:Dict[str,Callable[Intereter,Node,Iterable[Any]]] = {}
		self.context = context or Context()
		self.parent  = parent
		self.node:Optional[Node] = Node
		for name,value in inspect.getmembers(self):
			if hasattr(value, Interpreter.META_MATCH):
				self.matches[getattr(value, Interpreter.META_MATCH)] = value
		self.init()


	def init( self ):
		pass

	def derive( self ):
		return self.__class__(self.context.derive())

	def feed( self, node:Node ) -> Iterable[Any]:
		# TODO: Support namespace
		name = node.name
		func = self.matches.get(name)
		self.node = node
		if func:
			result = func(node)
			if result is None:
				print (" ! None result for node", node)
			elif isinstance(result, Iterator):
				yield from result
			elif isinstance(result, RuntimeError):
				yield NodeRuntimeError(node, result)
			else:
				yield result
		else:
			yield NodeRuntimeError(node, f"Unsupported node type: {name}")

	def __call__( self, node:Node ) -> Iterable[Any]:
		yield from self.feed(node)

match = Interpreter.Match

# -----------------------------------------------------------------------------
#
# BASE INTERPRETER
#
# -----------------------------------------------------------------------------

class BaseInterpreter(Interpreter):
	"""Interprets trees as runnable code, resolving slots and creating
	invocations."""

	def init( self ):
		self.context.parent = Primitives()
		self.symbols  = Context()
		self.data     = DataInterpreter(parent=self)

	@match("expr-comment")
	def onComment( self, node:Node ) -> None:
		yield None

	@match("expr-value-string")
	def onString( self, node:Node ) -> str:
		yield node.attr("value")

	@match("expr-value-number")
	def onNumber( self, node:Node ) -> float:
		yield node.attr("value")

	@match("expr-value-singleton")
	def onSingleton( self, node:Node ) -> Singleton:
		name = node.attr("name")
		assert name
		res = self.symbols.define(name, Singleton(name)) if not self.symbols.has(name) else self.symbols.get(name)
		yield res

	@match("expr-value-symbol")
	def onSymbol( self, node:Node ) -> Union[Value,Exception]:
		name = node.attr("name")
		assert name, "Node should have a name"
		value = self.context.resolve(name)
		if not value:
			return NodeRuntimeError(node, f"Symbol '{name}' cannot be resolved")
		else:
			return value

	@match("expr-value-ref")
	def onRef( self, node:Node ) -> Union[Value,Exception]:
		name = node.attr("name")
		assert name, "Node should have a name"
		value = self.context.resolve(name)
		if not value:
			return NodeRuntimeError(node, f"Reference '{name}' cannot be resolved")
		else:
			return value

	@match("expr-seq")
	def onSeq( self, node:Node ) -> Iterable[Any]:
		for child in node.children:
			yield from self.feed(child)

	@match("expr-quote")
	def onQuote( self, node:Node ) -> Iterable[Any]:
		yield from self.data.feed(node)

	@match("expr-list")
	def onInvocation( self, node:Node ) -> Iterable[Any]:
		args   = (self.feed(_) if i == 0 else _ for i,_ in enumerate(node.children))
		target = expand(next(args))
		yield from self.invoke(target, args, node)

	# TODO: Define the type signature
	# NOTE: We might take "meta" as arugment
	def invoke( self, target, args, node ):
		"""Performs an invocation of the target using the given arguments."""
		if isinstance(target, RuntimeError):
			yield target
		elif not hasattr(target, META_INVOCATION):
			yield NodeRuntimeError(node,f"Invocation target {target} has no invocation meta-information")
		else:
			meta = getattr(target, META_INVOCATION)
			argv = []
			j    = len(meta) - 1
			# Here we iterate through the arguments, extract the corresponding
			# meta information and process the arguments accordingly.
			interp = self.derive()
			for i, arg_node in enumerate(args):
				if i > j:
					# We skip any extra argument
					break
				else:
					arg_meta     = meta[min(i,j)]
					is_node      = arg_meta.flags & NODE == NODE
					is_data      = arg_meta.flags & DATA == DATA
					is_lazy      = arg_meta.flags & LAZY == LAZY
					if is_node:
						value = arg_node
					else:
						interpreter = self.data if is_data else self
						value       = interpreter.feed(arg_node) if is_lazy else expand(interpreter.feed(arg_node))
					if arg_meta.name != "*":
						interp.context.define(arg_meta.name, value)
					argv.append(value)
			yield from target(interp, argv)

# -----------------------------------------------------------------------------
#
# DATA INTERPRETER
#
# -----------------------------------------------------------------------------

class DataInterpreter(Interpreter):
	"""Interprets nodes as a data"""

	@match("expr-comment")
	def onComment( self, node:Node ) -> None:
		yield None

	@match("expr-value-number")
	def onNumber( self, node:Node ) -> float:
		yield from self.parent.onNumber(node)

	@match("expr-value-singleton")
	def onSingleton( self, node:Node ) -> Singleton:
		yield from self.parent.onSingleton(node)

	@match("expr-seq")
	def onSeq( self, node ):
		return [expand(self.feed(_)) for _ in node.children]

	@match("expr-list")
	def onList( self, node ):
		return [expand(self.feed(_)) for _ in node.children]

	@match("expr-quote")
	def onQuote( self, node ):
		yield from self.onList(node)

	@match("expr-value-symbol")
	def onSymbol( self, node ):
		return Symbol(node.attr("name"))

	@match("expr-value-ref")
	def onRef( self, node ):
		return Reference(node.attr("name"))

	@match("expr-value-string")
	def onString( self, node ):
		return node.attr("value")

# -----------------------------------------------------------------------------
#
# PRIMITIVES
#
# -----------------------------------------------------------------------------

class Primitives(Context):

	def __init__( self ):
		super().__init__()
		self.define("out!",      self.do_out)
		self.define("import",    self.do_import)
		self.define("iter",      self.do_iter)
		self.define("primitive", self.do_primitive)
		self.define("let",       self.do_let)
		self.define("lambda",    self.do_lambda)
		self.seal()

	@invocation( __=EAGER )
	def do_out( self, interpreter:Interpreter, args ):
		res = None
		for v in args:
			sys.stdout.write(str(v))
			res = v
		sys.stdout.write("\n")
		yield res

	@invocation( module=DATA|EAGER, __=DATA|EAGER )
	def do_import( self, interpreter:Interpreter, args:Iterator[Value] ):
		print ("import: ", args)
		yield None

	@invocation( iterable=VALUE|EAGER, functor=VALUE|EAGER )
	def do_iter( self, interpreter:Interpreter, args:Iterator[Value] ):
		"""Iterates through an iterable value. Stops when receiving the symbol `:Stop`"""
		value   = args[0]
		functor = args[1]
		if isinstance(functor, Symbol):
			# We do iterate, even if there's a no-op
			for _ in value:
				pass
		else:
			for i,v in enumerate(value):
				interpreter.invoke(functor, (v,i))
		yield None

	@invocation( __=DATA|EAGER )
	def do_primitive( self, interpreter:Interpreter, args:Iterator[Value] ):
		missing = []
		for prim in args:
			assert isinstance(prim, Symbol)
			if not self.has(prim.name):
				missing.append(prim.name)
		if missing:
			yield RuntimeError(f"Undefined primitives {missing}")
		else:
			yield None

	@invocation( __=NODE )
	def do_let( self, interpreter:Interpreter, args:Iterator[Value] ):
		"""Of the form `(let (SYMBOL VALUE)… VALUE)`, eagerly evaluates the
		values in the `(SYMBOL VALUE)` pairs and binds them to the corresponding
		`SYMBOL` in the context. Yields the evaluation of the last `VALUE`."""
		if len(args) < 2:
			raise RuntimeError("Let has a form (let (SYMBOL VALUE)… VALUE))")
		i      = interpreter.derive()
		for node in args[:-1]:
			# Expected (expr-value-symbol *)
			name  = node.children[0].attr("name")
			# NOTE: This is a letrec as the scope is the current derived
			# interpreter.
			# FIXME: This should probably be the first node that is not a comment
			value = expand(i.feed(node.children[1]))
			if isinstance(value, RuntimeError):
				yield RuntimeError(f"Could not define symbol '{name}' because: {value}")
			else:
				i.context.define(name, value)
		yield from i.feed(args[-1])

	@invocation( args=NODE, __=NODE )
	def do_lambda( self, interpreter:Interpreter, args:Iterator[Value] ):
		func_args = expand(interpreter.data.feed(args[0]))
		# We might have the unnormalized form (LAMBDA A B)
		if isinstance(func_args, Reference):
			func_args = [func_args]
		func_code = args[1:]
		# This is the actual execution of the function
		def functor(interpreter, args):
			# The functor creates a new context
			interp = interpreter.derive()
			# Maps out the function arguments
			for i,ref in enumerate(func_args):
				# NOTE: Not sure what args are at this stage
				value = args[i]
				if isinstance(value, RuntimeError):
					yield RuntimeError(f"Cannot bind argument {i} '{ref.name}', because: {value}")
				else:
					# We define the slots of the arguments
					interp.context.define(ref.name, value)
			# We re-interpret the nodes in the context
			for line in func_code:
				yield from interp.feed(line)
		# We define the invocation protocol, which is always eager, for now.
		kwargs = OrderedDict()
		for ref in func_args:
			kwargs[ref.name] = EAGER|VALUE
		# We yield the decorated functor
		yield invocation( **kwargs )(functor)

# -----------------------------------------------------------------------------
#
# UTILITIES
#
# -----------------------------------------------------------------------------

def expand( iterable:Iterator, asList=False ):
	"""Unwraps the given itearble. If there's only one value, it returns the
	first value, otherwise it returns a list with all the elements.

	Note that it is not recursive."""
	first = next(iterable, End)
	if first is End:
		return [] if asList else None
	v   = True
	res = None
	while v:
		v = next(iterable, End)
		if v is End:
			if res is None:
				return [first] if asList else first
			else:
				return res
		else:
			if res is None:
				res = [v]
			else:
				res.append(v)
	return res

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	import sys, logging
	run = BaseInterpreter()
	res = parseFile(sys.argv[1])
	val = None
	for _ in run.feed(res):
		if isinstance(_, Exception):
			logging.error(_)
		elif _ is not None:
			val = _
	print (f"→ {val}")

# EOF - vim: ts=4 sw=4 noet
