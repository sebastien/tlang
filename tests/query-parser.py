from tlang.query.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.query module.
"""

SELECTORS = """
/*
//*
/2/*
/node
/node-*
//node
//node-*
.
..
node/@attribute
@.
"""

EXPRESSIONS = """
count(//*)
sum(/*/@amount)
mean(/*/@amount,count(/*))
"""

BINDINGS = """
{node}
{node:A}
/{node}
add({sum(/*/@amount)},3)
"""

def test_selectors():
	for ql in SELECTORS:
		for q in ql.split("\n"):
			q = q.strip()
			if not q: continue
			r = parseString(q)
			print (q, r)

if __name__ == "__main__":
	test_queries()

# EOF - vim: ts=4 sw=4 noet
