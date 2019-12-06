from tlang.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.query module.
"""

QUERY_EXPR = """
(select @name)
(select  ./node)
(select  ./node/attribute)
(select  //node/attribute)
(select {A:@name})
(select {A:./node})
(select {A:./node/attribute})
(select {A://node/attribute})
"""

def test_query_expr():
	TestUtils.ParseLines(QUERY_EXPR, parseString)

if __name__ == "__main__":
	test_query_expr()

# EOF - vim: ts=4 sw=4 noet
