from tlang.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.query module.
"""

QUERY_EXPR = """
(out! "Hello, world!")
(select @name)
"""

def test_query_expr():
	TestUtils.ParseLines(QUERY_EXPR, parseString)

if __name__ == "__main__":
	test_query_expr()

# EOF - vim: ts=4 sw=4 noet
