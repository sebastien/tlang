from typing import Optional,Callable,Iterable,Any
from tlang.tree import Node
# FIXME: This should be reworked
from tlang.interpreter import parseFile
import inspect


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

	def __init__( self ):
		self.parent:Optional[Context] = None
		self.slots:Dict[str,Slot] = {}

	def define( self, name:str, value:Any ):
		# We don't allow to defined twice
		assert name not in self.slots
		self.slots[name] = value
		return self

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
# SYMBOL
#
# -----------------------------------------------------------------------------

class Symbol:

	def __init__( self, name:str ):
		self.name = name

	def __repr__( self ):
		return self.name

# -----------------------------------------------------------------------------
#
# INTERPRETER (ABSTRACT)
#
# -----------------------------------------------------------------------------

class Interpreter:

	@staticmethod
	def Match( name:str ):
		def decorator(f):
			setattr(f, "MATCH", name)
			return f
		return decorator

	def __init__( self, context:Optional[Context]=None ):
		self.matches:Dict[str,Callable[Intereter,Node,Iterable[Any]]] = {}
		self.context = context or Context()
		for name,value in inspect.getmembers(self):
			if hasattr(value, "MATCH"):
				self.matches[getattr(value, "MATCH")] = value
		self.init()

	def init( self ):
		pass

	def feed( self, node:Node ) -> Iterable[Any]:
		# TODO: Support namespace
		name = node.name
		func = self.matches.get(name)
		if func:
			result = func(node)
			if result is None:
				print (" ! None result for node", node)
			else:
				yield from result
		else:
			yield RuntimeError(f"Unsupported node type: {name}")

	def __call__( self, node:Node ) -> Iterable[Any]:
		yield from self.feed(node)

match = Interpreter.Match

# -----------------------------------------------------------------------------
#
# SEMANTICS
#
# -----------------------------------------------------------------------------

# TODO: Refine
#Invokable = Callable['Semantics', 'Any']

class Semantics:

	def evaluate( self, iterable:Iterable[Any] ) -> Any:
		res = None
		for v in iterable:
			if isinstance(v, RuntimeError):
				return v
			else:
				res = v
		return res

	def data( self, iterable:Iterable[Any] ) -> Any:
		res = None
		for v in iterable:
			if isinstance(v, RuntimeError):
				return v
			else:
				res = v
		return res

	def invoke( self, target:Any, args:Iterable[Any]):
		target = self.evaluate(target)
		if isinstance(target, RuntimeError):
			yield target
		else:
			yield from target(self, args)

# -----------------------------------------------------------------------------
#
# PRIMITIVES
#
# -----------------------------------------------------------------------------

class Primitives(Context):

	def __init__( self ):
		super().__init__()
		self.define("out!", self.do_out)
		self.define("import", self.do_import)
		self.seal()

	def do_out( self, semantics, args ):
		print ("out:", *(semantics.evaluate(_) for _ in args))
		yield None

	def do_import( self, semantics, args ):
		module  = next(args)
		symbols = [semantics.data(_) for _ in args]
		print ("import: ", module ,tuple(symbols))
		yield None

# -----------------------------------------------------------------------------
#
# BASE INTERPRETER
#
# -----------------------------------------------------------------------------

class BaseInterpreter(Interpreter):

	def init( self ):
		self.semantics = Semantics()
		self.context.parent = Primitives()
		self.symbols = Context()

	@match("expr-seq")
	def onSeq( self, node ):
		for child in node.children:
			yield from self.feed(child)

	@match("expr-list")
	def onInvocation( self, node ):
		args   = (self.feed(_) if i == 0 else _ for i,_ in enumerate(node.children))
		target = next(args)
		yield from self.semantics.invoke(target, args)

	@match("expr-value-symbol")
	def onSymbol( self, node ):
		name = node.attr("name")
		assert name, "Node should have a name"
		value = self.context.resolve(name)
		if not value:
			yield RuntimeError(f"Symbol '{name}' cannot be resolved")
		else:
			yield value

	@match("expr-value-string")
	def onString( self, node ):
		yield node.attr("value")

class DataInterpreter(Interpreter):
	"""Interprets nodes as a data"""

	@match("expr-seq")
	def onSeq( self, node ):
		yield [list(self.feed(_)) for _ in node.children]

	@match("expr-list")
	def onList( self, node ):
		yield [list(self.feed(_)) for _ in node.children]

	@match("expr-value-symbol")
	def onSymbol( self, node ):
		yield Symbol(node.attr("name"))

	@match("expr-value-string")
	def onString( self, node ):
		yield node.attr("value")

if __name__ == "__main__":
	import sys
	run = DataInterpreter()
	res = parseFile(sys.argv[1])
	for _ in run.feed(res):
		print (">>>", _)

# EOF - vim: ts=4 sw=4 noet
