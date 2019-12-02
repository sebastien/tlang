
from typing import Optional,Any,List,Dict,Union,Iterator,Iterable,Callable
from collections import OrderedDict
from tlang.utils import NOTHING
import json, inspect

# TODO: XML and JSON interop
# TODO: Source reference as attributes
# TODO: Nice tree formatter

__doc__ = """
The core model representing trees and nodes.
"""

# TODO: The operations should probably be made by a manipulator, and the
# core data structure should be kept as minimal as possible.

# -----------------------------------------------------------------------------
#
# NODE
#
# -----------------------------------------------------------------------------

class Node:
	"""A node is an uniquely identified, named object with zero or one parent,
	a set of attributes and a list of children."""

	IDS = 0

	def __init__( self, name:str ):
		# FIXME: This does not support namespace
		self.name = name
		self.id   = Node.IDS ; Node.IDS += 1
		self.parent:Optional['Node'] = None
		# FIXME: This does not support namespaces for attributes
		self.attributes:Dict[str,Any] = OrderedDict()
		self.children:List['Node'] = []
		self.metadata:Optional[Dict[str,Any]] = None

	@property
	def root( self ) -> Optional['Node']:
		root   = None
		parent = self.parent
		while parent:
			root = parent
			parent = parent.parent
		return root

	@property
	def isTree( self ) -> bool:
		return not self.parent

	@property
	def isEmpty( self ) -> bool:
		return self.isLeaf and not self.hasAttributes

	@property
	def isSubtree( self ) -> bool:
		return bool(self.parent)

	@property
	def isLeaf( self ) -> bool:
		return len(self.children) == 0

	@property
	def isNode( self ) -> bool:
		return len(self.children) > 0

	@property
	def hasAttributes( self ) -> bool:
		return len(self.attributes) > 0

	def hasAttribute( self, name:str ) -> bool:
		return name in self.attributes

	def attr( self, name, value=NOTHING ):
		if value is NOTHING:
			return self.attributes.get(name)
		else:
			self.attributes[name] = value
			return self

	def meta( self, name:str, value=NOTHING ):
		"""Sets/accesses the node's metadata."""
		if value is NOTHING:
			return self.metadata.get(name) if self.metadata else None
		else:
			if not self.metadata:
				self.metadata = {name:value}
			else:
				self.metadata[name] = value
			return self

	def index( self, node ) -> int:
		return self.children.index(node)

	def detach( self ) -> 'Node':
		if self.parent:
			self.parent.remove(self)
		return self

	def merge( self, node:'Node' ) -> 'Node':
		children = [_ for _ in node.children]
		for c in children:
			self.add(c.detach())
		return self

	def add( self, node:'Node' ) -> 'Node':
		assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(self, node)
		node.parent = self
		self.children.append(node)
		return node

	def remove( self, node:'Node' ) -> 'Node':
		assert node.parent is self, "Cannot remove node from {0}, it has a different parent: {1}".format(self, node.parent)
		node.parent = None
		self.children.remove(node)
		return node

	def insert( self, index:int, node:'Node' ) -> 'Node':
		index = index if index >= 0 else len(self.children) + index
		assert index >=0 and index <= len(self.children), "Index out of bounds {0} in: {1}".format(index, self)
		assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(self, node)
		node.parent = self
		if index == len(self.children):
			self.children.append(node)
		else:
			self.children.insert(index, node)
		return node

	def walk( self, functor ):
		return self._walk(self, functor)

	def _walk( self, node, functor ):
		if functor(node) is False:
			return False
		for c in node.children:
			if self._walk(c, functor) is False:
				return False
		return True

	def toPrimitive( self ):
		res   = [self.name]
		attr  = dict( (k,v) for k,v in self.attributes.items())
		if attr:
			res.append(attr)
		for _ in self.children:
			res.append(_.toPrimitive())
		return res

	def __str__( self ):
		return "".join(Repr.Apply(self))


# -----------------------------------------------------------------------------
#
# NODE TEMPLATE
#
# -----------------------------------------------------------------------------

# TODO: Shouldn't we wrap/compose nodes instead?
class NodeTemplate(Node):
	pass

# -----------------------------------------------------------------------------
#
# REPR
#
# -----------------------------------------------------------------------------

class Repr:
	"""Generates a text-based representation of a given node."""

	@classmethod
	def Apply( cls, node, pretty=True, depth=0 ):
		prefix = "  " * depth if pretty else ""
		yield prefix
		yield "("
		yield node.name
		if node.hasAttributes:
			yield " (@ "
			for k,v in node.attributes.items():
				yield " ("
				yield str(k)
				yield " "
				# TODO: We should support node references
				if isinstance(v, Node):
					yield "#{0}".format(v)
				else:
					yield json.dumps(v)
				yield ")"
			yield ")"
		for child in node.children:
			if pretty:
				yield "\n"
			yield prefix
			yield " "
			yield from cls.Apply(child, pretty, depth + 1)
		yield ")"


# -----------------------------------------------------------------------------
#
# ADAPTER
#
# -----------------------------------------------------------------------------

class Adapter:
	"""Adapters compose/wrap a TLang node and expose it following another
	API, such as the DOM."""

	@classmethod
	def Wrap( cls, node:Union[Node,'Adapter'] ) -> 'Adapter':
		return cls(node) if isinstance(node, Node) else node

	@classmethod
	def Unwrap( cls, adapter:'Adapter' ) -> Node:
		return adapter.node if isinstance(node, Adapter) else adapter

	def __init__( self, node:Node ):
		self.node = node

	def wrap( self, node:Node ) -> 'Adapter':
		self.node = node
		return self

# -----------------------------------------------------------------------------
#
# DOM ADAPTER
#
# -----------------------------------------------------------------------------

class DOMAdapter(Adapter):

	def appendChild( self, node:Node ) -> Node:
		return self.node.add(node)

	def removeChild( self, node:Node ) -> Node:
		return self.node.remove(node)

	def insertBefore( self, node:Node ) -> Node:
		i = self.node.index(node)
		assert i >= 0, "Cannot find node {0} in {1}".format(node, self.node)
		self.node.insert(i, node)
		return node


# -----------------------------------------------------------------------------
#
# OBEJCT ADAPATER
#
# -----------------------------------------------------------------------------

class ObjectAdapter(Adapter):
	"""Wraps a node so that you can use it as an object, where properties
	are mapped to attributes and items to child nodes."""

	def __getattribute__( self, name:str ):
		if name == "node" or name == "wrap":
			return super().__getattribute__(name)
		else:
			return node.attr(name)

	def __setattr__( self, name:str, value:Any ):
		if name == "node" or name == "wrap":
			return super().__setattr__(name)
		else:
			return node.attr(name, value)

	def __get_item__( self, index:int ):
		return self.node.children[index]

	def __len__( self ):
		return len(self.node.children)

# -----------------------------------------------------------------------------
#
# TREE BUILDER
#
# -----------------------------------------------------------------------------

class TreeBuilder:

	@classmethod
	def MakeNode( cls, name, *content, **kwargs ):
		node = Node(name)
		for k,v in kwargs.items():
			node.attr(k,v)
		if not content:
			return node
		head = content[0]
		if isinstance(head, dict) or isinstance(head, OrderedDict):
			content = content[1:]
			for k in head:
				v = head[k]
				# TODO: Validate schema
				node.attr(k, v)
		for child in content:
			if isinstance(child, Iterable):
				for c in child:
					if c is not None:
						node.add(c)
			else:
				if child is not None:
					node.add(child)
		return node

	def node( self, name, *content, **kwargs ):
		return self.MakeNode(name, *content, **kwargs)

# -----------------------------------------------------------------------------
#
# TREE PROCESSOR
#
# -----------------------------------------------------------------------------

class TreeProcessorError(Exception):

	def __init__( self, node, error ):
		self.node = node
		self.error = error

	def __str__( self ):
		return f"{self.error} in {self.node}"

class TreeProcessor:

	META_MATCH = "__tlang_model_treebuilder_match"

	@staticmethod
	def Match( name:str ):
		def decorator(f):
			setattr(f, TreeProcessor.META_MATCH, name)
			return f
		return decorator

	def __init__( self ):
		self.matches:Dict[str,Callable[TreeProcessor,Node,Iterable[Any]]] = {}
		self.node:Optional[Node] = Node
		for name,value in inspect.getmembers(self):
			if hasattr(value, TreeProcessor.META_MATCH):
				self.matches[getattr(value, TreeProcessor.META_MATCH)] = value
			elif name.startswith("on_"):
				self.matches[name[3:]] = value
		self.init()

	def init( self ):
		pass

	def build( self, node:Node ):
		res = []
		if isinstance(node, Iterable):
			for _ in node:
				for _ in self.feed(_):
					pass
		else:
			for _ in self.feed(node):
				pass
		return self

	def feed( self, node:Node ) -> Iterable[Any]:
		# TODO: Support namespace
		name = node.name
		func = self.matches.get(name)
		self.node = node
		if func:
			result = func(node)
			if result is None:
				pass
			elif isinstance(result, Iterator):
				yield from result
			elif isinstance(result, Exception):
				yield TreeProcessorError(node, result)
			else:
				yield result
		else:
			yield TreeProcessorError(node, f"Unsupported node type: {name}")

class NodeError(Exception):

	def __init__( self, node:Node, error:Exception ):
		self.node = node
		self.error = error

	def __str__( self ):
		return f"{self.error} in {self.node}"

# EOF - vim: ts=4 sw=4 noet
