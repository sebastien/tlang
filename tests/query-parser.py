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

"""

SUBSETS = """
./#0
./#0/#10
"""

PREDICATES = """
node[(has? {<<*@name})]
"""

def test_selectors():
	TestUtils.ParseLines(SELECTORS, parseString)

def test_axes():
	TestUtils.ParseLines(AXES, parseString)

def test_predicates():
	TestUtils.ParseLines(PREDICATES, parseString)

def test_subsets():
	TestUtils.ParseLines(SUBSETS, parseString)

if __name__ == "__main__":
	test_selectors()
	test_axes()
	test_subsets()
	test_predicates()

# EOF - vim: ts=4 sw=4 noet
