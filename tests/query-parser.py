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
ns:node
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

BINDINGS = """
{A:node}
{A:node/child}
{A:node/child[@attribute]}
{A://node}
{A:./*}
{./*}
{./*}
{CHILDREN:./*}
{CHILDREN:./*}
{//*[@attribute]}
"""

VARIABLES = """
A
AB
AB/node
AB/node/@attr
"""

QUERIES = """
./*
./node
"""

def test_selectors():
	TestUtils.ParseLines(SELECTORS, parseString)

def test_axes():
	TestUtils.ParseLines(AXES, parseString)

def test_subsets():
	TestUtils.ParseLines(SUBSETS, parseString)

def test_predicates():
	TestUtils.ParseLines(PREDICATES, parseString)

def test_bindings():
	TestUtils.ParseLines(BINDINGS, parseString)

def test_variables():
	TestUtils.ParseLines(VARIABLES, parseString)

def test_queries():
	TestUtils.ParseLines(QUERIES, parseString)

if __name__ == "__main__":
	test_selectors()
	test_axes()
	test_subsets()
	test_bindings()
	test_predicates()
	test_variables()
	test_queries()

# EOF - vim: ts=4 sw=4 noet
