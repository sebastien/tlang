from texto.main import run as texto
import os
BASE = os.path.normpath(os.path.abspath(__file__) + "/../../../../")
NOTHING = object()

def getExamples( name ):
	path = os.path.join(BASE, "docs", name)
	res  = []
	with open(path) as f:
		status, xmltree = texto(["-Odom"], f, noOutput=True)
		for node in xmltree.getElementsByTagName("pre"):
			if not node.getAttribute("data-lang") == "tree": continue
			res.append("\n".join(_.data for _ in node.childNodes))
	return res

# EOF - vim: ts=4 sw=4 noet
