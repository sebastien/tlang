
from typing import Optional, Any, List, Dict
from collections import OrderedDict
from tlang.utils import NOTHING

# TODO: XML and JSON interop

__doc__ = """
The core model representing trees and nodes.
"""

class Node:

	def __init__( self, name:str ):
		self.name = name
		self.parent:Optional['Node'] = None
		self.attributes:Dict[str,Any] = OrderedDict()
		self.children:List['Node'] = []

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

	def attr( self, name, value=NOTHING ):
		if value is NOTHING:
			return self.attributes.get(name)
		else:
			self.attributes[name] = value
			return self

	def index( self, node ) -> int:
		return self.children.index(node)

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
		assert index >=0 and index < len(self.children), "Index out of bounds {0} in: {1}".format(index, self)
		assert not node.parent, "Cannot add node to {0}, it already has a parent: {1}".format(self, node)
		node.parent = self
		self.children.insert(index, node)
		return node

	def __str__( self ):
		return "".join(Repr.Apply(self))

class NodeTemplate(Node):
	pass

class Repr:

	@classmethod
	def Apply( cls, node ):
		yield "("
		yield node.name
		if node.hasAttributes:
			yield " (@ "
			for k,v in node.attributes.items():
				yield " ("
				yield str(k)
				yield " "
				yield str(v)
				yield ")"
			yield ")"
		for child in node.children:
			yield " "
			yield from cls.Apply(child)
		yield ")"

class Adapter:

	def __init__( self, node:Node ):
		self.node = node

	def wrap( self, node:Node ) -> 'Adapter':
		self.node = node
		return self

class DOMAdapter(Adapter):

	def appendChild( self, node:Node ):
		return self.node.add(node)

	def removeChild( self, node:Node ):
		return self.node.remove(node)

	def insertBefore( self, node:Node ):
		i = self.node.index(node)
		assert i >= 0, "Cannot find node {0} in {1}".format(node, self.node)
		self.node.insert(i, node)
		return node

# EOF - vim: ts=4 sw=4 noet
