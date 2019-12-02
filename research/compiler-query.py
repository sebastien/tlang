#!/usr/bin/env python3
#| @tdoc:indent spaces=2
#| title: Query compiler research
#| text
#|   We want to create a compiler that will transform a TLang query expression
#|   into some kind of executable program that yields the different values.
#|
#|   The first part is going to be about *normalizing the query* so that it
#|   is in a canonical, standard form. The second part will be about
#|   *translating the query* to an executable form, and the last part will
#|   be working on *optimizations* so that we reduce the number of operations
#|   to perform the query.

from tlang.query import parseString as parseQuery
from tlang.tree import Node
from typing import Optional, Iterator, NamedTuple, Dict, List

#Axis      = implements("query-axis", axis=str)
#Selection = implements("query-selection", axis="query-axis")

# // → DOWN[-1]
# /  → DOWN[0]
# \\ → UP[-1]
# \  → UP[0]

WalkStep = NamedTuple('WalkStep', [('node',Node), ('depth',int)])

def walkDownDepth(node:Node, depth:int=0) -> Iterator[WalkStep]:
	for c in node.children:
		yield (c, depth)
		yield from walkDownDepth(c, depth + 1)

def walkDownBreadth(node:Node, depth:int=0) -> Iterator[WalkStep]:
	for c in node.children:
		yield (c, depth)
	for c in node.children:
		yield from walkDownBreadth(c, depth + 1)


NodeSet = List[Node]

class Rule:

	def __init__( self, id:str ):
		self.id = id

	def match( self, node:Node ) -> bool:
		yield NotImplementedError

class NodeRule( Rule ):

	def __init__( self, id:str, name:str ):
		super().__init__(id)
		self.name = name

	def match( self, node:Node ) -> bool:
		return node.name == self.name

class AttributeRule( Rule ):

	def __init__( self, id:str, name:str ):
		super().__init__(id)
		self.name = name

	def match( self, node:Node ) -> bool:
		return node.hasAttribute(self.name)

class Traversal:

	def __init__( self, rules:Optional[List[Rule]]=None ):
		self.node = Optional[Node]
		self.nodeSets:Dict[str,NodeSet] = {}
		self.rules:List[Rule] = [_ for _ in rules or ()]

	def run( self, root, walk:Iterator[WalkStep] ):
		self.node = node
		self._process(node,0)
		for step in walk(node):
			self._process( step.node, step.depth )

	def _process( self, step:WalkStep ):
		for _ in self.rules:
			if _.match(node):
				if _.id not in self.nodeSets:
					self.nodeSet[_.id] = []
				self.nodeSets[_.id].append(step)

# We're trying to parse. So we extract the unique set of rules R of 
# nodes and attributes to match.
#
# //dir/file[\\dir[./@name]]
# R1    R2   R1    R3 
#

#print (parseQuery("//dir/file[\\dir[./@name]]"))
R1 = NodeRule("R1", "dir")
R2 = NodeRule("R2", "file")
# We want to 
R3 = AttributeRule("R3", "name")





# EOF - vim: ts=4 sw=4 noet
