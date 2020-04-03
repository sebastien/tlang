from enum import Enum
from tlang.tree import Node
from tlang.query import Selection, Predicate, Axis
from typing import Optional, Iterator, NamedTuple, Tuple, Dict, List

## The core principle of the query compiler/interpreter is that upon traveral
## we keep track of the rules that matched:
##
## - is the current node like `dir` or `file`?
## - does the  current node has an attribute like `@path` or `@id`?
##
## Each match is registered at a given position: its depth, its offset and its
## step.
##
## Now during a traversal, queries like `parent/child` can be translated into
## - there is match for `parent` with a depth of the current depth - 1 (provided
##   a depth-first traversal).
## - and there is a match for `child` with the current node

# Range    = NamedTuple('Range', [('min',Optional[int]), ('max', Optional[int])])
# WalkStep = NamedTuple('WalkStep', [('node',Node), ('depth',int), ('index',int), ('step',int)])

# We want to normalize queries
# parent/child → child[\parent]
# ancestor//descendant → descendant[\\ancestor]


# TODO: Might need to be moved to model
TNodeSet  = List[Node]

# -----------------------------------------------------------------------------
#
# WALK
#
# -----------------------------------------------------------------------------

class Walk:
	"""Walks define ways to iterate on trees and yield steps that keep track
	of where we are in the tree. When associated with matches, the distance
	between walk steps can be measured and use to trigger rules that depend
	on other rules."""

	Step = NamedTuple('Step', [
		('node',Node), ('depth',int), ('breadth',int), ('index',int)])

	@staticmethod
	def DownDepth(node:Node, depth:int=0, step:int=0) -> Iterator['Walk.Step']:
		"""Walks down the given node and yields corresponding WalkStep, starting
		off the given `depth` and `step`. """
		for i,c in enumerate(node.children):
			yield Walk.Step(c, depth, i, step)
			step += 1
			yield from Walk.DownDepth(c, depth + 1, step)

	@staticmethod
	def DownBreadth(node:Node, depth:int=0, step:int=0) -> Iterator['Walk.Step']:
		"""Walks the give node in a breadth-first mode, yielding corresponding
		WalkSteps."""
		for i,c in enumerate(node.children):
			yield Walk.Step(c, depth, i, step)
			step += 1
		for c in node.children:
			yield from Walk.DownBreadth(c, depth + 1, step)


# -----------------------------------------------------------------------------
#
# RULE
#
# -----------------------------------------------------------------------------

class Rule:
	"""A rule wraps a selection's *predicate* in a uniquely identified rule.
	The rules abstract away from the predicate, creating an opportunity for
	loose coupling with compiler query model."""

	COUNT = 0

	def __init__( self, predicate:Predicate ):
		self.id = Rule.COUNT
		self.predicate = predicate
		self.name = f"R{self.id}"
		# A/B → A.duration = 1 ; B.duration = 0
		# A//B → A.duration = None ; B.duration = 0
		self.duration:Optional[int] = None
		Rule.COUNT += 1

	def __repr__( self ):
		return f"#{self.name}:{self.predicate}"

# -----------------------------------------------------------------------------
#
# INTERPRETER
#
# -----------------------------------------------------------------------------

TRuleMap = Dict[Optional[Rule], List[Rule]]

class Interpreter:
	"""Captures the map of rules that should be active after a given rule
	is triggered."""

	# A[B] means "A required B", which means that A cannot occur before B,
	# which means that `NEXT(B) = A`
	#
	# A/B means "B happens after A in top-down traversal", which also means
	# that B cannot occur before A, which means  `NEXT(A) = B`
	#
	# A//B also means like A/B that B cannot happen before A, but it also
	# means that A can also happen next in a top-downtraversal, which 
	# means `NEXT(A) = {A,B}`.
	# 

	def __init__( self ):
		# Next is the list of rules that are going to be active after the 
		# given rule matches.
		# --
		# For instance, with A/B
		#    next[A] → [B]
		# and with A//B
		#    next[A] → [A,B]
		self.next:TRuleMap = {}
		# There rules are rules that should be evaluated as part of the current
		# iteration, not for the next one. This happens in cases like
		# `file[\\dir]`, where `dir` is a requirement 
		self.there:TRuleMap = {}
		# The interpreter has a list of *active rules*, seeded with `next[None]`.
		# When a rule *matches*, its *action* is triggered, and its *succesors*
		# (`next[rule]`) are added to the list of active rules, which starts
		# blank as part of each step.
		# --
		# NOTE: Some rules might dynamically decide the next rules, or restrict
		# them based on some dynamic condition.

	def run( self, node:Node ):
		"""Runs the interpreter on the given node. You'll need to have queries
		already registered for it to work."""
		current:Optional[Node] = None
		rules:List[Rule] = self.next[current]
		for step in Walk.DownDepth(node):
			print ("STEP", step)
			for rule in rules:
				if rule.predicate.match(node):
					print ("  RULE MATCHES", rule, "ON", repr(node))

	# FIXME: This assumes depth-first, the logic would be different
	# for other traversal orders.
	def register( self, selection:Selection ) -> Tuple[TRuleMap,TRuleMap]:
		"""Registers the given `selection`. This will extract all the predicates
		from the selection and wrap them in rules that are uniquely
		identified.

		This will return a tuple `(rules, direct_rules)` where both are
		`Dict[Optional[Rule],List[Rule]` and tells which rules should be
		active on next step if the mapped rule matches.
		"""
		# These are the rules that should become active once the key rule
		# matches.
		rules = self.next
		# These are the rules that should become directly active once
		# the key rule matches. In other words, these rules must be tested
		# before we change the current node as we continue our walk.
		direct_rules = self.there
		predicate_rule:Dict[str,Rule] = {}
		def add( d:TRuleMap, key:str, r:Rule ):
			"""Helper function to register rules in the map."""
			l = d.get(key)
			if not l:
				l = [r]
				d[key] = l
			elif r not in l:
				l.append(r)
			return l
		def register_helper( sel:Selection, origin:Optional[Rule] ):
			"""Takes a selection, extracts the predicate, registers it as
			a new rule if not already defined and updates the direct successor
			and regular successors rule maps."""
			axis = sel.axis
			key  = str(sel.predicate)
			# NOTE: We need to make sure the key captures all the possible
			# variations of a predicate
			if key not in predicate_rule:
				predicate_rule[key] = Rule(sel.predicate)
			rule = predicate_rule[key]
			assert origin is None or isinstance(origin, Rule), f"Origin should be a rule, got: {origin}"
			# === SELF ========================================================
			if axis is Axis.SELF:
				add(direct_rules, origin, rule)
			# === CHILDREN ====================================================
			elif axis is Axis.CHILDREN:
				add(rules, origin, rule)
			# === DESCENDANTS =================================================
			elif axis is Axis.DESCENDANTS:
				# With descendants, the given rule is a successor of its
				# origin (parent) and of itself
				add(rules, origin, rule)
				add(rules, rule,   rule)
			else:
				raise NotImplementedError(f"Axis not supported yet {axis} in {str(selection)}")
			# *where* selections are required for the current
			# rule to match.
			for cond_sel in sel._where:
				# We normalize [\\] as //
				if cond_sel.axis == Axis.ANCESTORS:
					cond_sel = cond_sel.clone()
					cond_sel.axis = Axis.DESCENDANTS
				# So we register them as selections with no origin
				# FIXME: We should probably normalize the `where` clause before
				cond_rule = register_helper(cond_sel,  None)
				assert isinstance(cond_rule, Rule)
				# And we make the current rule a next rule of the condition
				# rule, because if `cond_rule` matches, then `rule`
				# should be evaluated.
				add(direct_rules, cond_rule, rule)
			for child_sel in sel._then:
				register_helper(child_sel, rule)
			return rule
		register_helper(selection, None)
		return (rules, direct_rules)

# EOF - vim: ts=4 sw=4 noet
