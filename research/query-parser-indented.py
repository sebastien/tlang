from libparsing import Grammar, Symbols
from tlang.utils import ParserUtils
from tlang.expr.parser import grammar as expr_grammar, ExprProcessor
from typing import Optional

GRAMMAR = Grammar

def symbols( g:Grammar ) -> Symbols:
	"""Registers tokens and words that are shared by all the grammars
	defined in this moddule."""
	s      = g.symbols
	tokens = {
		"SPACES"                  : "[\s]+",
		"INDENT"                  : "^[\t]*",
	}
	words = {
		"TAB"             : "\t",
	}
	groups = ()
	return ParserUtils.EnsureSymbols(g, tokens, words, groups)

def grammar(g:Optional[Grammar]=None, isVerbose=True) -> Grammar:
	"""Defines the grammar that parses grammar rule definitions."""
	global GRAMMAR
	if not g:
		if GRAMMAR:
			return GRAMMAR
		else:
			g=Grammar("expr-indent", isVerbose=isVerbose)

	s = symbols(g)

	g.procedure("ExprIndent", ParserUtils.Indent)
	g.procedure("ExprDedent", ParserUtils.Dedent)
	g.group("ExprIndentedValue")
	g.rule("ExprIndent", s.INDENT._as("indent"), g.acondition(ParserUtils.CheckIndent))
	g.rule("ExprLine", s.ExprIndent._as("indent"), s.ExprIndentedValue.oneOrMore()._as("value"))
	g.rule("ExprBlock")
	g.rule("ExprBlockChild", s.ExprIndent, s.ExprBlock._as("child"), s.ExprDedent)
	s.ExprBlock.set(s.ExprLine.oneOrMore(), s.ExprBlockChild.zeroOrMore())


	# # FIXME: Seting this line causes a lot of problems
	# s.ExprJoin.set(s.WS, s.ExprValuePrefix._as("arg"))
	g.rule("ExprIndentedList",       s.LP,    s.ExprIndentedValue._as("arg"),  s.RP)
	g.rule("ExprIndentedTemplate"  , s.EXPR_TEMPLATE, s.ExprIndentedValue._as("value"), s.RB)
	g.rule("ExprIndentedJoin",       s.SPACES,    s.ExprValuePrefix._as("arg"))

	# FIXME: This does not work better either
	# s.ExprValuePrefix.replace(0,s.ExprIndentedList)
	# s.ExprValuePrefix.replace(2,s.ExprIndentedTemplate)

	g.group("ExprIndentedValueSuffix").set(
		s.ExprPipe,
		s.ExprRest,
		s.ExprIndentedJoin,
		s.ExprComment,
	)

	s.ExprIndentedValue.set(
		s.ExprValuePrefix._as("prefix"), s.ExprIndentedValueSuffix.zeroOrMore()._as("suffixes")
	)

	g.axiom = s.ExprBlock
	g.skip  = s.SPACES

	if not GRAMMAR:
		GRAMMAR = g
	g.setVerbose(isVerbose)
	return g

class ExprIndentedProcessor(ExprProcessor):

	def onExprLine( self, match, indent, value ):
		print ("LINE", value)
		return value[0]

	def onExprIndentedJoin( self, match, arg ):
		return self.onExprJoin( match, arg )

	def onExprIndentedValue( self, match, prefix, suffixes ):
		return self.onExprJoin( prefix, suffixes )

	def onExprIndentedValueSuffix( self, match ):
		return self.onExprValueSuffix( prefix, suffixes )

	def onExprBlock( self, match ):
		node = self.tree.node("ex:list")
		lines    = self.process(match[0])
		print ("LINES", lines)
		# for line in lines:
		# 	node.append(line)
		# children = self.process(match[1])
		# for child in children:
		# 	print ("CHILD", child)
		# 	node.append(child)
		return node

	def onExprBlockChild( self, match, child ):
		print ("BLOCK", child)
		return child

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

if __name__ == '__main__':
	G = grammar(expr_grammar())
	print (ParserUtils.ParseMain(lambda isVerbose=False:G, ExprIndentedProcessor.Get()))

# EOF - vim: ts=4 sw=4 noet
