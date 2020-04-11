from tlang.query.model import Select,With
from tlang.compiler.query import QueryInterpreter
from tlang.tree import Node,node

# We define the given query: //dir/file[\\dir[@name]]
query = Select.Descendants(With.Name("dir")).then(
	Select.Children(With.Name("file")).where(
		Select.Ancestors(With.Name("dir")).where(
			Select.Self(With.Attribute("name")))))

# This is the tree we want to work with
tree = node("dir", {"name":"tlang"},
	node("dir", {"name":"research"},
		node("file", {"name":"compiler-query.py"}),
		node("file", {"name":"interpreter.py"}),
		node("file", {"name":"interpreter-stream.py"})))


# We start the querty interpreter
i = QueryInterpreter()
i.register(query)
for _ in i.terminals + i.composites:
	print (f"- {_}")
print (f"Registering query: {query}")
print (f"Running query '{query}' on tree:\n{tree}")

i.printMatchTable(i.run(tree))

# EOF - vim: ts=4 sw=4 noet
