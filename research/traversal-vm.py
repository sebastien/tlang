#!/usr/bin/env python3
# @ignore
from enum import Enum, auto
from tlang.tree.model import Node
from typing import Dict,Any,Optional

# @title A VM for tree traversal
#
# @texto
# In `tlang`, we want to make queries on the tree/graph and compute
# values of attributes that might have changed. This implies potentially
# many traversals of the tree/graph in order to retrieve the results
# and updates the values that do need an update.
#
# At this time, the main thing we know is that we want this operation to
# be as fast as possible, but we don't know yet what types of optimizations
# can be done to make it as fast as possible. As a result, we're going to
# explore how to create a virtual machine (VM) that would execute operations
# for tree traversal, and later try to define optimization passes on the
# VM "bytecode" to optimize a traversal program.
#
# A big advantage of this strategy is that it allowd for using tlang itself
# as a way to encode the VM and the optimization passes, once we have
# clearly identified the primitives and the optimizations.
#
# @h1 Key concepts


# @h2 Traversal direction
# @texto
# The first step is to define the direction of the traversal, we define the
# following:
#
# - `TD` for top-down traversal
# - `BU` for bottom-up traversal
# - `LR` for left-right traversal
# - `RL` for right-right traversal

# @aside
class Direction(Enum):
	TOP_DOWN   = auto
	BOTTOM_UP  = auto
	LEFT_RIGHT = auto
	RIGHT_LEFT = auto

# @aside
class Operation:

	def __init__( self, name, **kwargs ):
		self.name = name
		self.args = tuple(kwargs.values())
		self.argnames = tuple(kwargs.keys())

# @texto
# The first group of operations are about moving within the tree, these
# are the primivite to change the nodes and they all share the format
# `(OPCODE, FROM, TO)`.

UP    = Operation("UP",    fromNode=Node, toNode=Node)
DOWN  = Operation("DOWN",  fromNode=Node, toNode=Node)
LEFT  = Operation("LEFT",  fromNode=Node, toNode=Node)
RIGHT = Operation("RIGHT", fromNode=Node, toNode=Node)

# @texto
# Now a traversal should keep a map of conditions, which are all integers.
# A condition can be increased or decreased.
INC   = Operation("INC",  condition=str, value=int)
DEC   = Operation("DEC",  condition=str, value=int)

# @texto
# Rules are operations that are triggered when a specific operation
# arises during a traversal.
class Rule:

	def __init__( self, direction:Direction, node:str, condition:Operation, onMatch:Operation, onFail:Operation ):
		self.direction = direction
		self.node      = node
		self.condition = condition
		self.onMatch   = onMatch
		self.onFail    = onFail

	def match( self, direction:Direction, node:Node ) -> bool:
		return direction == direction and node.name == self.node

# @texto
# And now the traversal.
class Traversal:

	def __init__( self ):
		self.state:Dict[str,int] = {}

	def run( self, node:Node, rules:Dict[str,Rule] ):
		pass

# EOF - vim: ts=4 sw=4 noet 
