from enum import Enum
from typing import Optional, Any, List, Dict
from collections import OrderedDict
from tlang.utils import NOTHING
from tlang.tree.model import Node

__doc__ = """
Defines a model to represent selector and queries.
"""


class Axis(Enum):
	SELF        = "."
	PARENT      = "\\"
	ANCESTORS   = "\\\\"
	CHILDREN    = "/"
	DESCENDANTS = "//"
	PREV        = "<"
	NEXT        = "<"
	AFTER       = ">>"
	BEFORE      = "<<"

class Predicate:
	"""An abstract class that defines a predicate, that might match
	a given context."""

	def __init__( self ):
		pass

	def match( self, node:Node ) -> bool:
		raise NotImplementedError

	def clone( self ):
		raise NotImplementedError

class NodeNamePredicate(Predicate):

	def __init__( self, name:str ):
		super().__init__()
		self.name = name

	def match( self, node:Node ) -> bool:
		return node.name == self.name

	def clone( self ):
		return self.__class__(self.name)

	def __str__( self ):
		return self.name

class AttributeNamePredicate(Predicate):

	def __init__( self, attribute:str ):
		super().__init__()
		self.attribute = attribute

	def match( self, node:Node ) -> bool:
		self.node.hasAttribute(self.attribute)

	def clone( self ):
		return self.__class__(self.attribute)

	def __str__( self ):
		return f"@{self.attribute}"

# TODO: ExternalPredicate
# TODO: {And,Or,Not}Predicate


# -----------------------------------------------------------------------------
#
# SELECTION
#
# -----------------------------------------------------------------------------

class Selection:
	"""Combines a predicate and an axis, and allows for chaining of
	selections, using `where` (to restrict) and `then` (to expand)."""

	# TODO: Add capture

	def __init__( self, axis:Axis, predicate:Predicate ):
		# The list of sub-selections
		self._then:List['Selection']  = []
		# The list of selections that must match
		self._where:List['Selection'] = []
		self.axis = axis
		self.predicate = predicate

	# =========================================================================
	# COMBINATORS
	# =========================================================================

	def where( self, selection:'Selection' ) -> 'Selection':
		"""Adds a selection that will filter out matching nodes for this
		selection."""
		self._where.append(selection)
		return self

	def then( self, selection:'Selection' ) -> 'Selection':
		"""Starts a new sub selection that uses matching nodes as root."""
		self._then.append(selection)
		return self

	def clone( self ):
		res = self.__class__(self.axis, self.predicate.clone())
		res._then = [_.clone() for _ in self._then]
		res._where = [_.clone() for _ in self._where]
		return res

	def __str__( self ):
		w = "".join(f"[{str(_)}]" for _ in self._where)
		t = "".join(str(_) for _ in self._then)
		return f"{self.axis.value if self.axis is not Axis.SELF else ''}{self.predicate}{w}{t}"

# -----------------------------------------------------------------------------
#
# API SUGAR
#
# -----------------------------------------------------------------------------

class Select:
	"""A friendly interface to creating selections"""

	@staticmethod
	def Self( predicate:Predicate ):
		return Selection(Axis.SELF, predicate)

	@staticmethod
	def Ancestors( predicate:Predicate ):
		return Selection(Axis.ANCESTORS, predicate)

	@staticmethod
	def Descendants( predicate:Predicate ):
		return Selection(Axis.DESCENDANTS, predicate)

	@staticmethod
	def Children( predicate:Predicate ):
		return Selection(Axis.CHILDREN, predicate)

class With:
	"""A friendly interface to creating predicates"""

	@staticmethod
	def Name( name:str ):
		return NodeNamePredicate(name)

	@staticmethod
	def Attribute( name:str ):
		return AttributeNamePredicate(name)

# EOF - vim: ts=4 sw=4 noet
