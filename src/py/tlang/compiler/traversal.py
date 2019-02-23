from enum import Enum, auto
from typing import Optional
from tlang.tree.model import Node

class Axis(Enum):
	DESCENDANTS = auto
	ANCESTORS   = auto
	BEFORE      = auto
	AFTER       = auto

class Attribute:

	IDS = 0

	def __init__( self, name:str ):
		self.id   = self.IDS ; self.IDS += 1
		self.name = name

class Query:

	IDS = 0

	def __init__( self, axis:Axis, node:Optional[str], attribute:Optional[str] ):
		self.id   = self.IDS ; self.IDS += 1
		self.axis = axis
		self.node = node
		self.attribute = attribute

class Step1:

	def process( self, attributes:Node ):
		pass


REWRITE = """
(replace 
	(expr-value-invocation
"""

SAMPLE = """
(attr (node @total)         (sum .//node/@value))
"""

if __name__ == "__main__":
	from tlang.parser import parseString
	print (parseString(SAMPLE))

# EOF - vim: ts=4 sw=4 noet
