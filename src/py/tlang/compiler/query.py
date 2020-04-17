from enum import Enum
from tlang.tree import Node
from tlang.query import Selection, Predicate
from typing import Optional, Iterator, NamedTuple, Tuple, Dict, List, Set, Union

class Comparator(Enum):
	NONE = -100
	LT  = -2
	LTE = -1
	EQ  = 0
	GT  = 1
	GTE = 2

class QueryAxis(Enum):
	VERTICAL = 0
	HORIZONTAL = 1
	TRAVERSAL = 2

# -----------------------------------------------------------------------------
#
# TRAVERSAL
#
# -----------------------------------------------------------------------------

TraversalStep =  NamedTuple('TraversalStep', [
	('node',Node), ('depth',int), ('breadth',int), ('index', int)])

class Traversal:
	"""Traverses a tree, yielding steps that keep track of the position within
	the traversal. The steps can then be used by the traversal rules to
	detect if there is a match or not."""

	@classmethod
	def DownDepth(cls, node:Node) -> Iterator[TraversalStep]:
		"""Walks down the given node and yields corresponding TraversalStep, starting
		off the given `depth` and `step`. """
		i = 0
		stack = [TraversalStep(node, 0, 0, 0)]
		while stack:
			step = stack.pop()
			yield TraversalStep(step.node, step.depth, step.breadth, i)
			i += 1
			for j,child in enumerate(step.node.children):
				stack.append(TraversalStep(child, step.depth + 1, j, 0))

	@classmethod
	def DownBreadth(cls, node:Node, depth:int=0, step:int=0) -> Iterator[TraversalStep]:
		"""Walks the give node in a breadth-first mode, yielding corresponding
		traversal steps."""
		for i,c in enumerate(node.children):
			yield TraversalStep(c, depth, i, step)
			step += 1
		for c in node.children:
			yield from cls.DownBreadth(c, depth + 1, step)

# -----------------------------------------------------------------------------
#
# TRAVERSAL RULE
#
# -----------------------------------------------------------------------------

TMatches = Dict['TraversalRule', List[TraversalStep]]

class TraversalRule:
	"""An abstract rule that is used as a base for the terminal and
	composite rules."""

	def __init__( self, id:str ):
		self.id = id
		self.usedBy:List['Composite'] = []

	@property
	def captures( self ):
		return None

	def match( self, step:TraversalStep, matches:TMatches ) -> bool:
		return False

	def __repr__( self ):
		return self.id

RootRule = TraversalRule("RR")

# -----------------------------------------------------------------------------
#
# TERMINAL
#
# -----------------------------------------------------------------------------

class Terminal(TraversalRule):
	"""A terminal rule is a node predicate that can be directly tested."""

	IDS = 0

	def __init__( self, predicate:Predicate ):
		super().__init__(f"T{Terminal.IDS}")
		Terminal.IDS += 1
		self.predicate = predicate

	def match( self, step:TraversalStep, matches:TMatches ):
		# It's a terminal, so we ignore the contextual matches
		return self.predicate.match(step.node)

	def __repr__( self ):
		return f"{self.id}:{self.predicate}"

# -----------------------------------------------------------------------------
#
# DEPDENDENCY
#
# -----------------------------------------------------------------------------

class RuleDependency:
	"""Represents a dependency between two rules. For instance, in the
	selection `dir/file`, `file` depends on `dir`."""

	@staticmethod
	def FromRule( rule, axis ):

	def __init__( self, rule:TraversalRule, axis:Axis )
		self.rule = rule
		self.axis:QueryAxis, self.comparator:Comparator, self.minDistance:int, self.maxDistance:int = self.parseAxis(axis)

	def parseAxis( self, axis:Axis ):
		if axis == Axis.CHILDREN:
			return (QueryAxis.VERTICAL, Comparator.EQ, 1, 1)
		elif axis == Axis.DESCENDANTS:
			return (QueryAxis.VERTICAL, Comparator.EQ, 1, 1)

	def match( self, step:TraversalStep, matches:TMatches ) -> bool:
		# NOTE: For performance, the conditional should be outside of the for
		for match in matches.get(self.rule, ()):
			if self.axis in Axis.VERTICAL:
				# FIXME: This requires that the matches are popped when
				# backtracking in the traversal
				if self.matchDistance(step.depth - match.depth):
					return True
			else:
				raise ValueError(f"Axis type not supported: {self.axis}")
		return False

	def matchDistance( self, d ):
		if self.comparator == Comparator.NONE:
			return True
		elif self.comparator == Comparator.LTE:
			return d <= self.minDistance
		elif self.comparator == Comparator.LT:
			return d < self.minDistance
		elif self.comparator == Comparator.EQ:
			return self.minDistance <= d and d <= self.maxDistance
		elif self.comparator == Comparator.GT:
			return d >= self.minDistance
		elif self.comparator == Comparator.GTE:
			return d > self.minDistance
		else:
			raise ValueError(f"Comparator not supported: {self.comparator}")

# -----------------------------------------------------------------------------
#
# COMPOSITE
#
# -----------------------------------------------------------------------------

class Composite(TraversalRule):
	"""A composite rule typically depends on other rules to be triggered."""

	IDS = 0

	def __init__( self, selection, anchor=RootRule ):
		super().__init__(f"R{Composite.IDS}")
		Composite.IDS += 1
		self.selection:Selection = selection
		self.dependencies:List[RuleDependency] = [
			RuleDependency.FromSelection(selection)
		]

	@property
	def captures( self ):
		return self.selection._captures

	# def requires( self, rule:TraversalRule ):
	# 	# We register a dependency between the required rule and this
	# 	# rule. This is useful as terminals need to know which rules
	# 	# shold be then checked.
	# 	assert isinstance(rule, TraversalRule), f"Expected TraversalRule, got: {rule}"
	# 	if self not in rule.usedBy:
	# 		rule.usedBy.append(self)
	# 	self.dependencies.append(RuleDependency(rule, axis, comparator, distance))
	# 	return self

	def compose( self, rule:'Composite' ):
		assert isinstance(rule, Composite), f"Cannot compose with a terminal: {self} with {rule}"
		# We transpose all the dependencies with respect to the new rule
		# FIXME: This won't work for /file\\dir, for instance.
		self.dependencies = [_.transpose(rule.selection.axis) for _ in self.dependencies]
		# We add a new dependency for the given rule
		self.requires(rule, axis=rule.selection.axis)
		return self

	def match( self, step:TraversalStep, matches:TMatches ):
		# The rule dependency is not a terminal, so it ignores the current node
		# but only matches the context
		assert self.dependencies, f"Composite rule has no dependencies: {self}"
		for dep in self.dependencies:
			if not dep.match(step, matches):
				return False
		return True

	def __repr__( self ):
		return f"{self.id}:{self.selection}"

# -----------------------------------------------------------------------------
#
# SLECTION TO RULES
#
# -----------------------------------------------------------------------------

class SelectionProcessor:
	"""Processes selection object and registers rules (terminals and
	composites) that can then be used by the query interpreter."""

	def __init__( self ):
		self.terminals:Dict[str,Terminal] = {}
		self.composites:List[Composite] = []

	def process( self, selection:Selection ):
		# We extract the predicate from the selection and wrap it in a
		# terminal. Note that throughout the whole process we use the
		# string representation of a selection or predicate to get its
		# identity/signature, so that we can reuse them.
		self.processSelection(selection)
		return ([_ for _ in self.terminals.values()], self.composites)

	def processSelection( self, selection:Selection ) -> Composite:
		assert len(selection._then) <= 1
		# We wrap the selection predicate in a terminal. For
		# instance, if we have `//dir` then we extract `dir`
		# as a separate terminal rule. The terminals are shared amongst
		# composites and should be unique (ie. no duplicates of the same
		# predicate).
		predicate = self.processPredicate(selection.predicate)
		assert predicate, f"Selection must have predicate: {selection}"
		# We create the composite that requires that predicate
		composite = Composite(selection).requires(predicate)
		self.composites.append(composite)
		# Now we process the "where" rules (the one in []), like `@path`
		# in `//dir[@path]`. These rules must be satified for this
		# rule to happen.
		for sub_sel in selection._where:
			composite.requires(self.processSelection(sub_sel))
		# And now we process the "then" rules, like `dir/file`
		if selection._then:
			assert (len(selection._then) == 1)
			composite.compose(self.processSelection(selection._then[0]))
		return composite

	def processPredicate( self, predicate:Predicate ) -> Optional[Terminal]:
		"""Creates a terminal rule from the given predicate."""
		if not predicate:
			return None
		else:
			pred_key = str(predicate)
			if pred_key not in self.terminals:
				t = Terminal(predicate)
				self.terminals[pred_key] = t
				return t
			else:
				return self.terminals[pred_key]

# -----------------------------------------------------------------------------
#
# QUERY INTERPRETER
#
# -----------------------------------------------------------------------------

class QueryInterpreter:

	def __init__( self ):
		self.transform = SelectionProcessor()
		self.terminals = []
		self.composites = []
		self.isTracing = True
		self.trace = print

	def register( self, query:Selection ):
		(self.terminals, self.composites) = SelectionProcessor().process(query)
		return self

	def run( self, root:Node ):
		matches:Dict[TraversalRule, List[TraversalStep]] = {
			RootRule:[TraversalStep(root,0,0,0)],
		}
		for step in Traversal.DownDepth(root):
			if self.isTracing:
				self.trace("―┄ Step:", step.index, "/", ",".join(str(_) for _ in matches.keys()))
				self.trace("―┄┄ Node:", step.node)
			# We seed the lis of rules to check with the terminals
			to_check = [_ for _ in self.terminals]
			# Some rules might be matched more than one, so we keep
			# track of the matched ones.
			matched = []
			while to_check:
				rule = to_check.pop(0)
				if rule.match(step, matches) and rule not in matched:
					if self.isTracing:
						self.trace ("―┄┄ ✓ Match:", rule, "matched, captures?", rule.captures)
					if rule.captures:
						yield (rule.captures, step.node)
					# The latest matches go first
					matches.setdefault(rule,[]).insert(0, step)
					# FIXME: This might lead ot testing the same rule
					# multiple times and potentially having loops. Like
					# for cells, we should pre-compute the transitive
					# dependencies.
					matched.append(rule)
					for dep_rule in rule.usedBy:
						if dep_rule not in matched:
							to_check.append(dep_rule)
				else:
					if self.isTracing:
						self.trace("―┄┄ ✗ No match:", rule)
		if self.isTracing:
			self.traceMatchingTable(matches)

	def traceMatchingTable( self, matches, trace=None ):
		trace = self.trace
		rules = self.terminals + self.composites
		last_index = max(max(_.index for _ in matches.get(r, ())) for r in rules)
		col_values = [dict( (_.index, _) for _ in matches.get(r, ())) for r in rules]
		col_values = [[_.get(i,None) for i in range(last_index + 1)] for _ in  col_values]
		for i,_ in enumerate(rules):
			trace (f"     \t{'┊	'*i}⮦ {_}")
		trace ("   #\t" + "\t".join(_.id for _ in rules))
		for i in range(last_index + 1):
			trace (f"{i:4d}\t" + "\t".join("✓" if _[i] else " " for _ in col_values))

# EOF - vim: ts=4 sw=4 noet
