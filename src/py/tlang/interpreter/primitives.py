from .model import Context,Channel,Argument,Rest,invocation,EAGER,VALUE,DATA,NODE
from tlang.tree.model import NodeError,Node
from collections import OrderedDict
from typing import Iterator,Iterable,Any

class Primitives:

	def bind( self, context ):
		# Core operations
		context.define("let",        self.do_let)

		# Channel
		context.define("lazy",       self.do_lazy)
		context.define("next",       self.do_next)
		context.define("next?",      self.do_hasNext)
		context.define("skip",       self.do_skip)

		# Helpers
		context.define("primitive",  self.do_primitive)
		context.define("out!",       self.do_out)
		context.define("lambda",     self.do_lambda)

		# Math
		context.define("add",        self.do_add)
		return self

	@invocation( __=DATA|EAGER )
	def do_primitive( self, interpreter, args:Iterable[Node] ):
		missing = []
		for prim in args:
			# FIXME: For some reason, the ex:ref have no 
			# attributes, but they should.
			if prim.name == "ex:ref":
				pass
				# name = prim["name"]
				# if not self.has(name):
				# 	missing.append(name)
		if missing:
			yield RuntimeError(f"Undefined primitives {missing}")
		else:
			yield None

	@invocation( __=NODE )
	def do_lazy( self, interpreter, args ):
		"""Returns a pre-populated channel with lazy evaluations
		of the given arguments."""
		chan = Channel()
		for node in args:
			# NOTE: We need to close over the context
			chan.writeLazy(lambda n=node, interp=interpreter: interp.process(n))
		return chan

	@invocation( __=EAGER )
	def do_out( self, interpreter, args ):
		print (*args)

	@invocation( value=EAGER )
	def do_next( self, interpreter, args ):
		chan = args[0]
		if isinstance(chan, Channel):
			if chan.count > 0:
				return chan.read()
			else:
				# TODO: We should raise an exception
				return None
		else:
			return None

	@invocation( value=EAGER )
	def do_skip( self, interpreter, args ):
		chan = args[0]
		if isinstance(chan, Channel):
			if chan.count > 0:
				return chan.consume()
			else:
				# TODO: We should raise an exception
				return None
		else:
			return None

	@invocation( value=EAGER )
	def do_hasNext( self, interpreter, args ):
		chan = args[0]
		if isinstance(chan, Channel):
			return chan.count > 0
		else:
			return False

	@invocation( a=EAGER, b=EAGER )
	def do_add( self, interpreter, args ):
		a, b = args
		return a + b

	@invocation( __=NODE )
	def do_let( self, interpreter, args:Iterable[Node] ):
		"""Of the form `(let (SYMBOL VALUE)… VALUE)`, eagerly evaluates the
		values in the `(SYMBOL VALUE)` pairs and binds them to the corresponding
		`SYMBOL` in the context. Yields the evaluation of the last `VALUE`."""
		if len(args) < 2:
			raise RuntimeError("Let has a form (let (SYMBOL VALUE)… VALUE))")
		# We create a subcontext
		interp = interpreter.derive()
		# We bind the values in the context
		for node in args[:-1]:
			# Expected (expr-value-symbol *)
			name  = node.children[0].attr("name")
			# NOTE: This is a letrec as the scope is the current derived
			# interpreter.
			# FIXME: This should probably be the first node that is not a comment
			value = None
			for v in interp.feed(node.children[1]):
				value = v
			if isinstance(value, RuntimeError):
				yield RuntimeError(f"Could not define symbol '{name}' because: {value}")
			else:
				interp.context.define(name, value)
		yield from interp.feed(args[-1])

	# FIXME: Lambda should be rewritten using channels.
	@invocation( args=NODE, __=NODE )
	def do_lambda( self, interpreter, args:Iterator[Any] ):
		# We extrat the function arguments
		func_args = []
		for i,arg in enumerate(args[0].children):
			# FIXME: We only support ex:ref arguments for now 
			if arg.name == "ex:ref":
				# TODO: This is where we can extract form and type of evaluation
				func_args.append(Argument(arg.attr("name"), i))
			elif arg.name == "ex:rest":
				# TODO: This is where we can extract form and type of evaluation
				func_args.append(Rest(arg.attr("name") or "__", i))
			else:
				raise NodeError(arg, ValueError("Node type not supported as argument"))
		# This is the actual execution of the function
		func_code = args[1:]
		def functor(interpreter, args):
			# The functor creates a new context
			interp = interpreter.derive()
			# Maps out the function arguments
			for i,arg in enumerate(func_args):
				# NOTE: Not sure what args are at this stage
				value = args[i]
				if isinstance(value, RuntimeError):
					yield RuntimeError(f"Cannot bind argument {i} '{arg.name}', because: {value}")
				else:
					# We define the slots of the arguments
					interp.context.define(arg.name, value)
			# We re-interpret the nodes in the context
			for ast_node in func_code:
				yield from interp.feed(ast_node)
		# We define the invocation protocol, which is always eager, for now.
		kwargs = OrderedDict()
		for ref in func_args:
			kwargs[ref.name] = EAGER|VALUE
		# We yield the decorated functor
		yield invocation( **kwargs )(functor)

# EOF - vim: ts=4 sw=4 noet
