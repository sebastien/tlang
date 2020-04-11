from .model import Context,Argument,Singleton,META_INVOCATION,NODE,DATA,LAZY
from tlang.tree.model import TreeTransform,TreeProcessor,TreeBuilder,NodeError,SemanticError,Node
from typing import List,Dict,Optional,Any

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
		self.treeInterpreter = treeInterpreter or TreeInterpreter()

	def pushContext( self ):
		self.context = Context(self.context)
		return self.context

	def popContext( self ):
		res = self.context
		self.context = self.context.parent
		return res

	def derive( self ):
		return self.__class__(self.context.derive(), self.literalInterpreter, self.treeInterpreter)

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
			if not hasattr(target, META_INVOCATION):
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
			raise NodeError(node, SemanticError(f"Cannot resolve symbol: '{name}' in {node}\n ↳ slots: {','.join(sorted(self.context.listReachableSlots()))}"))
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
		self.pushContext()
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

	def on_ex__list( self, node ):
		print ("XXX", node)
		head = node.head
		node_name = self.process(node.head)
		res = Node(node_name)
		for child in node.tail:
			print ("CHILD", self.process(child))
		return res

	def on_ex__ref( self, node ):
		return node["name"]

	def on__q_query( self, node ):
		print ("QUERY", node)
		return None

# EOF - vim: ts=4 sw=4 noet
