from tlang.rules.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.tree module.
"""

def test_parsing():
	TestUtils.ParseExamples("rules.txto", parseString)

# def test_parsing_transparency():
# 	TestUtils.ReparseExamples("rules.txto", parseString)
# 
if __name__ == "__main__":
	test_parsing ()
	# test_parsing_transparency ()

# EOF - vim: ts=4 sw=4 noet
