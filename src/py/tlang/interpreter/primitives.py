from .model import Context,Channel,Argument,Rest,invocation,EAGER,LAZY,VALUE,DATA,NODE
from tlang.tree.model import NodeError,Node
from collections import OrderedDict
from typing import Iterator,Iterable,Any,List
import math

# TLang primitives are defined as a context to which are bound implementations
# implemented as part of th eruntime. Each primitive is decorated with
# `@invocation` to define the *invocation protocol*, specifying how the
# arguments should be handled at the call site.
#
# This makes it possible to implement primitives that have to do lazy
# evaluation or primitives that need to process the AST and not its
# evaluation.
#
# EAGER evaluation with return runtime values (in Python), LAZY evaluations will
# return a generator that yields either runtime values or anothe generator,
# NODE will return the AST nodes and DATA will return the AST as a data
# structure (ie. as a runtime value).
class Primitives:

	def bind( self, context ):
		# Core operations
		context.define("let",        self.do_let)
		context.define("set!",       self.do_set)

		# Channel
		context.define("lazy",       self.do_lazy)
		context.define("next",       self.do_next)
		context.define("next?",      self.do_hasNext)
		context.define("skip",       self.do_skip)

		# Constructors
		context.define("list",       self.do_list)
		context.define("dict",       self.do_dict)
		context.define("tree",       self.do_tree)

		# Helpers
		context.define("primitive",  self.do_primitive)
		context.define("out!",       self.do_out)
		context.define("lambda",     self.do_lambda)

		# Collections
		context.define("map",        self.do_map)
		context.define("filter",     self.do_filter)
		context.define("reduce",     self.do_reduce)

		# Logic
		context.define("and",        self.do_and)
		context.define("or",         self.do_or)
		# NOTE: Cond could probably be abstracted out
		context.define("cond",         self.do_cond)

		# Math
		context.define("add",        self.do_add)
		context.define("sub",        self.do_sub)
		context.define("mul",        self.do_mul)
		context.define("div",        self.do_div)
		context.define("floor",      self.do_floor)
		context.define("ceil",       self.do_ceil)
		context.define("round",      self.do_round)
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

	@invocation( __=EAGER )
	def do_tuple( self, interpreter, args ):
		return tuple(_ for _ in args)

	@invocation( __=EAGER )
	def do_list( self, interpreter, args ):
		return [_ for _ in args]

	@invocation( __=NODE )
	def do_dict( self, interpreter, args ):
		count = 0
		expect_value = False
		res = {}
		for node in args:
			if expect_value:
				value = interpreter.run(node)
				res[key] = value
				expect_value = False
			elif node.name == "ex:key":
				key = node["name"]
				expect_value = True
			else:
				key = count
				value = interpreter.run(node)
				res[key] = value
		return res

	@invocation( value=NODE )
	def do_tree( self, interpreter, args ):
		# The tree primitive simply forwards the evaluation of the AST
		# to the tree interpreter.
		return interpreter.treeInterpreter.run(args[0])

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

	@invocation( a=EAGER, b=EAGER )
	def do_sub( self, interpreter, args ):
		a, b = args
		return a - b

	@invocation( a=EAGER, b=EAGER )
	def do_mul( self, interpreter, args ):
		a, b = args
		return a * b

	@invocation( a=EAGER, b=EAGER )
	def do_div( self, interpreter, args ):
		a, b = args
		return float(a) / (b or 1)

	@invocation( a=EAGER )
	def do_floor( self, interpreter, args ):
		return int(math.floor(args[0]))

	@invocation( a=EAGER )
	def do_ceil( self, interpreter, args ):
		return int(math.ceil(args[0]))

	@invocation( a=EAGER )
	def do_round( self, interpreter, args ):
		return int(round(args[0]))

	@invocation( a=EAGER, b=LAZY )
	def do_or( self, interpreter, args ):
		a, b = args
		return b if not a else a

	@invocation( __=NODE )
	def do_cond( self, interpreter, args ):
		for node in args:
			value = None
			if node.isEmpty:
				# NOTE: We might raise a warning here for a malformed
				# cond.
				continue
			# We evaluate the
			value = interpreter.run(node.head, value)
			if value:
				for rest in node.tail:
					value = interpreter.run(rest, value)
				return value
		return None

	@invocation( a=EAGER, b=LAZY )
	def do_and( self, interpreter, args ):
		a, b = args
		return b if a else a

	@invocation( name=NODE, value=EAGER )
	def do_set( self, interpreter, args:Iterable[Node] ):
		"""Of the form `(set! SYMBOL VALUE)`"""
		if len(args) < 2:
			raise RuntimeError("set! has a form (set! SYMBOL VALUE)")
		name, value = args
		# TODO: It could also be a list which would attach attributes
		# to the slot, we need to support that.
		name = name.attr("name")
		# We access the parent context as the subcontext is the attributes
		interpreter.context.parent.define(name, value)
		return value

	@invocation( __=NODE )
	def do_let( self, interpreter, args:Iterable[Node] ):
		"""Of the form `(let (SYMBOL VALUE)… VALUE)`, eagerly evaluates the
		values in the `(SYMBOL VALUE)` pairs and binds them to the corresponding
		`SYMBOL` in the context. Yields the evaluation of the last `VALUE`."""
		if len(args) < 2:
			raise RuntimeError("Let has a form (let (SYMBOL VALUE)… VALUE))")
		# We create a subcontext
		# TODO: We should capture the node as well
		interpreter.pushContext(("let",))
		# We bind the values in the context
		for node in args[:-1]:
			# Expected (expr-value-symbol *)
			name  = node.children[0].attr("name")
			# NOTE: This is a letrec as the scope is the current derived
			# interpreter.
			# FIXME: This should probably be the first node that is not a comment
			value = None
			for v in interpreter.feed(node.children[1]):
				value = v
			if isinstance(value, RuntimeError):
				yield RuntimeError(f"Could not define symbol '{name}' because: {value}")
			else:
				interpreter.context.define(name, value)
		yield from interpreter.feed(args[-1])
		interpreter.popContext()

	@invocation( collection=EAGER, functor=EAGER )
	def do_map( self, interpreter, args:List[Any] ):
		l, f = args
		return [f(v,i) for i,v in enumerate(l)]

	@invocation( collection=EAGER, functor=EAGER )
	def do_filter( self, interpreter, args:List[Any] ):
		l, f = args
		return [v for i,v in enumerate(l) if f(v,i)]

	@invocation( collection=EAGER, functor=EAGER )
	def do_reduce( self, interpreter, args:List[Any] ):
		l, f, r = args
		for i,v in enumerate(l):
			r = f(r,v,i)
		return r

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
