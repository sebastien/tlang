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

	def __init__( self ):
		pass

	def match( self, node:Node ) -> bool:
		raise NotImplementedError

class NodeNamePredicate(Predicate):

	def __init__( self, attribute:str ):
		super().__init__()
		self.attribute = attribute

	def match( self, node:Node ) -> bool:
		self.node.name == self.attribute

class AttributeNamePredicate(Predicate):

	def __init__( self, attribute:str ):
		super().__init__()
		self.attribute = attribute

	def match( self, node:Node ) -> bool:
		self.node.hasAttribute(self.attribute)

# TODO: ExternalPredicate
# TODO: {And,Or,Not}Predicate


# -----------------------------------------------------------------------------
#
# SELECTION
#
# -----------------------------------------------------------------------------

class Selection:

	def __init__( self, axis:Axis, predicate:Predicate ):
		# The list of sub-selections
		self._then:List['Selection']  = []
		# The list of selections that must match
		self._where:List['Selection'] = []
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

# -----------------------------------------------------------------------------
#
# API SUGAR
#
# -----------------------------------------------------------------------------

class Select:

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
	"""A friendly interface to the predicates"""

	@staticmethod
	def Name( name:str ):
		return NodeNamePredicate(name)

	@staticmethod
	def Attribute( name:str ):
		return AttributeNamePredicate(name)

# EOF - vim: ts=4 sw=4 noet
