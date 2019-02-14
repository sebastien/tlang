
from typing import Optional, Any, List, Dict
from collections import OrderedDict
from tlang.utils import NOTHING

__doc__ = """
The core model representing selectors
"""

# -----------------------------------------------------------------------------
#
# VALUES
#
# -----------------------------------------------------------------------------

class Literal:
	pass

class Number(Literal):
	pass

class String(Literal):
	pass

# -----------------------------------------------------------------------------
#
# NODE/ATTRIBUTE PATTERN
#
# -----------------------------------------------------------------------------

class Predicate:
	pass

class IsNode(Predicate):
	pass

class IsNodeLike(Predicate):
	pass

class IsAttribute(Predicate):
	pass

class IsAttributeLike(Predicate):
	pass

class Constraint(Predicate):
	pass

# -----------------------------------------------------------------------------
#
# AXIS
#
# -----------------------------------------------------------------------------

class Axis:

	def __init__( self, depth:int=-1 ):
		pass

class Descendants(Axis):
	SYMBOL = "/"

class Ancestors(Axis):
	SYMBOL = "\\"

class NextSiblings(Axis):
	SYMBOL = ">"

class PreviousSiblings(Axis):
	SYMBOL = "<"

class Before(Axis):
	SYMBOL = "<<"

class After(Axis):
	SYMBOL = ">>"

# -----------------------------------------------------------------------------
#
# VARIABLES
#
# -----------------------------------------------------------------------------

class Binding:
	pass

class Expansion:
	pass

# -----------------------------------------------------------------------------
#
# INVOCATION
#
# -----------------------------------------------------------------------------

class Invocation:
	pass

# -----------------------------------------------------------------------------
#
# SELECTOR
#
# -----------------------------------------------------------------------------

class Selector:
	pass

class Query:
	pass



# EOF - vim: ts=4 sw=4 noet
