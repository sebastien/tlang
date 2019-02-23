from tlang.parser import parseString

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
  ${ATTRIBUTE_QUERY/query-node}
  ${ATTRIBUTE_QUERY/query-attribute}
  VALUE
)
""")

print (TEMPLATE)


