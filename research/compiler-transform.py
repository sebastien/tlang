#!/usr/bin/env python3

# @ignore
from typing import List

# @title Transform compiler
#
# @texto
# The idea of this module is to create a compiler for transforms that
# computes the values/tranasformations in the most efficient way. We'll 
# start with the computation of syntethic attributes:

# @h1 Synthetic Attributes Computation
#
# We start with the `sum` example:
#
# ```transform
# (attr (node @sum)  (sum .<<.node/@value))
# (attr (node @mean) (div ./@sum (count .<<.node)))
# ```
#
# The first step is to decompose the transforms so that we identify 
# the queries and the computations that need to happen to ensure that 
# all the attributes are up-to-date at the end of the traversal process.
#
# We can rephrase the transform as:
#
# ```dot
# A1 <-- Q1
# A2 <-- Q2 Q3
# Q2 <-- A1
# ```
#
# where:
#
# - `A1` is the synthetic attribute `node/@sum`
# - `A2` is the synthetic attribute `node/@mean`
# - `Q1` is the `.<<.node/@value` selection
# - `Q2` is the `./@sum` selection
# - `Q3` is the `.<<.node` 
#
# We can see here that Q1 actually depends on Q3 as Q1 is contained
# in Q3, so we can rephrase the depenencies list so, calculating the
# order of each node in the graph (in parens):
#
# ```dot
# Q3              (0)     # Q3 depends on a static attribute, so has order 0
# Q1 <-- Q3       (1)
# A1 <-- Q1       (2)
# Q2 <-- A1       (3)
# A2 <-- Q2 Q3    (4)
# ```
#
# In order to make this concrete, we can define the following functions
# to compute the attributes based on the current queries:

def node_sum( Q1:List[float] ):
	return sum(Q1)

def node_mean(  Q2:float, Q3:List[float]):
	return Q2 / len(Q3)

# @texto
# We define a `Traversal` object that maintains `q1`, `q2` and `q3`.
class Traversal:

	def __init__( self ):
		self.init()

	def init( self ):
		self.q1:List[float] = []
		self.q2:float       = 0
		self.q3:List[float] = []

# @texto
# The traversal's visit method is where the logic happens. Here, we update
# the queries as we traverse and apply the updates in the order defined
# by the depdency graph we identified above.

	def visit( self, node ) -> bool:
		if node.name is "node":
			self.q1.append(node.attr("value"))
			self.q2 = node.attr("sum", node_sum(self.q1))
			self.q3.append(node)
			node.attr("mean", node_mean(self.q2, self.q3))
		return True

# @texto
# So what are the takeaways from this? First, the compiler needs
# to catalogue the synthetic attributes (A0…AN) and the queries
# that they use in their computations (Q0…QN).
#
# Second, the compiler needs to map the queries `Q` to attributes
# `A`, and vice-versa (queries might use a synthetic attribute). The
# queries can also depend on each other based on their specificity, as 
# one query might be derived from the other, however this is probably
# less important than the query-attribute and attribute-attribute
# dependencies.
#
# Third, the compiler needs to rank the `A` and `Q` nodes in the 
# dependency graph. The ranking will dictate the order in which the
# queries and attributes are computed.

# @h1 Multiple traversals 

# @texto
# We can create an artificially complex example where one synthetic attribute
# might require a full traversal before being used. Let's introduce a synthetic
# `@total` that is the sum of all descendants `@value`, and a synthentic 
# attribute `@weight` that depends on the root's total. This means that 
# we'll need to do a first traversal to compute the root's total before
# being able to calculate the weight.
#
# ```
# (attr (node @total)         (sum .//node/@value))
# (attr (node @weight)        (div ./@total /node/@total))
# ```
#
# Let's decompose the attributes into a graph
#
# ```dot
# A1[label="node/@total"]  <-- Q1[label=".//node/@value"]
# A2[label="node/@weight"] <-- Q2[label="./@total"]
# A2[label="node/@weight"] <-- Q3[label="/node/@total"]
# ```
#
# Which translates into the following order:
#
# ```
# Q1              (0)
# A1 <-- Q1       (1)
# Q2 <-- A1       (2)
# Q3 <-- A1       (2)
# A2 <-- Q2 Q3    (3)
# ```
#
# But here, we don't have enough information to know how many traversals
# we'll need to compute all the synthetic attirbutes. However, we can
# annotate each attribute with the axis it depends on:
#
# - `A1` depends on the local descendants `.//`
# - `A2` depends on the current node
# - `A2` also depends on `A1` scoped at the root, which translates into all desendants `//`
#
# The question here is to identify how many traversals we'll need, in which
# direction and which attributes will be computed.
#
# We have the traversal `T1` that is `.//`, which is perfect as it is a subset
# of the depth or breadth-first traversal. However, `//` can only be satified
# at the *end of the traversal*. That means that any attribute that depends
# on `//` can only be computed on the next traversal.
#
# So we have a second traversal `T2` that we can use to compute the `A2`
# attributes, which uses a full depth-first travesal.
#
#      Note___________________________________________________________________
#      There is an opportunity to reuse parts of a previous traversal,
#      in particular queries that might be used to speed up the traversal.
#      In this case, `A2` is only for `node` nodes, so if we have other
#      types of nodes, we should skip them. 

class TraversalA:

	def __init__( self ):
		self.init()

	def init( self ):
		self.q1:List[float] = []
		self.q2:float       = 0
		self.q3:float       = 0

	def visit( self, node ) -> bool:
		if node.name is "node":
			self.q1.append(node.attr("value"))
			self.q2 = node.attr("sum", node_sum(self.q1))
			self.q3.append(node)
			node.attr("mean", node_mean(self.q2, self.q3))
		return True



# EOF - vim: ts=4 sw=4 noet
