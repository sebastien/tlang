from .model import Context,Argument,Rest,invocation,EAGER,VALUE,DATA,NODE
from tlang.tree.model import NodeError
from collections import OrderedDict
from typing import Iterator,Any

class Primitives:

	def bind( self, context ):
		context.define("out!",   self.do_out)
		context.define("lambda", self.do_lambda)
		context.define("add",    self.do_add)
		context.define("primitive",  self.do_primitive)
		return self

	@invocation( __=EAGER )
	def do_primitive( self, interpreter, args ):
		print ("TODO:primitive",*args)


	@invocation( __=EAGER )
	def do_out( self, interpreter, args ):
		print (*args)

	@invocation( a=EAGER, b=EAGER )
	def do_add( self, interpreter, args ):
		a, b = args
		return a + b
	# @invocation( iterable=VALUE|EAGER, functor=VALUE|EAGER )
	# def do_iter( self, interpreter:Interpreter, args:Iterator[Value] ):
	# 	"""Iterates through an iterable value. Stops when receiving the symbol `:Stop`"""
	# 	value   = args[0]
	# 	functor = args[1]
	# 	if isinstance(functor, Symbol):
	# 		# We do iterate, even if there's a no-op
	# 		for _ in value:
	# 			pass
	# 	else:
	# 		for i,v in enumerate(value):
	# 			interpreter.invoke(functor, (v,i))
	# 	yield None

	# @invocation( __=DATA|EAGER )
	# def do_primitive( self, interpreter:Interpreter, args:Iterator[Value] ):
	# 	missing = []
	# 	for prim in args:
	# 		assert isinstance(prim, Symbol)
	# 		if not self.has(prim.name):
	# 			missing.append(prim.name)
	# 	if missing:
	# 		yield RuntimeError(f"Undefined primitives {missing}")
	# 	else:
	# 		yield None

	# @invocation( __=NODE )
	# def do_let( self, interpreter:Interpreter, args:Iterator[Value] ):
	# 	"""Of the form `(let (SYMBOL VALUE)… VALUE)`, eagerly evaluates the
	# 	values in the `(SYMBOL VALUE)` pairs and binds them to the corresponding
	# 	`SYMBOL` in the context. Yields the evaluation of the last `VALUE`."""
	# 	if len(args) < 2:
	# 		raise RuntimeError("Let has a form (let (SYMBOL VALUE)… VALUE))")
	# 	i      = interpreter.derive()
	# 	for node in args[:-1]:
	# 		# Expected (expr-value-symbol *)
	# 		name  = node.children[0].attr("name")
	# 		# NOTE: This is a letrec as the scope is the current derived
	# 		# interpreter.
	# 		# FIXME: This should probably be the first node that is not a comment
	# 		value = expand(i.feed(node.children[1]))
	# 		if isinstance(value, RuntimeError):
	# 			yield RuntimeError(f"Could not define symbol '{name}' because: {value}")
	# 		else:
	# 			i.context.define(name, value)
	# 	yield from i.feed(args[-1])

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
		print ("KWARGS", kwargs)
		# We yield the decorated functor
		yield invocation( **kwargs )(functor)

# EOF - vim: ts=4 sw=4 noet
