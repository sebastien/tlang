
from typing import Optional, Any, List, Dict
from collections import OrderedDict
from tlang.utils import NOTHING
from tlang.tree.model import Node

__doc__ = """
The core model representing rules
"""

class Element:
	pass

class Token(Element):

	def __init__( self, value:str ):
		pass

	def match( self, textr:str, offset:int ) -> int:
		return False

class TokenString(Token):

	def __init__( self, value:str ):
		self.value = value
		self.length = len(value)

	def match( self, text:str, offset:int ) -> int:
		n = len(self.text)
		m = offset + self.length
		if  m > n:
			return -1
		i = offset
		j = 0
		v = self.value
		while i < n:
			if text[i] != v[j]:
				return -1
			i += 1
			j += 1
		return m

class TokenRange(Token):

	def __init__( self, start:str, end:str):
		self.start  = start
		self.ostart = ord(start)
		self.end    = end
		self.oend   = ord(end)

	def match( self, text:str, offset:int ) -> int:
		o = ord(text[offset])
		return offset if self.ostart <= o and o <= self.oend else -1

class RuleReference(Token):

	# TODO: Use enum for cardinality
	def __init__( self, rule:"Rule", cardinality:str="" ):
		self.rule = rule
		self.cardinality = cardinality

	def match( self, text:str, offset:int ) -> int:
		# TODO
		return -1

class TokenList(Token):

	def __init__( self, tokens:List[Token], cardinality:str="" ):
		self.tokens = tokens
		self.cardinality = cardinality

	def match( self, text:str, offset:int ) -> int:
		# TODO
		return -1

class Rule:

	def __init__( self, name:str, variant:Optional[str]=None ):
		self.name = name
		self.variant = variant
		self.definition:TokenList = TokenList([])
		self.pattern:Optional[Node] = None

	def match( self, text:str, offset:int ) -> int:
		return self.definition.match(text, offset)

class Repr:

	@classmethod
	def Apply( cls, element ):
		if isinstance(element, TokenString):
			yield "'"
			yield element.value
			yield "'"
		elif isinstance(element, TokenRange):
			yield "["
			yield element.start
			yield "-"
			yield element.end
			yield "]"
		elif isinstance(element, RuleReference):
			yield element.name
			yield element.cardinality
		elif isinstance(element, Rule):
			rule = element
			yield rule.name
			if rule.variant:
				yield "("
				yield rule.variant
				yield ")"
			yield " := "
			for token in rule.definition.tokens:
				yield from cls.Apply(token)
			yield ";"
			if rule.pattern:
				yield "\n--> "
				# FIMXE: We should have a `toReprStream()`

# EOF - vim: ts=4 sw=4 noet
