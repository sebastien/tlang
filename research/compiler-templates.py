from tlang.parser import parseString

# TODO: Does the absence of an attribute indicate that the node can have
# an attribute or do we denote it differently (`@_`).

TEMPLATE = parseString("""
(expr-value-list
   (expr-value-symbol (@  (name "attr")))
   (expr-value-list
       (expr-value-symbol (@  (name "name")))
       (query ATTRIBUTE_QUERY))
    VALUE
)""")

EXPANSION = parseString("""
(declare-attribute
  (@ (name "name"))
  ${ATTRIBUTE_QUERY/query-node}
  ${ATTRIBUTE_QUERY/query-attribute}
  VALUE
)
""")

# @texto
#
# So we want to generate a state machine that 1) matches a tree and 2)
# binds the subtree to a context. We have to taking into account that
# there might be `…` in the template, that match zero or more elements.
# But in this case, we'll do a one-shot pass as we don't have any `…`


UPPER_CASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ_"

class TemplateTranspiler:

	def process( self, node, indent=0 ):
		prefix = "\t" * indent
		if node.name[0] in UPPER_CASE:
			yield "{0}{1} = node".format(prefix,node.name)
		else:
			yield "{0}if node.name != '{1}': return False".format(prefix,node.name)
			for k,v in node.attributes.items():
				yield "{0}attr = node.attr({1})".format(prefix,k)
				# TODO: Support attirbute template or wildcard
				yield "{0}if attr != ({1}): return False".format(prefix, v)
			for c in node.children:
				yield from self.process(c, indent + 1)

# @texto
# Note that some of these verifications could be skipped if we knew
# that the tree conforms to a schema.
# for _ in TemplateTranspiler().process(TEMPLATE):
# 	print (_)

# Now we want to expand the template and potentially execute the queries
# that it contains.

# TODO: We should really use an FSM instead
class ExpansionTranspiler:

	def process( self, node, indent=0 ):
		prefix = "\t" * indent
		if node.name == "expr-list":
			first_child = node.children[0]
			assert first_child.name == "expr-value-symbol"
			if first_child.attr("name") == "@":
				# We have an attribute, we expect the source to be
				# (expr-list
				#    (expr-value-symbol (@ (name NAME)))
				for c in node.children[1:]:
					assert c.name == "expr-list"
					assert len(c.children) == 2
					name  = c.children[0].attr("name")
					value = c.children[1].attr("value")
					yield "{0}node.attr('{1}', {2})".format(prefix, name, repr(value))
			else:
				# A list means that we're creating a new node
				for i,c in enumerate(node.children):
					if i == 0:
						# We're creating a new node and we have a symbol
						# as first child.
						node_name = node.children[0].attr("name")
						yield "{0}node = create_node('{1}')".format(prefix, node_name)
					else:
						# Children, which might be attributes
						yield from self.process(c, indent)
			# TODO
		elif node.name == "expr-value-template":
			# If it's a template, then we run the query and merge
			# in the selection
			for c in node.children:
				yield from self.process(c, indent)
				yield "{0}node.merge(selection)".format(prefix)
			pass
		elif node.name == "expr-variable":
			yield "{0}node.merge(context['{1}'])".format(prefix, node.attr("name"))
		elif node.name == "query":
			# A query always starts at the root
			yield "{0}query_root = root_node".format(prefix)
			for c in node.children:
				yield from self.process(c)
		elif node.name == "query-variable":
			yield "{0}query_root = context['{1}']".format(prefix, node.attr("name"))
		elif node.name == "query-selection":
			yield "{0}query_axis = None ; query_node = None ; query_attribute = None ; query_predicate = None".format(prefix)
			for c in node.children:
				yield from self.process(c)
			yield "{0}selection = query(query_root, query_axis, query_node, query_attribute, query_predicate)".format(prefix)
		elif node.name == "query-axis":
			# TODO: Axis should be an enum
			yield "{0}query_axis = '{1}'".format(prefix, node.attr("axis"))
		elif node.name == "query-node":
			yield "{0}query_node = '{1}'".format(prefix, node.attr("pattern"))
		else:
			raise ValueError("Unsupported node: {0}".format(node))

# print ("------" * 10)
#print (TEMPLATE)
print (EXPANSION)
for _ in ExpansionTranspiler().process(EXPANSION):
	print (_)

# EOF - vim: ts=4 sw=4 noet
