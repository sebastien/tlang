from tlang.query.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.query module.
"""

SELECTORS = """
.
..
...
@
@attribute
@attribute-*
*
node
node-*
VARIABLE_NAME
"""

AXES = """
/*
//*
/2/*
./*

\\*
\\\\*
\\2\\*

>*
>>*
>2>*

<*
<<*
<<*

.<*
.>*

<-<*
<-=<*
<+<*
<=+<*

.<-<*
.<-=<*
.<+<*
.<=+<*


>->*
>-=>*
>+>*
>=+>*

.>->*
.>-=>*
.>+>*
.>=+>*

.|*
"""

SUBSETS = """
./#0
./#0/#10
"""

PREDICATES = """
node[(has? {<<*/@name})]
"""

VARIABLES = """
A
AB
AB/node
AB/node/@attr
"""

def test_selectors():
	TestUtils.ParseLines(SELECTORS, parseString)

def test_axes():
	TestUtils.ParseLines(AXES, parseString)

def test_subsets():
	TestUtils.ParseLines(SUBSETS, parseString)

def test_predicates():
	TestUtils.ParseLines(PREDICATES, parseString)

def test_variables():
	TestUtils.ParseLines(VARIABLES, parseString)

if __name__ == "__main__":
	test_selectors()
	test_axes()
	test_subsets()
	test_predicates()
	test_variables()

# EOF - vim: ts=4 sw=4 noet
