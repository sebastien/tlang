from tlang.tree.parser import parseString
from texto.main import run as texto
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC  = os.path.join(BASE, "docs", "trees.txto")

# We extract the examples from the documentation
EXAMPLES = []
with open(DOC) as f:
	status, xmltree = texto(["-Odom"], f, noOutput=True)
	for node in xmltree.getElementsByTagName("pre"):
		if not node.getAttribute("data-lang") == "tree": continue
		EXAMPLES.append("\n".join(_.data for _ in node.childNodes))

# We run through the examples and make sure they all compile
for i,example in enumerate(EXAMPLES):
	result = parseString(example)
	if result.status is b'F':
		print ("FAILED", i)
	elif result.status is b'p':
		print ("PARTIAL", i)
	elif result.status is b'S':
		print ("OK", i)
	else:
		raise Exception("Unknown status: {0}". format(result.status))

# EOF - vim: ts=4 sw=4 noet
