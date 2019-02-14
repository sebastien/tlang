from tlang.expr.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.expr module.
"""

VALUES = """
1
1.0
symbol-name
"string value"
"""

INVOCATIONS = """
count()
count(A)
count(A,B)
"""

BINDINGS = """
{1}
{1:A}
{count(A):A}
{count(A):A},{count(B):B}
"""


def test_values():
	TestUtils.ParseLines(VALUES, parseString)

def test_invocations():
	TestUtils.ParseLines(INVOCATIONS, parseString)

def test_bindings():
	TestUtils.ParseLines(BINDINGS, parseString)

if __name__ == "__main__":
	test_values()
	test_invocations()
	test_bindings()

# EOF - vim: ts=4 sw=4 noet