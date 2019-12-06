#!/usr/bin/env python3
## @tdoc:indent spaces=2
## title: Query compiler research
## text|texto
##   We want to create a compiler that will transform a TLang query expression
##   into some kind of executable program that yields the different values.
##
##   The first part is going to be about *normalizing the query* so that it
##   is in a canonical, standard form. The second part will be about
##   *translating the query* to an executable form, and the last part will
##   be working on *optimizations* so that we reduce the number of operations
##   to perform the query.

## hidden
from tlang.query import parseString as parseQuery
from tlang.tree import Node, node
from typing import Optional, Iterator, NamedTuple, Dict, List
from collections import namedtuple

#Axis      = implements("query-axis", axis=str)
#Selection = implements("query-selection", axis="query-axis")

# // → DOWN[-1]
# /  → DOWN[0]
# \\ → UP[-1]
# \  → UP[0]


# -----------------------------------------------------------------------------
#
# WALKING
#
# -----------------------------------------------------------------------------
## section
##   title: Walking
##   text|texto
##     Walking a tree is a key part of querying, and we need to introduce
##     concepts that repesent the important elements of a walk:
##
##     - The current step we're at
##     - The direction we're going
##   :

Range    = NamedTuple('Range', [('min',Optional[int]), ('max', Optional[int])])
WalkStep = NamedTuple('WalkStep', [('node',Node), ('depth',int), ('index',int), ('step',int)])
NodeSet  = List[Node]

def walkDownDepth(node:Node, depth:int=0, step:int=0) -> Iterator[WalkStep]:
	for i,c in enumerate(node.children):
		yield WalkStep(c, depth, i, step)
		step += 1
		yield from walkDownDepth(c, depth + 1, step)

def walkDownBreadth(node:Node, depth:int=0, step:int=0) -> Iterator[WalkStep]:
	for i,c in enumerate(node.children):
		yield WalkStep(c, depth, i, step)
		step += 1
	for c in node.children:
		yield from walkDownBreadth(c, depth + 1, step)

class WalkState:

	def __init__( self ):
		self.matches:Dict[str,List[WalkStep]] = {}
		self.step:Optional[WalkStep] = None

	def onStep( self, step:WalkStep ):
		self.step = step
		return self

	def doMatch( self, rule:'Rule', step:WalkStep ):
		# NOTE: We put the newest first
		self.matches.setdefault(rule.id, []).insert(0,step)

	def getMatchesForRule( self, rule:'Rule' ) -> Iterator[WalkStep]:
		for step in self.matches.get(rule.id, ()):
			yield step

# -----------------------------------------------------------------------------
#
# ABSTRACT RULES
#
# -----------------------------------------------------------------------------

class Rule:

	def __init__( self, id:str ):
		self.id = id
		self.handlers = None

	def match( self, state:WalkState, step:WalkStep ) -> bool:
		raise NotImplementedError

	def onMatch( self, handler ):
		if not self.handlers:
			self.handlers = [handler]
		else:
			self.handlers.append(handler)
		return self

	def doMatch( self, state:WalkState, step:WalkStep ):
		if self.handlers:
			for handler in self.handlers:
				if handler(state, step) is False:
					break

	def _as( self, id:str ):
		self.id = id
		return self

	def __repr__( self ) -> str:
		return f"<{self.__class__.__name__}:{self.id}>"

class AtomicRule( Rule ):
	"""A rule that does not rely on another rule."""

class CompositeRule( Rule ):
	"""A rule that wraps other rules."""

	@property
	def rules( self ):
		raise NotImplementedError

	def expandRules( self ):
		for _ in self.rules:
			if isinstance(_, CompositeRule):
				# We yield the children rules first, because they
				# need to be resolved first.
				yield from _.expandRules()
				yield _
			else:
				yield _

# -----------------------------------------------------------------------------
#
# ATOMIC RULES
#
# -----------------------------------------------------------------------------

class NodeRule( AtomicRule ):
	"""Matches a node with the given name."""

	def __init__( self, id:str, name:str ):
		super().__init__(id)
		self.name = name

	def match( self, state:WalkState, step:WalkStep ) -> bool:
		return step.node.name == self.name

class AttributeRule( Rule ):
	"""Matches a node with the given attribute."""

	def __init__( self, id:str, name:str ):
		super().__init__(id)
		self.name = name

	def match( self, state:WalkState, step:WalkStep ) -> bool:
		return step.node.hasAttribute(self.name)

# -----------------------------------------------------------------------------
#
# COMPOSITE RULES
#
# -----------------------------------------------------------------------------

class WalkStateRule( CompositeRule ):

	COUNT = 0

	def __init__( self, rule:Optional[Rule], node:Optional[Node], depth:Optional[Range], index:Optional[Range]):
		super().__init__(f"W{self.__class__.COUNT}")
		self.__class__.COUNT += 1
		self.rule = rule
		self.node = node
		self.depth = depth
		self.index = index

	@property
	def rules( self ):
		return [self.rule]

	def match( self, state:WalkState, step:WalkStep ) -> bool:
		# NOTE: This is the slow version
		for step in state.getMatchesForRule(self.rule):
			# We need to make the depth/index relative to the current step
			rel_depth = step.depth - state.step.depth
			rel_index = step.index - state.step.index
			if self.isNode(step.node, self.node) and self.isInRange(rel_depth, self.depth) and self.isInRange(rel_index, self.index):
				return True
		return False

	def isNode( self, node:Node, expected:Optional[Node] ) -> bool:
		if expected is None:
			return True
		else:
			return node and node.name == expected.name

	def isInRange( self, value:int, range:Range ) -> bool:
		if range is None:
			return True
		else:
			mn, mx = range
			# NOTE: Range is inclusive [mn, mx]
			if mx is not None and value > mx:
				return False
			elif mn is not None and value < mn:
				return False
			else:
				return True

class Predicate(CompositeRule):

	COUNT = 0

	@classmethod
	def Is( cls, rule:Rule ) -> WalkStateRule:
		return WalkStateRule(rule, None, Range(0, 0), None)

	@classmethod
	def Ancestor( cls, rule:Rule ) -> WalkStateRule:
		return WalkStateRule(rule, None, Range(None, -1), None)

	@classmethod
	def Parent( cls, rule:Rule ) -> WalkStateRule:
		return WalkStateRule(rule, None, Range(-1, -1), None)

	def __init__(  self, *rules:Rule ):
		super().__init__(f"P{Predicate.COUNT}")
		Predicate.COUNT += 1
		self._rules  = rules

	@property
	def rules( self ):
		return self._rules

	def match( self, state:WalkState, step:WalkStep ) -> bool:
		# We have an 'AND' joining the rules
		for rule in self._rules:
			if not rule.match(state, step):
				return False
		return True

# -----------------------------------------------------------------------------
#
# TRAVERSAL
#
# -----------------------------------------------------------------------------

class Traversal:

	def __init__( self, *rules:Rule ):
		self.rules:List[Rule] = []
		for r in rules or ():
			# We skip the walk state rules
			if isinstance(r, CompositeRule):
				for _ in r.expandRules():
					if _ not in self.rules:
						self.rules.append(_)
			if r not in self.rules:
				self.rules.append(r)
		# We exclude WalkStateRules, as they're just meant to be used
		# by rpedicates.
		self.rules = [_ for _ in self.rules if not isinstance(_, WalkStateRule)]


	def traverse( self, node:Node, walk ):
		state       = WalkState()
		self._process(state, WalkStep(node, -1, 0, 0))
		for step in walk(node, step=1):
			self._process( state ,step)
		return state

	def _process( self, state:WalkState, step:WalkStep ):
		state.onStep(step)
		for rule in self.rules:
			# FIXME: OK, so here we match all the rules, but obviously we
			# should not have to test them all. Only the atomic rules should
			# be tested, as the non atom ones can be deduced from the
			# atomic.
			# FIXME: We should also discard some of the matches based on the
			# rules. The limits will tell how long we'll need to keep them.
			if rule.match(state, step):
				state.doMatch(rule, step)
				if rule.handlers:
					rule.doMatch(state, step)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

## section
##   title: Parsing
##   text
##      We're trying to parse. So we extract the unique set of rules R of 
##      nodes and attributes to match.
##   code
##      //dir/file[\\dir[./@name]]
##        R1  R2     R1   R3 
##                   P1 ---------
##        P3------ P2------------

# We print the query
# print (parseQuery("//dir/file[\\dir[./@name]]"))

R1 = NodeRule("R1", "dir")
R2 = NodeRule("R2", "file")
R3 = AttributeRule("R3", "name")

## NOTE: We're trying to define an encoding for queries here.
# P1 is dir[@name]
Q1 = Predicate(
	Predicate.Is(R1),
	Predicate.Is(R3),
)._as("Q1")

# Q2 is //P1 → //dir[@name]
Q2 = Predicate(Predicate.Ancestor(Q1))._as("Q2")

# Q3 is R1/R2 → dir/file
Q3 = Predicate(
	Predicate.Is(R2),
	Predicate.Parent(R1)
)._as("Q3")

# Q4 is Q2[Q3]
Q4 = Predicate(
	Predicate.Is(Q3),
	Predicate.Is(Q2)
)._as("Q4")

def match_found( state:WalkState, step:WalkStep ):
	print ("FOUND", step)

Q4.onMatch(match_found)

tree = node("dir", {"name":"tlang"},
	node("dir", {"name":"research"},
		node("file", {"name":"compiler-query.py"}),
		node("file", {"name":"interpreter.py"}),
		node("file", {"name":"interpreter-stream.py"})))


print (tree)

t = Traversal(Q4)
print (t.rules)
state = t.traverse(tree, walkDownDepth)
# TODO: We should get the rank as an optimization


# EOF - vim: ts=4 sw=4 noet
