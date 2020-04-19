from .model import Context,Argument,Singleton,META_INVOCATION,NODE,DATA,LAZY
from tlang.tree.model import TreeTransform,TreeProcessor,TreeBuilder,NodeError,SemanticError,Node
from typing import List,Dict,Optional,Any,Callable

# -----------------------------------------------------------------------------
#
# INTERPRETERS
#
# -----------------------------------------------------------------------------

class ValueInterpreter(TreeProcessor):
	"""Creates processes out of definitions."""

	PREFIX = "ex:"

	def __init__( self, context:Context=None, literalInterpreter=None, treeInterpreter=None ):
		super().__init__()
		self.context:Context = context or Context()
		self.literalInterpreter = literalInterpreter or LiteralInterpreter()
		# NOTE: The tree interpreter needs a reference to the value interpreter
		# as the tree can have template expressions.
		self.treeInterpreter = treeInterpreter or TreeInterpreter(self)

	def pushContext( self, reference ):
		self.context = Context(self.context).setReference(reference)
		return self.context

	def popContext( self ):
		res = self.context
		self.context = self.context.parent
		return res

	def derive( self, reference ):
		return self.__class__(self.context.derive(reference), self.literalInterpreter, self.treeInterpreter)

	#NOTE: This is a direct invocation
	#TODO: @on("(list (name (@ (name A))) … REST)")
	def on_list( self, node ):
		if not node.children:
			# This is a runtime value
			return []
		else:
			target = self.process(node.children[0])
			# NOTE: We do eager evaluation here
			raw_args = [_ for _ in node.children[1:]]
			if target is None:
				raise NodeError(node.children[0], SemanticError("Target resolved to None"))
			elif not isinstance(target, Callable):
				raise NodeError(node, SemanticError(f"Invocation target is not a function or invocable, got: {target}"))
			elif not hasattr(target, META_INVOCATION):
				raise NodeError(node, SemanticError("Invocation target is missing invocation protocol meta-information"))
			else:
				protocol = getattr(target, META_INVOCATION)
				return self.invoke(target, protocol, raw_args)

	def on_seq( self, node ):
		for _ in node.children:
			for _ in self.feed(_):
				if isinstance(_, Exception):
					raise _

	def on_comment( self, node ):
		return node

	def on_ref( self, node ):
		return self.on_name(node)

	def on_name( self, node ):
		name = node["name"]
		res = self.context.resolve(name)
		if res is None:
			import ipdb;ipdb.set_trace()
			raise NodeError(node, SemanticError(
				f"Cannot resolve symbol '{name}'",
				f"reachable slots are: {','.join(sorted(self.context.listReachableSlots()))}"))
		else:
			return res

	def on_string( self, node ):
		return node["value"]

	def on_number( self, node ):
		return node["value"]

	def on_quote( self, node ):
		# (quote (1 2 3)) returns (1 2 3)
		# (quote (1 2 3) (4 5)) returns ((1 2 3) (4 5))
		# FIXME: This should actually be a primitive, as (quote …) should have
		# the same effect.
		return self.literalInterpreter.process(node.head) if len(node.children) == 1 else [self.literalInterpreter.process(_) for _ in node.children]

	def invoke( self, target, protocol:'Arguments', args:List[Any] ):
		"""Performs an invocation of the target using the given arguments.
		This will use the protocol information in order to determine what to
		do with the arguments, which can be passed a raw AST, AST as data or
		AST as value, and evaluated lazily or eagerly."""
		argv = []
		j    = len(protocol) - 1
		# Here we iterate through the arguments, extract the corresponding
		# protocol information and process the arguments accordingly.
		self.pushContext(("invocation", target))
		inter = self
		has_rest = protocol and protocol[-1].name == "__"
		# We skip comments from invocations, but they're still part
		# of the AST.
		for i, arg_node in enumerate(_ for _ in args if _.name != "ex:comment"):
			if not has_rest and i > j:
				# We skip any extra argument, but only if
				# there is no __ (rest) argument in the
				# protocol.
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
				if arg_meta.name != "__":
					self.context.define(arg_meta.name, value)
				argv.append(value)
		res = target(self, argv)
		self.popContext()
		return res

class LiteralInterpreter(TreeTransform):
	"""Evaluates the AST to a primitive structure"""

	PREFIX = "ex:"

	def on_list( self, node ):
		return [self.process(_) for _ in node.children] if node.children else []

	def on_name( self, node ):
		return node["value"]

	def on_singleton( self, node ):
		return Singleton.Get(node["name"][1:])

	def on_string( self, node ):
		return node["value"]

	def on_number( self, node ):
		return node["value"]

class TreeInterpreter(TreeTransform):
	"""Evaluates the AST to form a TLang tree"""

	def __init__( self, valueInterpreter:ValueInterpreter ):
		super().__init__()
		self.valueInterpreter = valueInterpreter

	def isListAttribute( self, node ):
		# NOTE: This doesn't work for something like
		# ({pick((list a: b: c: d:))} 1.0)
		return node.name == "ex:list" and len(node.children) >= 1 and len(node.children) <= 2 and node.head.name == "ex:key"

	def on_ex__list( self, node ):
		head = node.head
		# An empty list in a tree leads to nothing
		if not head:
			return None
		# If the first node is a key, then we have a list of
		# attributes (ie. it's a map)
		elif head.name == "ex:key":
			return []
		# If it's a reference, then we have a node
		# attributes (ie. it's a map)
		elif head.name == "ex:ref":
			res = Node(self.process(head))
			for child in node.tail:
				if self.isListAttribute(child):
					# TODO: We should probably interpret the value if it's
					# not a key.
					head = child.head
					assert head.name == "ex:key"
					if len(child.children) == 1:
						res.attr(head["name"], None)
					else:
						res.attr(head["name"], self.process(child[1]))
				else:
					value = self.process(child)
					res.add(Node("#text").attr("value", value) if isinstance(value, str) else value)
			return res

	def on_ex__template( self, node ):
		# We have a template node, and we need to expand it
		if len(node.children) == 0:
			return None
		elif len(node.children) == 1:
			return self.valueInterpreter.run(node.head)
		else:
			return [self.valueInterpreter.run(_) for _ in node.children]

	def on_ex__ref( self, node ):
		return node["name"]

	def on_ex__key( self, node ):
		return node["name"]

	def on_ex__string( self, node ):
		return node["value"]


	def on__q_query( self, node ):
		print ("QUERY", node)
		return None

# EOF - vim: ts=4 sw=4 noet
