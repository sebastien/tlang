from tlang.format.parser import parseString
from tlang.utils import TestUtils

__doc__ = """
Exercises the tlang.format module.
"""

def test_count():
	assert len(TestUtils.GetExamples("format.txto", "format")) > 0

def test_parsing():
	TestUtils.ParseExamples("format.txto", "format", parseString)

def test_parsing_transparency():
	TestUtils.ReparseExamples("format.txto", "format", parseString)

if __name__ == "__main__":
	test_count()
	test_parsing ()
	test_parsing_transparency ()

# EOF - vim: ts=4 sw=4 noet
