
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
		assert isinstance(name,str), f"Node name must be a string, got: {name}"
		self.name = name
		self.id   = Node.IDS ; Node.IDS += 1
		self.parent:Optional['Node'] = None
		# FIXME: This does not support namespaces for attributes
		self.attributes:Dict[str,Any] = OrderedDict()
		self._children:List['Node'] = []
		self.metadata:Optional[Dict[str,Any]] = None

	@property
	def head( self ) -> Optional['Node']:
		return self._children[0] if self._children else None

	@property
	def tail( self ) -> List['Node']:
		return self._children[1:]

	@property
	def children( self ) -> List['Node']:
		return self._children

	@property
	def childrenCount( self ) -> int:
		return len(self._children)

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
		return len(self._children) == 0

	@property
	def isNode( self ) -> bool:
		return len(self._children) > 0

	@property
	def hasAttributes( self ) -> bool:
		return len(self.attributes) > 0

	def hasAttribute( self, name:str ) -> bool:
		return name in self.attributes

	def setAttribute( self, name, value=None ):
		self.attributes[name] = value
		return self

	def attr( self, name, value=NOTHING ):
		if value is NOTHING:
			return self.attributes.get(name)
		else:
			self.attributes[name] = value
			return self

	def copy( self, depth=-1 ):
		"""Does a deep copy of this node. If a depth is given, it will
		stop at the given depth."""
		node = Node(self.name)
		self.attributes = type(self.attributes)((k,v) for k,v in self.attributes.items())
		if depth != 0:
			for child in self._children:
				node.append(child.copy(depth - 1))
		return node

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
		return self._children.index(node)

	def detach( self ) -> 'Node':
		if self.parent:
			self.parent.remove(self)
		return self

	def merge( self, node:'Node' ) -> 'Node':
		children = [_ for _ in node._children]
		for c in children:
			self.add(c.detach())
		return self

	def add( self, node:'Node' ) -> 'Node':
		assert isinstance(node, Node), f"Expected a Node, got: {node}"
		assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(self, node)
		node.parent = self
		self._children.append(node)
		return node

	def append( self, node:'Node') -> 'Node':
		return self.add(node)

	def extend( self, nodes:List['Node']) -> 'Node':
		for node in nodes:
			self.add(node.detach())
		return self

	def remove( self, node:'Node' ) -> 'Node':
		assert node.parent is self, "Cannot remove node from {0}, it has a different parent: {1}".format(self, node.parent)
		node.parent = None
		self._children.remove(node)
		return node

	def insert( self, index:int, node:'Node' ) -> 'Node':
		index = index if index >= 0 else len(self._children) + index
		assert index >=0 and index <= len(self._children), "Index out of bounds {0} in: {1}".format(index, self)
		assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(self, node)
		node.parent = self
		if index == len(self._children):
			self._children.append(node)
		else:
			self._children.insert(index, node)
		return node

	def walk( self, functor=None ):
		if not functor or functor(self) is not False:
			yield self
			for c in self._children:
				yield from c.walk(functor)

	def toPrimitive( self ):
		res   = [self.name]
		attr  = dict( (k,v) for k,v in self.attributes.items())
		if attr:
			res.append(attr)
		for _ in self._children:
			res.append(_.toPrimitive())
		return res

	def __getitem__( self, index:Union[int,str] ):
		if isinstance(index, str):
			if index not in self.attributes:
				raise IndexError(f"Node has no attribute '{index}': {self}")
			else:
				return self.attributes[index]
		else:
			return self._children[index]

	def toPrimtive(self):
		res = {"id":self.id}
		if self.name: res["name"] = self.name
		if self.parent: res["parent"] = self.parent.id
		if self.attributes: res["attributes"]  = self.attributes
		if self.metadata: res["metadata"]  = self.metadata
		if self._children: res["children"] = [_._asdict() for _ in self._children]
		return res

	def __str__( self ):
		return "".join(Repr.Apply(self))

	def __repr__( self ):
		return f"<Node:{self.name} {' '.join(str(k)+'='+repr(v) for k,v in self.attributes.items())}{' …' + str(len(self.children)) if self._children else ''}>"

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
	def Apply( cls, node, pretty=True, compact=False, depth=0 ):
		prefix = "  " * depth if pretty else ""
		if node.name == "#text":
			# Special handling of text nodes
			yield json.dumps(node["value"])
		else:
			yield prefix
			yield "("
			yield node.name
			if node.hasAttributes:
				for k,v in node.attributes.items():
					yield f" ({k}: "
					# TODO: We should support node references
					if isinstance(v, Node):
						yield "#{0}".format(v)
					else:
						yield json.dumps(v)
					yield ")"
			if not node.isLeaf and compact:
				yield " …"
			else:
				many_children = node.childrenCount
				for child in node.children:
					if pretty and many_children:
						yield "\n"
						yield prefix
					yield " "
					yield from cls.Apply(child, pretty=pretty, compact=compact, depth=depth + 1)
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

	def __getitem__( self, index:int ):
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
	def MakeNode( cls, nodeName, *content, **kwargs ):
		node = Node(nodeName)
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

	def node( self, nodeName, *content, **kwargs ):
		return self.MakeNode(nodeName, *content, **kwargs)

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
	PREFIX     = ""
	INSTANCE   = None

	@classmethod
	def Get( cls ):
		if not cls.INSTANCE:
			cls.INSTANCE = cls()
		return cls.INSTANCE

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
				self.matches[self.PREFIX + name[3:].replace("__",":").replace("_","-")] = value
		self.init()

	def init( self ):
		pass

	def process( self, node:Node ):
		res = None
		if isinstance(node, Iterable):
			for _ in node:
				for _ in self.feed(_):
					if isinstance(_, Exception):
						raise _
					else:
						res = _
		else:
			for _ in self.feed(node):
				if isinstance(_, Exception):
					raise _
				else:
					res = _
		return res

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
			yield from self.catchall(node)

	def run( self, node:Node, value=None ) -> Any:
		"""Like feed, but instead of returning an iterator will run through
		all the values and return the last one."""
		value = value
		for v in self.feed(node):
			value = v
		return value

	def catchall( self, node ) -> Iterable[Any]:
		yield TreeProcessorError(node, f"{self.__class__.__name__} does not support node type: {node.name}")

# NOTE: We might differenciate later
class TreeTransform(TreeProcessor):

	def catchall( self, node ):
		n = node.copy(0)
		for c in node.children:
			r = self.process(c)
			try:
				for _ in iter(r):
					yield _
			except TypeError as e:
				yield r
		yield n

	# TODO: The catchall might just be a copy?

class SemanticError(Exception):

	def __init__( self, message:str, hint=None ):
		super().__init__(message)
		self.hint = hint

class NodeError(Exception):

	def __init__( self, node:Node, error:Exception, hint=None ):
		self.node = node
		self.error = error
		self.hint = hint or (error.hint if error and hasattr(error, "hint") else None)

	def __str__( self ):
		return f"{self.error} in {self.node}"

# EOF - vim: ts=4 sw=4 noet
