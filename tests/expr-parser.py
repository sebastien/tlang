from tlang.expr.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.expr module.
"""

VALUES = """
1
1.0
symbol-name
:Symbol
Binding:
#singleton
"string value"
;; Comment
"""

INVOCATIONS = """
(count)
(count A)
(count A B)
(has? A)
(fail! A)
"""

SUFFIXES = """
(list A ... B)
(list A … B)
(list A … B C D)
(list A | A)
(list A | A B)
(list A . B)
(list A…B)
(list A|B)
(list A.B)
"""

QUOTES = """
'(count)
'(count A '(A B C))
"""

BINDINGS = """
(A: 1)
(A: (count A))
(A: (count A)) (B: (count B))
(C: (count A | add 5)) (D: (count B | add 10))
(A: 1)
"""

TEMPLATES = """
{1}
{VARIABLE_NAME}
(add {1})
(add {(add 1 2)})
{A . B}
{A.B}
{A|B}
{a|format}
"""

def test_values():
	TestUtils.ParseLines(VALUES, parseString)

def test_invocations():
	TestUtils.ParseLines(INVOCATIONS, parseString)

def test_suffixes():
	TestUtils.ParseLines(SUFFIXES, parseString)

def test_bindings():
	TestUtils.ParseLines(BINDINGS, parseString)

def test_quotes():
	TestUtils.ParseLines(QUOTES, parseString)

def test_templates():
	TestUtils.ParseLines(TEMPLATES, parseString)

def test_long():
	TestUtils.ParseLines("1.0 " * 10000, parseString)

if __name__ == "__main__":
	test_values()
	test_invocations()
	test_suffixes()
	test_quotes()
	test_bindings()
	test_templates()
	test_long()

# EOF - vim: ts=4 sw=4 noet
