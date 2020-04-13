#!/usr/bin/env pytest

from tlang.query.parser import parseString as parseQuery
from tlang.query.model import processQuery
from tlang.compiler.query import QueryInterpreter
from tlang.tree import node

query = lambda _:processQuery(parseQuery(_))

# That's the tree we want to work with
tree = node("dir", {"name":"tlang"},
	node("dir", {"name":"research"},
		node("file", {"name":"compiler-query.py"}),
		node("file", {"name":"interpreter.py"}),
		node("file", {"name":"interpreter-stream.py"})))
dir0, dir1, file0, file1, file2 = tree.walk()

def test_identity():
	for q in ("/file", "//dir", "//dir/file"):
		t = query(q)
		assert str(t) == q

def test_engine():
	for qs,expected in {
		"/file":[],
		"//file":[file0,file1,file2],
		"//dir":[dir0, dir1],
		"//dir/file":[file0, file1,file2],
	}.items():
		assert (qs, expected) == (qs, [_[1] for _ in QueryInterpreter().register(query(qs)).run(tree)])

# EOF
