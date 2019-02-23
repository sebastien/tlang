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
  ${ATTRIBUTE_QUERY | /query-node}
  ${ATTRIBUTE_QUERY | ./query-attribute}
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

class ExpansionTranspiler:

	def process( self, node, indent=0 ):
		prefix = "\t" * indent
		if node.name == "expr-value-invocation":
			for i,c in enumerate(node.children):
				if i == 0:
					# Main node
					node_name = node.children[0].attr("name")
					yield "{0}node = create_node('{1}')".format(prefix, node_name)
				else:
					# Children, which might be attributes
					yield "{0}"
			# TODO
		elif node.name == "expr-value-template":
			pass
		elif node.name == "query":
			pass
		elif node.name == "query-selection":
			pass
		elif node.name == "query-axis":
			pass
		elif node.name == "query-node":
			pass
		elif node.name == "query-variable":
			pass
		else:
			raise Error("Unsupported node: {0}".format(node))

print (EXPANSION)
print ("------" * 10)
print (TEMPLATE)

# EOF - vim: ts=4 sw=4 noet
