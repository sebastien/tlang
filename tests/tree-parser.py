from tlang.tree.parser import parseString
from tlang.utils import getExamples

__doc__ = """
Exercises the tlang.tree module.
"""

def test_parsing():
	"""Ensures that the examples in the documentation compile properly"""
	# We run through the examples and make sure they all compile
	for i,example in enumerate(getExamples("trees.txto")):
		result = parseString(example, process=False)
		if result.isFailure():
			raise Exception("Test {0} failed: {1}".format(i, result.describe()))
		elif result.isPartial():
			raise Exception("Test {0} failed: {1}".format(i, result.describe()))
		elif result.isSuccess():
			pass
		else:
			raise Exception("Unknown status: {0}". format(result.status))

def test_parsing_transparency():
	"""Ensures that the output of a parsed element is parseable and generates
	the exact same tree."""
	for i,example in enumerate(getExamples("trees.txto")):
		source_repr   = "\n".join(str(_) for _ in parseString(example))
		reparsed_repr = "\n".join(str(_) for _ in parseString(source_repr))
		assert source_repr == reparsed_repr

if __name__ == "__main__":
	test_parsing ()
	test_parsing_transparency ()

# EOF - vim: ts=4 sw=4 noet
